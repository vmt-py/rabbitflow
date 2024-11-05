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
    def __init__(self, channel: Channel):
        self.channel = channel
        
    def _ensure_channel(self) -> None:
        if self.channel.is_closed:
            self.channel = self.channel.connection.channel()

class ExchangePair(MessageInfrastructure):
    """A fanout exchange connected to a topic exchange."""
    def __init__(self, channel: Channel, config: ExchangePairConfig):
        super().__init__(channel)
        self.config = config

    def setup(self) -> None:
        """Setup exchanges and binding."""
        try:
            # Setup exchanges
            for name, type_ in [(self.config.fanout_name, 'fanout'), 
                              (self.config.topic_name, 'topic')]:
                try:
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True,
                        passive=True
                    )
                    logger.info(f"Exchange {name} already exists")
                except ChannelClosedByBroker:
                    self._ensure_channel()
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True
                    )
                    logger.info(f"Created exchange {name}")
            
            # Setup binding
            try:
                self.channel.exchange_bind(
                    source=self.config.fanout_name,
                    destination=self.config.topic_name,
                    routing_key="#"
                )
                logger.info(f"Created binding from {self.config.fanout_name} to {self.config.topic_name}")
            except ChannelClosedByBroker:
                logger.info(f"Binding already exists")
                self._ensure_channel()
                
        except Exception as e:
            raise Exception(f"Error setting up ExchangePair: {str(e)}")

class QueueBinding(MessageInfrastructure):
    """A queue bound to a topic exchange."""
    def __init__(self, channel: Channel, config: QueueConfig):
        super().__init__(channel)
        self.config = config

    def setup(self) -> None:
        """Setup queue and binding."""
        try:
            # Setup queue
            try:
                self.channel.queue_declare(
                    queue=self.config.queue_name,
                    durable=True,
                    passive=True
                )
                logger.info(f"Queue {self.config.queue_name} already exists")
            except ChannelClosedByBroker:
                self._ensure_channel()
                self.channel.queue_declare(
                    queue=self.config.queue_name,
                    durable=True
                )
                logger.info(f"Created queue {self.config.queue_name}")

            # Setup binding
            try:
                self.channel.queue_bind(
                    queue=self.config.queue_name,
                    exchange=self.config.exchange_name,
                    routing_key=self.config.routing_key
                )
                logger.info(f"Created binding from {self.config.exchange_name} to {self.config.queue_name}")
            except ChannelClosedByBroker:
                logger.info("Binding already exists")
                self._ensure_channel()

        except Exception as e:
            raise Exception(f"Error setting up QueueBinding: {str(e)}")