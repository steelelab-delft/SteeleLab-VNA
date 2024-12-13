"""Module containing a generator controller in a form of an abstract base class,
indicating which functionality a new controller class for a custom generator
at least requires.
"""

from abc import ABC, abstractmethod


class BaseSCPIGeneratorController(ABC):
    """Contains the methods required for any SCPI generator controller used in the SLVNA project."""

    DEADTIME: float = 1E12
    """Generator is switching between frequencies during its dead time (in seconds), meaning acquired data is inconsistent."""

    def __init__(self, resource_addr: str) -> None:
        """The generator must cache a name!"""
        self.name = resource_addr

    def __repr__(self) -> str:
        """Each generator should have an identifying name, queried with the SCPI '*IDN?'."""
        return self.name

    @staticmethod
    @abstractmethod
    def capabilities() -> dict:
        """Returns a dict of capabilities and configuration requests."""
        return {
            "operations": {
            BaseSCPIGeneratorController.continuous_wave: False,
            BaseSCPIGeneratorController.fsweep: False,
            BaseSCPIGeneratorController.psweep: False
            },
            "constants": {
            BaseSCPIGeneratorController.DEADTIME: BaseSCPIGeneratorController.DEADTIME
            },
            "trigger": {
            "length": 10E-6,
            "polarity": True,
            "first": True,
            "remaining": True
            }
        }

    @abstractmethod
    def continuous_wave(self, freq: float, power: float) -> None:
        """Configures a fixed frequency (Hz) at fixed power (dBm)."""

    def fsweep(self, start_freq: float, stop_freq: float, power: float, points: float, timestep: float) -> None:
        """Configures a hardware frequency sweep. Not an abstract method since not all generators support it."""

    def psweep(self, freq: float, start_power: float, stop_power: float, points: float, timestep: float) -> None:
        """Configures a hardware power sweep. Not an abstract method since not all generators support it."""

    @abstractmethod
    def query(self, parameter: str) -> float | str:
        """Queries the generator with a Standard Command for Programmable Instruments (SCPI).
        Returns a floating-point value or a string.
        """

    @abstractmethod
    def rf_on(self) -> None:
        """Turns on RF output and starts the programmed sequence."""

    @abstractmethod
    def rf_off(self) -> None:
        """Stops the programmed sequence and turns off RF output."""

    @abstractmethod
    def configure_trigger(self, enabled: bool | None = None, on_each_point: bool | None = None) -> None:
        """Configures the trigger settings for this generator.

        Args:
            enabled (bool): whether to accept external triggers;
            on_each_point (bool | None, optional): whether to enable point (step) triggering. Defaults to None.
        """

    @abstractmethod
    def configure_ref_osc(
        self,
        ref_out_enabled: bool | None = None,
        ext_ref_listen: bool | None = None,
        out_freq: float | None = None,
        in_freq: float | None = None
    ) -> None:
        """Configures the reference oscillator input and output for this generator.

        Args:
            ref_out_enabled (bool | None, optional): whether to output an external clock signal of frequency `out_freq`.
                Defaults to None;
            ext_ref_listen (bool | None, optional): whether to listen to an external clock signal input of frequency
                `in_freq`. Defaults to None;
            out_freq (float | None, optional): frequency in hertz for external clock output. Defaults to None;
            in_freq (float | None, optional): expected external clock frequency in hertz. Defaults to None.
        """

    @abstractmethod
    def start(self) -> None:
        """Makes a connection to the generator and initialises."""

    @abstractmethod
    def stop(self) -> None:
        """Cleans up and ends connection to the generator."""

    def is_locked(self) -> bool:
        """Checks if the generator is locked to an external clock (or internal clock if ROSC:SOUR INT).
        Recommended to implement and call in `rf_on`; not used by the SLVNA API.
        """

    def network_ping_rtt(self) -> tuple[str, float | None]:
        """If supported, pings generator via the network.
        Returns IP address and average round trip time.
        """

    @abstractmethod
    def __enter__(self) -> "BaseSCPIGeneratorController":
        """Calls self.start()."""

    @abstractmethod
    def __exit__(self, *args, **kwargs) -> None:
        """Calls self.stop()."""
