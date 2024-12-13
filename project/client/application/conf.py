"""Configuration class for the SLVNA"""

import ipaddress as ip
import threading as td
from dataclasses import dataclass
from datetime import datetime
from logging import warning
from math import ceil
from typing import ClassVar

import xarray as xr

from project.client.generator.base_controller import BaseSCPIGeneratorController


@dataclass
class SLVNAConfig:
    """Dataclass to hold the hardware and parameter configuration of a VNA"""
    CONSTANT = 0
    addr_soc: tuple[ip.IPv4Address | ip.IPv6Address, int]
    gen_rf: BaseSCPIGeneratorController
    gen_lo: BaseSCPIGeneratorController
    gen_clk: BaseSCPIGeneratorController | None

    start_freq: float | None = None  # [Hz] Start frequency of the RF generator when doing a frequency sweep
    stop_freq: float | None = None  # [Hz] Stop frequency of the RF generator when doing a frequency sweep
    freq: float | None = None  # [Hz] Fixed frequency of the RF generator if sweeping some other parameter

    start_power: float | None = None  # [dBm] Start power of the RF generator when doing a power sweep
    stop_power: float | None = None  # [dBm] Stop power of the RF generator when doing a power sweep
    power: float | None = None  # [dBm] Fixed power of the RF generator if sweeping some other parameter

    points: int | None = None  # [-] Amount of points in a 1D sweep
    power_points: int | None = None  # [-] Amount of powers to test when doing a 2D sweep
    timestep: float | None = None  # [s] Measurement time before switching frequency/power (includes deadtime!)

    # Temporaries
    _rf_cap: dict = None  # [-] Capabilities dict of the RF generator. Set by SLVNA._ready_check()
    _lo_cap: dict = None  # [-] Capabilities dict of the LO generator. Set by SLVNA._ready_check()
    _deadtime: float = None  # [s] Deadtime at the beginning of each point. Set by SLVNA._ready_check()
    _triglen: float = None  # [s] Trigger pulse length. Set by SLVNA._ready_check()

    # Advanced settings, should really just be left alone
    sweep_mode: str | None = None  # [-] Selected sweep mode, of
    # ["time", "continuouswave", "frequency", "power", "2d", "table"]
    ifreq: float = 7.8125E6  # [Hz] Intermediate frequency (IF) used by the VNA, default to 7.8125MHz
    lo_power: float = 23.0  # [dBm] Power of the LO generator, default to 23dBm
    socclk_freq: float = 125E6  # [Hz] The frequency of the SoC clock
    socclk_power: float = 10.0  # [dBm] Power of the SoC clock

    _running: td.Event = td.Event()  # [-] VNA currently measuring. Do not modify any properties when set!

    HIGH_PING: ClassVar[float] = 20E-3  # [s] When ping to generator rtt is above this threshold, warning/raise exception.

    # -- CONFIGURATION METHODS --
    def set_(self, **kwargs) -> None:
        """Sets any configuration parameter available, except for the ones starting with an `_`."""
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)
            elif key.startswith("_"):
                raise ValueError(f"Cannot set protected keyword argument `{key}={value}`.")
            else:
                raise ValueError(f"Unknown keyword argument `{key}={value}`.")

    def set_fsweep(
        self,
        start_freq: float,
        stop_freq: float,
        power: float,
        freqstep: float = None,
        points: int = None,
        time: float = None,
        timestep: float = None,
        ifbw: float = None,
        **kwargs
    ) -> None:
        """Set up a frequency sweep"""
        # Copy over the mandatory ones
        self.start_freq = float(start_freq)
        self.stop_freq = float(stop_freq)
        self.power = float(power)
        self.sweep_mode = "frequency"

        # Set all keyword arguments.
        self.set_(**kwargs)

        # Figure out what self.timestep should be
        if (timestep is not None and ifbw is None):
            # If timestep was specified:
            self.timestep = float(timestep)
        elif (timestep is None and ifbw is not None):
            # If ifbw was specified:
            self.timestep = 1 / ifbw
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (timestep, ifbw) in set_fsweep()!")

        # Figure out what self.points should be
        if (freqstep is not None and points is None and time is None):
            # If freqstep was specified:
            # Calculate how many points would fit in the range
            points_in_range = (self.stop_freq - self.start_freq) / freqstep
            self.points = ceil(points_in_range)
            # If not an integer amount, change stop frequency and warning user
            if (points_in_range % 1) != 0:
                warning("Changing stop frequency to fit specified frequency step evenly!")
                self.stop_freq = self.start_freq + self.points * freqstep
        elif (freqstep is None and points is not None and time is None):
            # If points was specified:
            self.points = round(points)
        elif (freqstep is None and points is None and time is not None):
            # If time was specified:
            # Calculate how many points would fit in the range and round
            self.points = round(time / self.timestep)
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (freqstep, points, time) in set_fsweep()!")

    def set_psweep(
        self,
        freq: float,
        start_power: float,
        stop_power: float,
        points: int = None,
        time: float = None,
        timestep: float = None,
        ifbw: float = None,
        **kwargs
    ) -> None:
        """Set up a power sweep"""
        # Copy over the mandatory ones
        self.freq = float(freq)
        self.start_power = float(start_power)
        self.stop_power = float(stop_power)
        self.sweep_mode = "power"

        # Set all keyword arguments.
        self.set_(**kwargs)

        # Figure out what self.timestep should be
        if (timestep is not None and ifbw is None):
            # If timestep was specified:
            self.timestep = float(timestep)
        elif (timestep is None and ifbw is not None):
            # If ifbw was specified:
            self.timestep = 1 / ifbw
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (timestep, ifbw) in set_psweep()!")

        # Figure out what self.points should be
        # NOTE: set_psweep does NOT allow specifying power step as this leads to too much ambiguity
        if (points is not None and time is None):
            # If points was specified:
            self.points = round(points)
        elif (points is None and time is not None):
            # If time was specified:
            # Calculate how many points would fit in the range and round up
            self.points = round(time / self.timestep)
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (points, time) in set_psweep()!")

    def set_cw(
        self,
        freq: float = None,
        power: float = None,
        points: int = None,
        time: float = None,
        timestep: float = None,
        ifbw: float = None,
        **kwargs
    ) -> None:
        """Set up a continuous wave measurement"""
        # Copy over the mandatory ones
        self.freq = float(freq)
        self.power = float(power)
        self.sweep_mode = "continouswave"

        # Set all keyword arguments.
        self.set_(**kwargs)

        # Figure out what self.timestep should be
        if (timestep is not None and ifbw is None):
            # If timestep was specified:
            self.timestep = float(timestep)
        elif (timestep is None and ifbw is not None):
            # If ifbw was specified:
            self.timestep = 1 / ifbw
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (timestep, ifbw) in set_cw()!")

        # Figure out what self.points should be
        if (points is not None and time is None):
            # If points was specified:
            self.points = round(points)
        elif (points is None and time is not None):
            # If time was specified:
            self.points = round(time / self.timestep)
        else:
            # If none or too many were specified:
            raise ValueError("Specify one of (points, time) in set_cw()!")

    # -- OTHER --
    def set_config_data(self, config: xr.Dataset) -> None:
        """Applies the configuration specified in the given xarray. Intended for use with
        xarrays generated by SLVNA.get_config_data()."""
        # Note to self: discard any state stuff!
        raise NotImplementedError("SLVNA.set_config_data() is not implemented yet!")

    def get_config_data(self) -> xr.Dataset:
        """Returns a x-array Dataset containing the configuration and state of the VNA."""
        # Create empty set
        config = xr.Dataset()

        # Copy over the configuration
        d = self.__dict__
        for key in d:
            if key in {'addr_soc'}:
                # Format address of SoC as string
                config[key] = f"{d[key][0]}:{d[key][1]}"
            elif key in {'gen_rf', 'gen_lo', 'gen_clk'}:
                # Look up names of generators
                config[key] = repr(d[key])
            elif key in {"_rf_cap", "_lo_cap", "_running"}:
                # Discard some temporaries
                continue
            else:
                # Just copy all other parameters
                config[key] = d[key]

        config["time"] = str(datetime.now())

        return config

    # -- INTERNAL --
    def _ready_checks(self, fail_on_warning: bool = False) -> None:
        """Performs various readiness checks. Returns None if succesfull, raises the appropriate exceptions if not.
        Can also raise several warningings or turn these into exceptions."""

        # Verify no measurement is running at this moment (if threaded).
        if self.running:
            raise ValueError("VNA not ready; currently performing a measurement!")

        # Make set of required properties for this mode
        to_check = {self.addr_soc, self.gen_rf, self.gen_lo, self.timestep}
        if self.sweep_mode == "frequency":
            to_check.update({self.start_freq, self.stop_freq, self.points, self.power})
        elif self.sweep_mode == "continuouswave":
            to_check.update({self.freq, self.points, self.power})
        elif self.sweep_mode == "time":
            to_check.update({self.freq, self.points})
        elif self.sweep_mode == "power":
            to_check.update({self.start_power, self.stop_power, self.points, self.freq})
        elif self.sweep_mode == "2d":
            to_check.update({
                self.start_freq, self.stop_freq, self.points, self.start_power, self.stop_power, self.power_points
            })
        else:
            raise NotImplementedError(f"Mode {self.sweep_mode} not implemented!")

        # Check if every required property is specified
        for v in to_check:
            if v is None:
                raise ValueError(f"Not all parameters needed for mode {self.sweep_mode} specified!")

        # warning if no SoC clock generator is specified
        if self.gen_clk is None:
            if fail_on_warning: raise ValueError("Red Pitaya clock generator not specified!")
            else: warning("Red Pitaya clock generator not specified, assuming it has an external clock source!")

        # Check connection to generators as PyVISA doesn't like high ping.
        for gen in (self.gen_rf, self.gen_lo, self.gen_clk):
            if gen is not None:
                rtt = gen.network_ping_rtt()[1]
                if rtt < SLVNAConfig.HIGH_PING:
                    continue
                if fail_on_warning:
                    raise ValueError(
                        f"High ping round trip time ({rtt} s) to {gen}; "
                        "unable to reliably control via PyVISA!"
                    )
                else:
                    warning(f"High ping round trip time ({rtt} s) to {gen}; control could be unreliable!")

        # Check if generators can do the required sweep.
        match self.sweep_mode:
            case "frequency" | "power":
                key = BaseSCPIGeneratorController.fsweep if "frequency" else BaseSCPIGeneratorController.psweep
                if not self.gen_rf.capabilities()["operations"][key]:
                    raise NotImplementedError(f"RF generator {self.gen_rf} cannot perform fsweep!")
                if not self.gen_lo.capabilities()["operations"][key]:
                    raise NotImplementedError(f"LO generator {self.gen_lo} cannot perform fsweep!")
            case _:
                warning(f"Ready checks for sweep mode '{self.sweep_mode}' are not implemented.")
        if self.gen_clk is not None and not self.gen_clk.capabilities()["operations"][
            BaseSCPIGeneratorController.continuous_wave]:
            raise NotImplementedError(f"Clock generator {self.gen_clk} cannot do continuous wave!")

        # Get generator capabilities
        self._rf_cap = self.gen_rf.capabilities()
        self._lo_cap = self.gen_lo.capabilities()

        # Use capabilities to set _deadtime and _triglen
        self._deadtime = max(
            self._rf_cap["constants"][BaseSCPIGeneratorController.DEADTIME],
            self._lo_cap["constants"][BaseSCPIGeneratorController.DEADTIME]
        )
        self._triglen = max(self._rf_cap["trigger"]["length"], self._lo_cap["trigger"]["length"])

        # Check some properties for feasibility
        if self.timestep <= self._deadtime:
            raise ValueError(f"Timestep {self.timestep} should be larger than dead time {self._deadtime}.")
        if self.timestep <= self._triglen:
            raise ValueError(f"Timestep {self.timestep} should be larger than trigger pulse length {self._triglen}.")
