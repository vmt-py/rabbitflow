# core.py
"""Core components and abstractions for RabbitFlow."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Protocol
from pika.channel import Channel
from pika.exceptions import ChannelClosedByBroker
from loguru import logger

T = TypeVar('T')
U = TypeVar('U')

@dataclass
class ProcessResult(Generic[T]):
    """Result of a message processing operation."""
    success: bool
    data: Optional[T]
    error: Optional[str] = None

class Processor(ABC, Generic[T, U]):
    """Base processor interface."""
    @abstractmethod
    def process(self, message: T) -> ProcessResult[U]:
        """Process a message."""
        pass

@dataclass
class ExchangePairConfig:
    """Configuration for a pair of exchanges."""
    fanout_name: str
    topic_name: str

@dataclass
class QueueConfig:
    """Configuration for a queue."""
    exchange_name: str
    queue_name: str
    routing_key: str = "#"

class MessageInfrastructure(ABC):
    """Base class for message infrastructure."""
    def __init__(self, channel: Channel, config):
        self.channel = channel
        self.config = config

        
    def _ensure_channel(self) -> None:
        """Ensure channel is open and create a new one if needed."""
        try:
            if self.channel.is_closed:
                self.channel = self.channel.connection.channel()
                # Configurar el canal para confirmar publicaciones
                self.channel.confirm_delivery()
                logger.info("Created new channel")
        except Exception as e:
            logger.warning(f"Error ensuring channel: {str(e)}")
            # Crear nuevo canal y configurarlo
            self.channel = self.channel.connection.channel()
            self.channel.confirm_delivery()
            logger.info("Created new channel after error")

class ExchangePair(MessageInfrastructure):
    """A fanout exchange connected to a topic exchange."""
    def setup(self) -> None:
        """Setup exchanges and binding."""
        try:
            self._ensure_channel()
            
            # Setup exchanges sin usar passive=True inicialmente
            for name, type_ in [(self.config.fanout_name, 'fanout'), 
                              (self.config.topic_name, 'topic')]:
                try:
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True
                    )
                    logger.info(f"Exchange {name} setup complete")
                except Exception as e:
                    logger.warning(f"Error declaring exchange {name}: {str(e)}")
                    self._ensure_channel()
                    # Reintentar sin passive
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True
                    )
            
            # Setup binding
            self._ensure_channel()
            self.channel.exchange_bind(
                source=self.config.fanout_name,
                destination=self.config.topic_name,
                routing_key="#"
            )
            logger.info(f"Created binding from {self.config.fanout_name} to {self.config.topic_name}")
                
        except Exception as e:
            raise Exception(f"Error setting up ExchangePair: {str(e)}")

class QueueBinding(MessageInfrastructure):
    """A queue bound to a topic exchange."""
    def setup(self) -> None:
        """Setup queue and binding."""
        try:
            self._ensure_channel()
            
            # Setup queue sin usar passive=True inicialmente
            try:
                self.channel.queue_declare(
                    queue=self.config.queue_name,
                    durable=True
                )
                logger.info(f"Queue {self.config.queue_name} setup complete")
            except Exception as e:
                logger.warning(f"Error declaring queue: {str(e)}")
                self._ensure_channel()
                self.channel.queue_declare(
                    queue=self.config.queue_name,
                    durable=True
                )

            # Setup binding
            self._ensure_channel()
            self.channel.queue_bind(
                queue=self.config.queue_name,
                exchange=self.config.exchange_name,
                routing_key=self.config.routing_key
            )
            logger.info(f"Created binding from {self.config.exchange_name} to {self.config.queue_name}")

        except Exception as e:
            raise Exception(f"Error setting up QueueBinding: {str(e)}")