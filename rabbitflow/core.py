# core.py
"""Core components and abstractions for RabbitFlow."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Generic, Optional, Protocol, Tuple
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

class ExchangeType(Enum):
    """Tipos de exchanges soportados."""
    FANOUT = 'fanout'
    TOPIC = 'topic'

@dataclass
class ExchangeConfig:
    """Configuración de un exchange."""
    name: str
    type: ExchangeType
    durable: bool = True

@dataclass
class BindingConfig:
    """Configuración de un binding."""
    source: str
    destination: str
    routing_key: str = "#"

class IMessageBroker(Protocol):
    """Interfaz para operaciones del message broker."""
    def declare_exchange(self, name: str, type: str, durable: bool, passive: bool) -> None:
        pass
    
    def bind_exchange(self, source: str, destination: str, routing_key: str) -> None:
        pass
    
    def declare_queue(self, name: str, durable: bool, passive: bool) -> None:
        pass
    
    def bind_queue(self, queue: str, exchange: str, routing_key: str) -> None:
        pass

class MessageInfrastructure(ABC):
    """Base class for message infrastructure components."""
    def __init__(self, channel: Channel):
        self.channel = channel
        
    def _ensure_channel(self) -> None:
        """Ensure channel is open, reconnect if needed."""
        if self.channel.is_closed:
            self.channel = self.channel.connection.channel()
            
    def _verify_exchange(self, name: str, type_: str) -> Tuple[bool, Optional[str]]:
        """Verify if exchange exists with correct type."""
        try:
            self.channel.exchange_declare(
                exchange=name,
                exchange_type=type_,
                durable=True,
                passive=True
            )
            return True, type_
        except ChannelClosedByBroker as e:
            self._ensure_channel()
            if "NOT_FOUND" in str(e):
                return False, None
            return True, "unknown"

class ExchangePair(MessageInfrastructure):
    """Base class for exchange pairs."""
    def __init__(self, channel: Channel, name: str, 
                 source_type: ExchangeType, dest_type: ExchangeType):
        super().__init__(channel)
        self.name = name
        self.source = ExchangeConfig(f"{name}.{source_type.value}", source_type)
        self.dest = ExchangeConfig(f"{name}.{dest_type.value}", dest_type)
        
    def setup(self) -> None:
        """Setup exchanges and verify configuration."""
        try:
            for config in [self.source, self.dest]:
                exists, actual_type = self._verify_exchange(config.name, config.type.value)
                
                if exists:
                    if actual_type == config.type.value:
                        logger.info(f"Exchange {config.name} exists with correct type")
                    else:
                        raise ValueError(
                            f"Exchange {config.name} exists with wrong type: {actual_type}"
                        )
                else:
                    logger.info(f"Creating exchange {config.name}")
                    self.channel.exchange_declare(
                        exchange=config.name,
                        exchange_type=config.type.value,
                        durable=True
                    )
                    
            self._create_binding()
            logger.success(f"Exchange pair {self.name} setup completed")
            
        except Exception as e:
            raise Exception(f"Error setting up {self.__class__.__name__}: {str(e)}")
    
    def _create_binding(self) -> None:
        """Create binding between exchanges."""
        try:
            self.channel.exchange_bind(
                source=self.source.name,
                destination=self.dest.name,
                routing_key="#"
            )
            logger.info(f"Created binding between {self.source.name} and {self.dest.name}")
        except ChannelClosedByBroker:
            logger.info(f"Binding already exists between {self.source.name} and {self.dest.name}")
            self._ensure_channel()

class FanoutTopicPair(ExchangePair):
    """A fanout exchange connected to a topic exchange."""
    def __init__(self, channel: Channel, name: str):
        super().__init__(channel, name, ExchangeType.FANOUT, ExchangeType.TOPIC)

class TopicQueuePair(MessageInfrastructure):
    """A topic exchange connected to a queue."""
    def __init__(self, channel: Channel, name: str, queue_name: str, routing_key: str = ""):
        super().__init__(channel)
        self.topic = f"{name}.topic"
        self.queue = queue_name
        self.routing_key = routing_key
        
    def setup(self) -> None:
        """Setup exchange, queue and binding."""
        try:
            # Verify/create topic exchange
            exists, actual_type = self._verify_exchange(self.topic, 'topic')
            if not exists:
                self.channel.exchange_declare(
                    exchange=self.topic,
                    exchange_type='topic',
                    durable=True
                )

            # Verify/create queue
            try:
                self.channel.queue_declare(queue=self.queue, durable=True, passive=True)
                logger.info(f"Queue {self.queue} exists")
            except ChannelClosedByBroker:
                self._ensure_channel()
                self.channel.queue_declare(queue=self.queue, durable=True)
                logger.info(f"Created queue {self.queue}")

            # Create binding
            try:
                self.channel.queue_bind(
                    exchange=self.topic,
                    queue=self.queue,
                    routing_key=self.routing_key
                )
                logger.info(f"Created binding from {self.topic} to {self.queue}")
            except ChannelClosedByBroker:
                logger.info(f"Binding already exists from {self.topic} to {self.queue}")
                self._ensure_channel()

        except Exception as e:
            raise Exception(f"Error setting up TopicQueuePair: {str(e)}")