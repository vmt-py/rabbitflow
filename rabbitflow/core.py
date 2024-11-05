"""Core components and abstractions for RabbitFlow."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Any, Dict

T = TypeVar('T')
U = TypeVar('U')

@dataclass
class ProcessResult(Generic[U]):
    """Result of a message processing operation."""
    success: bool
    data: Optional[U]
    error: Optional[str] = None

class Processor(ABC, Generic[T, U]):
    """Base processor interface."""

    @abstractmethod
    def process(self, message: T) -> ProcessResult[U]:
        """Process a message."""
        pass

class FanoutTopicPair:
    """A fanout exchange connected to a topic exchange."""

    def __init__(self, channel: Any, name: str):
        self.channel = channel
        self.fanout = f"{name}.fanout"
        self.topic = f"{name}.topic"

    def setup(self) -> None:
        """Setup exchanges and binding."""
        exchanges = [
            (self.fanout, 'fanout'),
            (self.topic, 'topic'),
        ]
        for exchange_name, exchange_type in exchanges:
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=True
            )
            # Verify exchange type
            declared_type = self.channel.exchange_declare(
                exchange=exchange_name,
                passive=True
            ).method.exchange_type
            if declared_type != exchange_type:
                raise ValueError(f"Exchange {exchange_name} expected type {exchange_type}, got {declared_type}")

        # Create binding
        self.channel.exchange_bind(
            destination=self.topic,
            source=self.fanout,
            routing_key="#"
        )
