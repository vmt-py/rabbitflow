"""Main RabbitFlow application."""
from typing import Type, Dict
from loguru import logger
from .core import Processor, FanoutTopicPair
from .rabbit import RabbitClient
from pika import ConnectionParameters

class RabbitFlow:
    """Main application class."""
    
    def __init__(self, name: str, rabbit_params : ConnectionParameters ):
        self.name = name
        self.rabbit = RabbitClient(rabbit_params)
        self.rabbit.connect()
        
        # Components
        self.decoder = None
        self.validator = None
        self.processor = None
        
        # Exchange pairs
        self.raw = FanoutTopicPair(self.rabbit.channel, f"{name}.raw")
        self.decoded = FanoutTopicPair(self.rabbit.channel, f"{name}.decoded")
        self.validated = FanoutTopicPair(self.rabbit.channel, f"{name}.validated")
        self.failed = FanoutTopicPair(self.rabbit.channel, f"{name}.failed")

    def register_decoder(self, decoder: Type[Processor]) -> None:
        """Register decoder component."""
        self.decoder = decoder()
        self.raw.setup()
        self.decoded.setup()
        logger.info(f"Registered decoder: {decoder.__name__}")

    def register_validator(self, validator: Type[Processor]) -> None:
        """Register validator component."""
        self.validator = validator()
        self.validated.setup()
        logger.info(f"Registered validator: {validator.__name__}")

    def register_processor(self, processor: Type[Processor]) -> None:
        """Register main processor component."""
        self.processor = processor()
        logger.info(f"Registered processor: {processor.__name__}")

    def run(self) -> None:
        """Start processing messages."""
        try:
            logger.info("Starting message processing...")
            self.rabbit.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.rabbit.close()