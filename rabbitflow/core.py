"""Core components and abstractions for RabbitFlow."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Any
from pika.channel import Channel
from pika.exceptions import ChannelClosedByBroker

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

class FanoutTopicPair:
    """A fanout exchange connected to a topic exchange."""
    def __init__(self, channel: Channel, name: str):
        self.channel = channel
        self.fanout = f"{name}.fanout"
        self.topic = f"{name}.topic"

    def setup(self) -> None:
        """Setup exchanges and binding."""
        try:
            # Verificar si los exchanges existen usando passive=True
            for name, type_ in [(self.fanout, 'fanout'), (self.topic, 'topic')]:
                try:
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True,
                        passive=True
                    )
                except ChannelClosedByBroker:
                    # Si no existe, lo declaramos
                    self.channel = self.channel.connection.channel()
                    self.channel.exchange_declare(
                        exchange=name,
                        exchange_type=type_,
                        durable=True
                    )
            
            # Intentar crear el binding
            try:
                self.channel.exchange_bind(
                    source=self.fanout,
                    destination=self.topic,
                    routing_key="#"
                )
            except ChannelClosedByBroker:
                # Si falla, asumimos que el binding ya existe
                self.channel = self.channel.connection.channel()
                
        except Exception as e:
            raise Exception(f"Error setting up FanoutTopicPair: {str(e)}")

class TopicQueuePair:
    """A topic exchange connected to a queue."""
    def __init__(self,  channel: Channel, name: str, queue_name: str, routing_key: str = ""):
        self.channel = channel
        self.topic = f"{name}.topic"
        self.queue = queue_name
        self.routing_key = routing_key
        
    def setup(self) -> None:
        """Setup exchanges and binding."""
        try:
            # Verificar si el exchange existe
            try:
                self.channel.exchange_declare(
                    exchange=self.topic,
                    exchange_type='topic',
                    durable=True,
                    passive=True
                )
            except ChannelClosedByBroker:
                # Si no existe, lo declaramos
                self.channel = self.channel.connection.channel()
                self.channel.exchange_declare(
                    exchange=self.topic,
                    exchange_type='topic',
                    durable=True
                )

            # Verificar si la cola existe
            try:
                self.channel.queue_declare(
                    queue=self.queue,
                    durable=True,
                    passive=True
                )
            except ChannelClosedByBroker:
                # Si no existe, la declaramos
                self.channel = self.channel.connection.channel()
                self.channel.queue_declare(
                    queue=self.queue,
                    durable=True
                )

            # Intentar crear el binding
            try:
                self.channel.queue_bind(
                    exchange=self.topic,
                    queue=self.queue,
                    routing_key=self.routing_key
                )
            except ChannelClosedByBroker:
                # Si falla, asumimos que el binding ya existe
                self.channel = self.channel.connection.channel()

        except Exception as e:
            raise Exception(f"Error setting up TopicQueuePair: {str(e)}")