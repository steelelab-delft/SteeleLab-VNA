"""Mocked generator control module"""

from project.client.generator.base_controller import BaseSCPIGeneratorController


class MockedGenController(BaseSCPIGeneratorController):
    """Mocked controller class for testing purposes when no generator is available"""

    DEADTIME = 1E-12
    """This imaginary generator is very close to ideal (zero deadtime)."""

    def __init__(self, resource_addr: str) -> None:
        self.name = f"MockedGen @ {resource_addr}, not yet connected."
        self.gen = None

    def __repr__(self) -> str:
        """Each generator should have an identifying name, queried with the SCPI '*IDN?'."""
        return f"MockedGenController({self.__dict__})"

    @staticmethod
    def capabilities() -> dict:
        """A mocked generator is capable of doing everything."""
        return {
            "operations": {
            BaseSCPIGeneratorController.fsweep: True,
            BaseSCPIGeneratorController.psweep: True,
            BaseSCPIGeneratorController.continuous_wave: True
            },
            "constants": {
            BaseSCPIGeneratorController.DEADTIME: MockedGenController.DEADTIME
            },
            "trigger": {
            "length": 10E-6,
            "polarity": True,
            "first": True,
            "remaining": True
            }
        }

    def continuous_wave(self, freq: float, power: float) -> None:
        """Lets the mocked generator output a constant frequency."""

    def fsweep(self, start_freq: float, stop_freq: float, power: float, points: float, timestep: float) -> None:
        """Configures a hardware frequency sweep on the mocked generator."""

    def psweep(self, freq: float, start_power: float, stop_power: float, points: float, timestep: float) -> None:
        """Configures a hardware power sweep on the mocked generator."""

    def query(self, parameter: str) -> float | str:
        """Lets caller know this is a mocked generator."""
        return "mocked_generator" if parameter == "*IDN?" else -1.

    def rf_on(self) -> None:
        """Turns on the mocked RF output."""

    def rf_off(self) -> None:
        """Stops the mocked RF output."""

    def configure_trigger(self, enabled: bool | None = None, on_each_point: bool | None = None) -> None:
        """Configures the mocked trigger."""

    def configure_ref_osc(
        self,
        ref_out_enabled: bool | None = None,
        ext_ref_listen: bool | None = None,
        out_freq: float | None = None,
        in_freq: float | None = None
    ) -> None:
        """Configures the mocked reference oscillator input and output."""

    def start(self) -> None:
        """Makes a mocked connection to the generator and initialises."""
        self.gen = object()

    def stop(self) -> None:
        """Cleans up and ends connection to the generator."""

    def is_locked(self) -> bool:
        """Always imaginarily locked."""
        return True

    def network_ping_rtt(self) -> tuple[str, float | None]:
        return "1.2.3.4", 1E-12

    def __enter__(self) -> "MockedGenController":
        """Calls self.start()."""
        self.start()

    def __exit__(self, *args, **kwargs) -> None:
        """Calls self.stop()."""
        self.stop()
