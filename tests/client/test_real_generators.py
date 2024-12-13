import pytest
import pyvisa

from project.client.generator.anapico import APUASYN20Controller


@pytest.mark.skip()
def test_real_anapico() -> None:
    power = 23  # dBm
    freq = 5000E6  # for single freq, Hz
    ifreq = 7.8125E6  # IF for IQ decomposition, Hz
    start_freq = 7000E6  # Hz
    stop_freq = 8000E6  # Hz
    timestep = 100E-6  # time step in seconds (when not triggered externally)
    points = 1001  # number of points in sweep
    with APUASYN20Controller("TCPIP::172.19.20.24::INSTR") as pico24_rf:
        with APUASYN20Controller("TCPIP::172.19.20.25::INSTR") as pico25_lo:

            pico24_rf.configure_trigger(enabled=True, on_each_point=True)
            pico24_rf.fsweep(start_freq, stop_freq, power, points, timestep)
            pico24_rf.rf_on()
            # pico24_rf.continuous_wave(freq, power)

            pico24_rf.configure_trigger(enabled=True, on_each_point=True)
            pico25_lo.fsweep(start_freq + ifreq, stop_freq + ifreq, power, points, timestep)
            pico25_lo.rf_on()
            # pico25_lo.continuous_wave(freq + ifreq, power)


def test_anapico_without_connect() -> None:
    """Tests passing keyword arguments to generator initialiser."""
    invalid_addr = "INSTR::^4*[@8m\n,b;3_!"
    APUASYN20Controller(invalid_addr)
    with pytest.raises(ValueError):
        APUASYN20Controller(invalid_addr, this_is_an_invalid_keyword="argument")
        pytest.fail("Should have captured the invalid keyword argument.")
    with pytest.raises(ValueError):
        APUASYN20Controller(invalid_addr, ref_out_enabled=False, another_invalid="argument")
        pytest.fail("Should have captured the invalid keyword argument.")
    with pytest.raises(pyvisa.errors.Error):
        APUASYN20Controller(invalid_addr, ref_out_enabled=True)
        pytest.fail(f"Should have raised pyvisa error since cannot connect to {invalid_addr}.")
