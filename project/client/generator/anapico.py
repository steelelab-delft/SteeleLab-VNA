"""Module for controlling RF generators from AnaPico"""

from inspect import signature
from re import sub
from sys import platform
from typing import Callable
from warnings import warn

import pyvisa

from project.client.connection.ping import network_ping_average
from project.client.generator.base_controller import BaseSCPIGeneratorController


class APUASYN20Controller(BaseSCPIGeneratorController):
    """Programmer manual: https://www.anapico.com/download/pm_signal-generators/?wpdmdl=6829&refresh=665ecb7bc31c21717488507"""

    OUT_REF_FREQ_RANGE: tuple[float, float] = (100E6, 100E6)
    """Range of frequencies this generator supports in its output clock reference."""

    def __init__(self, resource_addr: str, **kwargs) -> None:
        """Initialise an APUASYN20 generator with VISA `resource_addr`
        and optionally configure its reference oscillator settings via keyword arguments.
        """
        super().__init__(f"APUASYN20 @ {resource_addr}, not yet connected.")
        self.resource_addr = resource_addr
        self.resource_info = "A not yet connected APUASYN20 RF generator."
        self.gen: pyvisa.Resource | None = None
        self.mode: Callable | None = None

        # Process kwargs.
        possible_kwarg_keys = set(signature(self.configure_ref_osc).parameters.keys())
        if not set(kwargs.keys()).issubset(possible_kwarg_keys):
            raise ValueError(
                f"{self} does not support kwargs "
                f"{set(kwargs.keys()).difference(possible_kwarg_keys)}, only {possible_kwarg_keys}."
            )

        # Send reference configuration by setting up a temporary connection with the generator.
        if kwargs:
            with self:  # calls self.__enter__ and self.__exit__
                self.configure_ref_osc(**kwargs)

    def __repr__(self) -> str:
        """Representation of this generator with all its current settings."""
        if self.gen is None:
            return f"APUASYN20Controller({self.__dict__})"
        return (
            f"APUASYN20Controller(\n\t{self.__dict__},\n\tlocked={self.is_locked()},\n\t" +
            f"trig_type={self.gen.query('TRIG_TYPE?')}),\n\tosc={self.gen.query('ROSC_SOUR?')}\n)"
        )

    @staticmethod
    def capabilities() -> dict:
        return {
            "operations": {
            BaseSCPIGeneratorController.continuous_wave: True,
            BaseSCPIGeneratorController.fsweep: True,
            BaseSCPIGeneratorController.psweep: False
            },
            "constants": {
            BaseSCPIGeneratorController.DEADTIME: 500E-6
            },
            "trigger": {
            "length": 10E-6,
            "polarity": True,
            "first": True,
            "remaining": True
            }
        }

    def continuous_wave(self, freq: float, power: float) -> None:
        self._check_conn()

        self.gen.write(f"POW:AMPL {power}DBM")  # RF output power in dBm
        self.gen.write("FREQ:MODE FIX")  # frequency mode: fixed frequency
        self.gen.write(f"SOUR:FREQ {freq}Hz")  # frequency in Hz
        self.mode = APUASYN20Controller.continuous_wave

    def fsweep(self, start_freq: float, stop_freq: float, power: float, points: float, timestep: float) -> None:
        """Configures a hardware frequency sweep (without starting it).

        Args:
            start_freq (float): first frequency in hertz;
            stop_freq (float): last frequency in hertz. If smaller than `start_freq`, sweep direction is reversed;
            power (float): RF output power in dBm;
            points (float): number of points in the sweep. Frequency step is calculated by generator;
            timestep (float): time per point in seconds (ignored if using an external trigger). Generator accepts dwell time,
                calculated by subtracting constant deadtime (from `APUASYN20Controller.capabilities`) from `timestep`.
        """
        self._check_conn()

        if stop_freq < start_freq:
            start_freq, stop_freq = stop_freq, start_freq
            self.gen.write("SWE:DIR DOWN")  # from highest to lowest frequency
        self.gen.write(f"POW:AMPL {power}DBM")  # RF output power in dBm
        self.gen.write(f"FREQ:STAR {start_freq}Hz")  # start frequency in hertz
        self.gen.write(f"FREQ:STOP {stop_freq}Hz")  # stop frequency in hertz
        self.gen.write(f"SWE:POIN {points}")  # number of points in the sweep
        deadtime = APUASYN20Controller.capabilities().get("deadtime", 0)
        self.gen.write(f"SWE:DWEL {timestep - deadtime}s")
        self.mode = APUASYN20Controller.fsweep  # Set mode here because FREQ:MODE SWE has to be sent later.

    def query(self, parameter: str) -> float | str:
        self._check_conn()

        result = self.gen.query(parameter)
        try:
            return float(result)
        except (ValueError, OverflowError):
            return result

    def rf_on(self) -> None:
        self._check_conn()
        if not self.is_locked():
            warn(f"Turning RF on for {self.gen} that is not locked!")

        # Enable the RF output. Important: this has to be done before FREQ:MODE SWE!
        self.gen.write("OUTP 1")

        # Set mode based on instance attribute.
        if self.mode == APUASYN20Controller.fsweep:
            self.gen.write("FREQ:MODE SWE")

    def rf_off(self) -> None:
        self._check_conn()
        self.gen.write("OUTP OFF")

    def configure_trigger(self, enabled: bool | None = None, on_each_point: bool | None = None) -> None:
        self._check_conn()

        if enabled is not None:  # trigger source: external (requires rising edge on trigger)
            self.gen.write(f"TRIG:SOUR {'EXT' if enabled else 'IMM'}")  # or immediate (no trigger)
        if on_each_point is not None:  # trigger type: each trigger starts step (POINT)
            self.gen.write(f"TRIG:TYPE {'POINT' if on_each_point else 'NORM'}")  # or sweep (NORM)
            self.gen.write("INIT:CONT ON")  # trigger arming: always armed after first point

    def configure_ref_osc(
        self,
        ref_out_enabled: bool | None = None,
        ext_ref_listen: bool | None = None,
        out_freq: float | None = None,
        in_freq: float | None = None
    ) -> None:
        self._check_conn()

        if ref_out_enabled is not None:
            self.gen.write(f"ROSC:OUTP:STAT {'ON' if ref_out_enabled else 'OFF'}")
        if ext_ref_listen is not None:
            self.gen.write(f"ROSC:SOUR {'EXT' if ext_ref_listen else 'INT'}")  # set external reference clock
        if in_freq is not None:
            self.gen.write(f"ROSC:EXT:FREQ {in_freq}Hz")
        if out_freq is not None:
            low, high = APUASYN20Controller.OUT_REF_FREQ_RANGE
            if low < out_freq or out_freq > high:
                raise ValueError(
                    f"{self.name} does not support output reference frequency {out_freq}, "
                    f"only in range {APUASYN20Controller.OUT_REF_FREQ_RANGE}."
                )
            self.gen.write(f"ROSC:OUTP:FREQ {out_freq}Hz")

    def start(self) -> None:
        if self.gen is not None:
            warn(f"Already initialised connection to {self} before, skipping start() method.")
            return  # Already initialised before.
        if platform.startswith("win"):  # Windows
            rm = pyvisa.ResourceManager()
        elif platform.startswith("darwin"):  # MacOS
            rm = pyvisa.ResourceManager("@py")
        else:
            raise pyvisa.OSNotSupported(f"Platform '{platform}' not supported to control {self}.")
        try:
            self.gen = rm.open_resource(self.resource_addr)

        # Find possible Visa addresses and try pinging the device if it has an IP address in its resource string.
        except pyvisa.errors.VisaIOError as err:
            resources = rm.list_resources(self.name)
            ip, rtt = self.network_ping_rtt()
            raise pyvisa.errors.Error(
                f"{err}\nFailed to connect to {self.resource_addr}. "
                f"Found these VISA resources:\n{resources}\n"
                f"Ping average round trip time to {ip}: {rtt} ms" if rtt is not None else ""
            ) from err

        self.gen.write("*RST")  # reset the generator, otherwise power cannot be modified
        self.gen.write("*CLS")  # clear status byte

        # Update the generator name and info if connected.
        self.name = str(self.query("*IDN?"))
        self.resource_info = self.gen.resource_info

        # Initialise default trigger configuration.
        self.configure_trigger(enabled=True, on_each_point=True)

    def stop(self) -> None:
        if self.gen is not None:
            try:
                _ = self.gen.session
                self.rf_off()
                self.gen.close()
            except pyvisa.errors.InvalidSession:
                return  # for instance when connection opened twice
            finally:
                self.gen = None

    def is_locked(self) -> bool:
        return float(self.query("ROSC:LOCK?")) == 1.  # Can only ever be 0.0 or 1.0.

    def _check_conn(self) -> None:
        """Checks if the user connected to the generator to be able to send SCPI."""
        if self.gen is None:
            raise ConnectionError(f"Not yet connected to {self}! Call .start() first.")

    def network_ping_rtt(self) -> tuple[str, float | None]:
        """Pings the generator, if `self.resource_addr` contains an IPv4 address.
        Returns extracted IPv4 address and average round trip time in seconds (else None).
        """
        ip_address = sub(r"([^0-9]*)(((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4})(.*)", r"\2", self.resource_addr)
        if ip_address != self.resource_addr:
            return ip_address, 1E-3 * network_ping_average(ip_address)
        return f"[no ipv4 address inside {self.resource_addr}]", None

    def __enter__(self) -> "BaseSCPIGeneratorController":
        self.start()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.stop()
