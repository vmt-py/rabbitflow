"""Main RabbitFlow application."""
from typing import Type, Optional, Any, Dict
from loguru import logger
from .core import Processor, FanoutTopicPair, ProcessResult
from .rabbit import RabbitClient
import pika
import graphviz

class RabbitFlow:
    """Main application class."""

    def __init__(self, name: str, rabbit_params: pika.ConnectionParameters):
        """
        Initialize the RabbitFlow application.

        :param name: Name of the application.
        :param rabbit_params: RabbitMQ connection parameters.
        """
        self.name = name
        self.rabbit = RabbitClient(rabbit_params)
        self.rabbit.connect()

        # Registered processors
        self.processors: Dict[str, Dict[str, Any]] = {}

        # Exchange pairs
        self.exchanges: Dict[str, FanoutTopicPair] = {}

    def setup_exchange(self, stage: str) -> FanoutTopicPair:
        """Setup an exchange for a given stage."""
        if stage in self.exchanges:
            return self.exchanges[stage]

        exchange = FanoutTopicPair(self.rabbit.channel, f"{self.name}.{stage}")
        exchange.setup()
        self.exchanges[stage] = exchange
        logger.info(f"Exchange set up for stage: {stage}")
        return exchange

    def register_processor(self, stage: str, processor_cls: Type[Processor], output_stage: Optional[str] = None) -> None:
        """Register a processor for a given stage."""
        processor = processor_cls()
        self.processors[stage] = {
            'processor': processor,
            'output_stage': output_stage
        }
        self.consume_stage(stage, processor, output_stage)
        logger.info(f"Registered processor: {processor_cls.__name__} for stage: {stage}")

    def consume_stage(self, input_stage: str, processor: Processor, output_stage: Optional[str]) -> None:
        """Set up consumption for a given stage."""
        input_exchange = self.setup_exchange(input_stage)

        if output_stage:
            output_exchange_success = self.setup_exchange(f"{output_stage}.success")
            output_exchange_failure = self.setup_exchange(f"{output_stage}.failure")
        else:
            output_exchange_success = None
            output_exchange_failure = None

        queue_name = f"{self.name}.{input_stage}.queue"
        self.rabbit.channel.queue_declare(queue=queue_name, durable=True)
        self.rabbit.channel.queue_bind(
            exchange=input_exchange.topic,
            queue=queue_name,
            routing_key="#"
        )

        def callback(ch: pika.adapters.blocking_connection.BlockingChannel, method, properties, body):
            result: ProcessResult = processor.process(body)
            if result.success:
                if output_exchange_success and result.data is not None:
                    ch.basic_publish(
                        exchange=output_exchange_success.fanout,
                        routing_key='',
                        body=result.data if isinstance(result.data, bytes) else str(result.data).encode()
                    )
                logger.info(f"Message processed successfully at stage: {input_stage}")
            else:
                if output_exchange_failure:
                    ch.basic_publish(
                        exchange=output_exchange_failure.fanout,
                        routing_key='',
                        body=result.error.encode() if result.error else b"Unknown error"
                    )
                logger.error(f"Message processing failed at stage: {input_stage} with error: {result.error}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.rabbit.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        logger.info(f"Consumer set up for stage: {input_stage}")

    def draw_network_graph(self, output_file: str = 'rabbitflow_network') -> None:
        """Generate a graph representation of the RabbitMQ network."""
        dot = graphviz.Digraph(comment='RabbitFlow Network')

        # Add nodes for exchanges and queues
        for exchange_name, exchange in self.exchanges.items():
            dot.node(exchange_name, shape='ellipse', label=exchange_name)

        for stage in self.processors:
            queue_name = f"{self.name}.{stage}.queue"
            dot.node(queue_name, shape='box', label=queue_name)

        # Add edges between exchanges and queues
        for stage, info in self.processors.items():
            input_exchange = self.exchanges[stage]
            queue_name = f"{self.name}.{stage}.queue"
            dot.edge(input_exchange.topic, queue_name)

            output_stage = info['output_stage']
            if output_stage:
                # Edges from processor (queue) to success and failure exchanges
                success_exchange = self.exchanges.get(f"{output_stage}.success")
                failure_exchange = self.exchanges.get(f"{output_stage}.failure")

                if success_exchange:
                    dot.edge(queue_name, success_exchange.fanout, label='success')
                if failure_exchange:
                    dot.edge(queue_name, failure_exchange.fanout, label='failure')

        # Save the graph to a file
        dot.render(output_file, format='png', cleanup=True)
        logger.info(f"Network graph generated: {output_file}.png")

    def run(self) -> None:
        """Start processing messages."""
        try:
            logger.info("Starting message processing...")
            self.rabbit.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.rabbit.close()
