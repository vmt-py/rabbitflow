# app.py
"""Main RabbitFlow application."""
from typing import Type, Optional
from loguru import logger
from pika import ConnectionParameters
from .core import (
    Processor, FanoutTopicPair, TopicQueuePair, 
    ProcessResult, MessageInfrastructure
)
from .rabbit import RabbitClient

class RabbitFlow:
    """Main application class."""
    
    def __init__(self, name: str, rabbit_params: ConnectionParameters):
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
        
        # Setup message infrastructure
        self._setup_infrastructure()

    def _setup_infrastructure(self) -> None:
        """Initialize message processing infrastructure."""
        self.raw = FanoutTopicPair(self.rabbit.channel, f"{self.name}.raw")
        self.decoded = FanoutTopicPair(self.rabbit.channel, f"{self.name}.decoded")
        self.validated = FanoutTopicPair(self.rabbit.channel, f"{self.name}.validated")
        self.failed = FanoutTopicPair(self.rabbit.channel, f"{self.name}.failed")

    def _register_component(self, 
                          component: Type[Processor], 
                          infrastructure: Optional[MessageInfrastructure] = None,
                          name: str = None) -> None:
        """Register a processing component with optional infrastructure setup."""
        component_name = name or component.__name__.lower()
        logger.info(f"Registering {component_name}")
        
        if infrastructure:
            infrastructure.setup()
            
        setattr(self, component_name, component())
        logger.success(f"{component_name} registered successfully")

    def register_decoder(self, decoder: Type[Processor]) -> None:
        """Register decoder component."""
        self._register_component(decoder, self.raw, "decoder")
        self.decoded.setup()

    def register_validator(self, validator: Type[Processor]) -> None:
        """Register validator component."""
        self._register_component(validator, self.validated, "validator")

    def register_processor(self, processor: Type[Processor]) -> None:
        """Register main processor component."""
        self._register_component(processor, name="processor")

    def _verify_components(self) -> bool:
        """Verify all required components are registered."""
        required = ['decoder', 'validator', 'processor']
        missing = [comp for comp in required if not getattr(self, comp)]
        
        if missing:
            logger.error(f"Missing required components: {', '.join(missing)}")
            return False
        return True

    def run(self) -> None:
        """Start processing messages."""
        try:
            logger.info("=== Starting RabbitFlow Message Processing ===")
            
            if not self._verify_components():
                return
            
            logger.info("Starting message consumption...")
            self.rabbit.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.warning("Received shutdown signal")
            self._shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            self._shutdown()
            raise

    def _shutdown(self) -> None:
        """Shutdown the application."""
        logger.info("Initiating graceful shutdown...")
        self.rabbit.close()
        logger.success("RabbitFlow shutdown completed")