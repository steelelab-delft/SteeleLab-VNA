"""Mocked TCP client module for testing without connecting to the server"""

import numpy as np

from project.client.connection.tcp_client import TCPClient
from project.server.helpers import floats64_to_bytes
from project.server.protocol import TCPCommandProtocol


class MockedTCPClient(TCPClient):
    """Mocked version of TCP client class"""

    def __init__(self, host: str, port: int) -> None:
        """Fakes to connect with a socket"""

    def __exit__(self, *args) -> None:
        """Overloads parent class' __exit__ method."""

    def send_receive(self, data: str) -> bytes:
        """Mocks the communication by always returning a negative temperature or an OK response."""
        if data == TCPCommandProtocol.CPU_TEMP:
            return floats64_to_bytes((-5., ))
        elif data == TCPCommandProtocol.QUEUE_SIZE:
            return (1).to_bytes(length=32, byteorder="big")
        return TCPCommandProtocol.RESPONSE_OK

    def request_data(self) -> tuple[float] | tuple[float, float, float, float]:
        """Returns test data: four randomised IQ values per point in interval [-1, 1)."""
        return tuple((np.random.random_sample(4 * TCPCommandProtocol.POINTS_PER_PACKET) * 2 - 1))
