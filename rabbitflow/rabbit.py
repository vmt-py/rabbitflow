"""RabbitMQ client implementation."""
import pika
from loguru import logger
from typing import Optional

class RabbitClient:
    """Simple RabbitMQ client."""

    def __init__(self, connection_params: pika.ConnectionParameters):
        """
        Initialize the RabbitMQ client with connection parameters.

        :param connection_params: Connection parameters for RabbitMQ.
        """
        self.connection_params = connection_params
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def connect(self) -> None:
        """Establish connection."""
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        logger.info("Connected to RabbitMQ")

    def close(self) -> None:
        """Close connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Connection to RabbitMQ closed")
