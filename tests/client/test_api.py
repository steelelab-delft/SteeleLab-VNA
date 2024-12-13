"""Tests for Application Programming Interface"""

from threading import Thread
from unittest.mock import patch

from pytest import fail, raises

from project.client.application.api import SLVNA
from tests.client.mocked_generator import MockedGenController
from tests.client.mocked_tcp_client import MockedTCPClient


def new_imaginary_vna() -> SLVNA:
    gen_rf = MockedGenController("rf")
    gen_lo = MockedGenController("lo")
    gen_clk = MockedGenController("clk")
    return SLVNA("1.2.3.4:5678", gen_rf, gen_lo, gen_clk)


def test_api_fsweep() -> None:
    """Initialises mocked generators for rf, lo and clock and test basic frequency sweep."""
    vna = new_imaginary_vna()
    vna.set_fsweep(1, 9E9, -5, points=50, timestep=5E-3)

    # Where to patch: https://docs.python.org/3/library/unittest.mock.html#where-to-patch.
    # Patch the TCP client and obtain the mocked data.
    with patch("project.client.application.api.TCPClient", side_effect=MockedTCPClient):
        data = vna.run()[0]

    assert data.sizes.get("f") == 50, "should contain 50 frequencies (points)"


def test_kwargs() -> None:
    """Tests the ability to change VNA configuration in any set_ method."""
    vna = new_imaginary_vna()
    vna.set_(addr_soc="2.3.4.5:6789", lo_power=-0.12345)
    assert getattr(vna, "addr_soc") == "2.3.4.5:6789", "addr_soc attribute not set correctly"
    vna.set_fsweep(0, 2, 4, timestep=5, points=6)
    assert getattr(vna, "points") == 6, "points attribute not set correctly"
    vna.set_psweep(0, 1, 2, timestep=3, points=7)
    assert getattr(vna, "points") == 7, "points attribute not updated correctly"
    assert getattr(vna, "timestep") == 3, "timestep attribute not updated correctly"
    assert getattr(vna, "lo_power") == -0.12345, "lo_power attribute should not have changed during above set_ calls"
    with raises(ValueError):
        vna.set_(_deadtime=1E-15)
        fail("Should not be able to change _deadtime attribute since starts with `_`.")


def test_running() -> None:
    """Tests that simultaneous measurements are rejected."""
    vna = new_imaginary_vna()

    # Set up a one-minute sweep in the background.
    vna.set_fsweep(1E6, 5E6, -1, points=20, timestep=3)
    with patch("project.client.application.api.TCPClient", side_effect=MockedTCPClient):
        run_background = Thread(target=vna.run, name="vna_run")
        run_background.start()

        # Try a new measurement.
        with raises(ValueError):
            vna.run()
            fail("Should not be able to start new measurement by raising ValueError!")
        run_background.join()
