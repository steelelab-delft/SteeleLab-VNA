"""Basic TCP client for retrieving measurement data"""

import socket
from struct import unpack
from types import TracebackType
from typing import Type

from pythonping import ping

from project.server.helpers import printd
from project.server.protocol import TCPCommandProtocol as prot


class TCPClient:
    """Simple host:port socket client; use `with TCPClient(host, port) as c` for proper disconnect!"""

    BUFSIZE = prot.POINTS_PER_PACKET * 32
    """Receiver buffer size in bytes = optimal packet size times the size of four (64-bits) floats"""

    DEBUG = True
    """Whether to print debugging information"""

    def __init__(self, host: str, port: int) -> None:
        try:
            self.socket = socket.create_connection((host, port), timeout=5)
        except socket.gaierror as err:
            raise socket.gaierror(f"TCP client could not resolve address {host}:{port}.") from err
        except (ConnectionRefusedError, TimeoutError) as err:
            raise ConnectionError(f"Attempted to connect to {host}:{port}. {err.strerror}") from err
        self._reset_trigger_config()

    def __enter__(self) -> "TCPClient":
        """Enters the `with` block."""
        return self

    def send_receive(self, data: str) -> bytes:
        """Simplest form of useful communication.
        Server expects a command from client and expects client to wait for response.
        """
        if len(data) == 0:
            return b""
        if len(data) > TCPClient.BUFSIZE:
            raise ValueError(f"Data {data} is too long (> {TCPClient.BUFSIZE}).")
        self.socket.sendall(data.encode("utf-8"))
        return self.socket.recv(TCPClient.BUFSIZE)

    def start_acquisition(self) -> None:
        """Requests programmable logic to start acquisition."""
        if self.send_receive(f"{prot.RUN_PL}1") != prot.RESPONSE_OK:
            raise RuntimeError("SoC refused to start acquisition, check configuration!")

    def stop_acquisition(self) -> None:
        """Requests programmable logic to stop acquisition."""
        self.send_receive(f"{prot.RUN_PL}0")

    def request_data(self) -> tuple[float, float, float, float]:
        """Asks server for acquired data."""
        out = self.send_receive(prot.DATA)
        # This should be 32 bytes or an integer multiple (in case of multiple samples).
        if len(out) % 32 != 0:
            raise RuntimeError(f"TCP expected a multiple of 32 bytes (4 values), but got {len(out)}!")
        return self.unpack_floats(out)

    def send_tpp(self, time: float) -> None:
        """Configures time per point in seconds. Note: rounded to nearest microsecond!"""
        self.send_receive(f"{prot.TPP}{time*1E6:.0f}")

    def send_dead_time(self, time: float) -> None:
        """Configures deadtime in seconds. Note: rounded to nearest microsecond!"""
        self.send_receive(f"{prot.DEAD_TIME}{time*1E6:.0f}")

    def send_trigger_length(self, time: float) -> None:
        """Configures trigger pulse length in seconds. Note: rounded to nearest microsecond!"""
        self.send_receive(f"{prot.TRIG_LEN}{time*1E6:.0f}")

    def _reset_trigger_config(self) -> None:
        """Disables trigger outputs."""
        self.send_receive(f"{prot.TRIG_0_CONF}0")  # no trigger output
        self.send_receive(f"{prot.TRIG_1_CONF}0")  # no trigger output

    def send_trigger_config(self, trig_nr: int, positive: bool, sweep: bool = True, step: bool = True) -> None:
        """Configure an output trigger (either 0 or 1).
        `positive` controls the trigger polarity (True = active-high; False = active-low).
        `sweep` controls whether to trigger at the start of the first point.
        `step` controls whether to trigger for each subsequent point.
        """
        if trig_nr not in {0, 1}:
            raise ValueError(f"Cannot configure trigger number {trig_nr}; only 0 or 1 are allowed.")
        char = prot.TRIG_1_CONF if trig_nr else prot.TRIG_0_CONF
        bits = 0b0000
        # TODO: un-hardcode this
        if not positive:
            bits |= 0b0001
        if sweep:
            bits |= 0b0010
        if step:
            bits |= 0b0100
        self.send_receive(f"{char}{bits}")

    def get_queue_size(self) -> int:
        """Queries DMA buffer queue size."""
        return int.from_bytes(self.send_receive(prot.QUEUE_SIZE), byteorder="big")

    def get_server_cpu_temp(self) -> float:
        """Queries server's SoC temperature."""
        return self.unpack_floats(self.send_receive(prot.CPU_TEMP))[0]

    def ping(self) -> float:
        """Returns the network latency in seconds between the client and server, aka ping.
        Returns timeout length if no connection could be made (1 second).
        """
        return ping(self.socket.getpeername(), timeout=1, count=5).rtt_avg

    @staticmethod
    def unpack_floats(by: bytes) -> tuple[float, float, float, float]:
        """Converts multiples of 8 bytes to 64-bit floating point numbers."""
        return unpack(f"{len(by) // 8}d", by)

    def _stop_server(self, really: bool = False) -> bool:
        """Stops TCP server. Be careful, you have to restart the server manually if stopped!
        Only use this for debugging.
        """
        if really:
            # Server should return empty byte string only if it shut down itself correctly.
            return self.socket.send(prot.STOP_SERVER.encode())
        return False

    def __exit__(
        self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Leaves the `with` block."""
        if TCPClient.DEBUG:
            printd("TCP client exiting.")
            if exc_type is not None:
                printd(f"Exception occured: {type(exc_val).__name__}: {' '.join(exc_val.args)}")
        self.socket.close()
