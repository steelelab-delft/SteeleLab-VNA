"""Tests for the TCP server"""

from threading import Thread
from types import TracebackType
from typing import Type

# Apply the mocked pynq module before importing the classes to be tested.
from project.server.protocol import TCPCommandProtocol
from tests.server import mocked_pynq

mocked_pynq.mock_pynq_module(mocked_pynq)

from project.client.connection.tcp_client import TCPClient
from project.server.tcp_server import TCPDataServer


class TCPClient(TCPClient):
    """Modification of TCPClient class for testing purposes"""

    def __exit__(
        self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Stops server when exiting a `with` block."""
        try:
            self._stop_server(True)
        except ConnectionAbortedError:
            pass  # socket already closed
        super().__exit__(exc_type, exc_val, exc_tb)


def test_tcp_commands() -> None:
    dead_time = 100E-6  # seconds
    tpp = 1E-3  # seconds
    trig_length = 10E-6  # seconds
    tds = TCPDataServer(host="localhost", port=2024)
    thr = Thread(target=tds.serve_one_client, name="test_tcp_data_server")

    # Start local test server and connect with client.
    thr.start()
    with TCPClient(host="localhost", port=2024) as tc:
        # Send config parameters.
        tc.send_dead_time(dead_time)
        tc.send_tpp(tpp)
        tc.send_trigger_length(trig_length)
        tc.send_trigger_config(trig_nr=0, positive=True, sweep=True, step=False)

        # Check that trigger config arrived in MMIO register.
        bits = tds.pl_interface.read_mmio(tds.TRIG_0_CONF)
        assert (  # binary trig conf OR trig length in clock cycles
            bits == 0b0010
        ), "trigger config not correctly written to MMIO register"
        tc.send_trigger_config(trig_nr=0, positive=False, sweep=False, step=True)
        bits = tds.pl_interface.read_mmio(tds.TRIG_0_CONF)
        assert (  # binary trig conf OR trig length in clock cycles
            bits == 0b0101
        ), "trigger config not correctly updated in MMIO register"

        # Check that dead time and time per point arrived in MMIO registers.
        bits = tds.pl_interface.read_mmio(tds.DEAD_TIME)
        assert (  # binary dead time in microseconods is read
            bits == dead_time * 1E6
        ), "dead time not correctly written to MMIO register"
        bits = tds.pl_interface.read_mmio(tds.TPP)
        assert (  # binary time per point point in microseconds is read
            bits == tpp * 1E6
        ), "time per point not correctly written to MMIO register"

        # Test queue size.
        qs = tc.get_queue_size()
    assert isinstance(qs, int), "queue size request did not return integer"
    assert qs == 0, "queue size is not zero before start data acquisition (invalid data in queue)"
    thr.join(timeout=15)
    assert not thr.is_alive(), "server thread did not finish in 15 seconds after receiving stop command"


def test_tcp_request_data() -> None:
    tds = TCPDataServer(host="localhost", port=2025)
    thr = Thread(target=tds.serve_one_client, name="server_thread")

    # Start local test server and connect with client.
    thr.start()
    with TCPClient(host="localhost", port=2025) as tc:
        tc.send_tpp(2)  # minimal settings for no error
        tc.send_dead_time(1)  # 0 < dead_time < tpp
        assert (  # try data request
            tc.send_receive(TCPCommandProtocol.DATA) == TCPCommandProtocol.RESPONSE_ERR
        ), "acquisition not started should return error response"

        # Start acquisition and request data again.
        tc.start_acquisition()
        data = tc.request_data()
    # Stop server when exiting with block
    assert len(data) > 0, "data should not be empty"
    assert len(data) <= TCPCommandProtocol.POINTS_PER_PACKET * 4, "data should not be longer than 4 * points per packetwt"
    assert isinstance(data[0], float), "data element should be float"
    thr.join(timeout=15)
    assert not thr.is_alive(), "server did not exit properly"
