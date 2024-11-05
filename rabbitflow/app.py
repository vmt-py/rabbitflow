"""Main RabbitFlow application."""
from typing import Type, Optional
from loguru import logger
from pika import ConnectionParameters
from .core import (
    Processor, ExchangePair, QueueBinding,
    ExchangePairConfig, QueueConfig
)
from .rabbit import RabbitClient

class RabbitFlow:
    """Main application class."""
    
    def __init__(self, name: str, rabbit_params: ConnectionParameters):
        """Initialize RabbitFlow application."""
        logger.info(f"Initializing RabbitFlow application '{name}'")
        self.name = name
        
        # Setup RabbitMQ connection
        self.rabbit = RabbitClient(rabbit_params)
        self.rabbit.connect()
        logger.success("RabbitMQ connection established")
        
        # Components
        self.decoder = None
        self.validator = None
        self.processor = None
        
        # Default names
        self.default_names = self._get_default_names()

    def _get_default_names(self) -> dict:
        """Get default names for exchanges and queues."""
        return {
            'decodification': {
                'fanout': f"{self.name}.raw.fanout",
                'topic': f"{self.name}.raw.topic",
                'queue': f"{self.name}.decodification.queue"
            },
            'validation': {
                'fanout': f"{self.name}.decoded.fanout",
                'topic': f"{self.name}.decoded.topic",
                'queue': f"{self.name}.validation.queue"
            },
            'processing': {
                'fanout': f"{self.name}.validated.fanout",
                'topic': f"{self.name}.validated.topic",
                'queue': f"{self.name}.processing.queue"
            }
        }

    def register_decoder(
        self, 
        decoder: Type[Processor],
        fanout_name: Optional[str] = None,
        topic_name: Optional[str] = None,
        queue_name: Optional[str] = None
    ) -> None:
        """Register decoder component."""
        logger.info(f"Registering decoder: {decoder.__name__}")
        
        # Use provided names or defaults
        fanout = fanout_name or self.default_names['decodification']['fanout']
        topic = topic_name or self.default_names['decodification']['topic']
        queue = queue_name or self.default_names['decodification']['queue']
        
        # Setup decodification message infrastructure
        decoder_pair = ExchangePair(
            self.rabbit.channel, 
            ExchangePairConfig(fanout_name=fanout, topic_name=topic)
        )
        decoder_pair.setup()
        
        # Setup queue binding
        if queue:
            queue_binding = QueueBinding(
                self.rabbit.channel,
                QueueConfig(
                    exchange_name=topic,
                    queue_name=queue
                )
            )
            queue_binding.setup()
        
        # Setup validation message infrastructure
        validation_pair = ExchangePair(
            self.rabbit.channel,
            ExchangePairConfig(
                fanout_name=self.default_names['validation']['fanout'],
                topic_name=self.default_names['validation']['topic']
            )
        )
        validation_pair.setup()
        
        self.decoder = decoder()
        logger.success("Decoder registered successfully")

    def register_validator(
        self, 
        validator: Type[Processor],
        fanout_name: Optional[str] = None,
        topic_name: Optional[str] = None,
        queue_name: Optional[str] = None
    ) -> None:
        """Register validator component."""
        logger.info(f"Registering validator: {validator.__name__}")
        
        # Use provided names or defaults
        fanout = fanout_name or self.default_names['validation']['fanout']
        topic = topic_name or self.default_names['validation']['topic']
        queue = queue_name or self.default_names['validation']['queue']
        
        # Setup validation message infrastructure
        validation_pair = ExchangePair(
            self.rabbit.channel,
            ExchangePairConfig(fanout_name=fanout, topic_name=topic)
        )
        validation_pair.setup()
        
        # Setup processing message infrastructure
        processing_pair = ExchangePair(
            self.rabbit.channel,
            ExchangePairConfig(
                fanout_name=self.default_names['processing']['fanout'],
                topic_name=self.default_names['processing']['topic']
            )
        )
        processing_pair.setup()
        
        # Setup queue binding if queue name provided
        if queue:
            queue_binding = QueueBinding(
                self.rabbit.channel,
                QueueConfig(
                    exchange_name=topic,
                    queue_name=queue
                )
            )
            queue_binding.setup()
        
        self.validator = validator()
        logger.success("Validator registered successfully")

    def register_processor(
        self, 
        processor: Type[Processor],
        queue_name: Optional[str] = None,
        topic_name: Optional[str] = None
    ) -> None:
        """Register processor component with optional queue binding."""
        logger.info(f"Registering processor: {processor.__name__}")
        
        # Use provided names or defaults
        topic = topic_name or self.default_names['processing']['topic']
        queue = queue_name or self.default_names['processing']['queue']
        
        # Setup queue binding if queue name provided
        if queue:
            queue_binding = QueueBinding(
                self.rabbit.channel,
                QueueConfig(
                    exchange_name=topic,
                    queue_name=queue
                )
            )
            queue_binding.setup()
        
        self.processor = processor()
        logger.success("Processor registered successfully")

    def run(self) -> None:
        """Start processing messages."""
        try:
            logger.info("=== Starting RabbitFlow Message Processing ===")
            
            # Verify components
            if not all([self.decoder, self.validator, self.processor]):
                logger.error("Missing required components")
                return
            
            logger.info("Starting message consumption...")
            self.rabbit.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.warning("Received shutdown signal")
            self.rabbit.close()
            logger.success("Shutdown completed")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            self.rabbit.close()
            raise