"""API for the SteeleLab Vector Network Analyser"""

import ipaddress as ip
from datetime import datetime, timedelta

import numpy as np
import xarray as xr

from project.client.application.conf import SLVNAConfig
from project.client.connection.tcp_client import TCPClient
from project.client.generator.base_controller import BaseSCPIGeneratorController
from project.server.helpers import printd


class SLVNA(SLVNAConfig):
    """Class to hold hardware and software configuration of VNA and the run function to execute a sweep"""

    def __init__(
        self,
        addr_soc: tuple[ip.IPv4Address | ip.IPv6Address, int] | str,
        gen_rf: BaseSCPIGeneratorController,
        gen_lo: BaseSCPIGeneratorController,
        gen_clk: BaseSCPIGeneratorController | None = None,
        **kwargs
    ) -> None:
        # If any of the mandatory parameters is None raise an exception
        if addr_soc is None or gen_rf is None or gen_lo is None:
            raise TypeError("Must specify SoC, RF generator and LO generator when creating a VNA!")

        # If the SoC address is a string but is not of the valid IP:port format raise an exception
        if isinstance(addr_soc, str):
            try:
                split = addr_soc.split(':')
                addr_soc = (ip.ip_address(split[0]), int(split[1]))
            except (IndexError, ValueError) as e:
                raise ValueError(f"Value for addr_soc {addr_soc} is not a valid IP and port!") from e

        self._running.clear()

        super().__init__(addr_soc=addr_soc, gen_rf=gen_rf, gen_lo=gen_lo, gen_clk=gen_clk, **kwargs)

    @property
    def running(self) -> bool:
        """True if the VNA is currently running a measurement. DO NOT modify any properties when True!"""
        return self._running.is_set()

    # -- ACQUISITION METHODS --
    def run(self) -> tuple[xr.Dataset, xr.Dataset]:
        """Runs a sweep according to the parameters set up before this point.
        Blocks until complete and returns an x-array Dataset with the data"""
        # This function blocks until the action configured before is completed
        # It returns an xarray dataframe with a bunch of columns and also
        # an xarray with the current configuration and state of the VNA.
        # Selection depends on sweep type??

        # Check if we're ready to do a sweep
        self._ready_checks()

        # Do the appropriate sweep
        self._running.set()
        if self.sweep_mode == "frequency":
            results, config = self._fsweep()
        else:
            self._running.clear()
            raise NotImplementedError(f"SLVNA.run() is not implemented yet for mode '{self.sweep_mode}'!")
        self._running.clear()

        # Return the results alongside the configuration used to acquire them
        return results, config

    def _fsweep(self) -> tuple[xr.Dataset, xr.Dataset]:
        if self.gen_clk is None:
            raise NotImplementedError("fsweep() not implemented without clock generator!")

        with self.gen_rf, self.gen_lo, self.gen_clk:  # Connect to generators
            printd(f"Connected with {self.gen_rf.name} as RF generator.")
            printd(f"Connected with {self.gen_lo.name} as LO generator.")
            printd(f"Connected with {self.gen_clk.name} as clock generator.")
            with TCPClient(host=str(self.addr_soc[0]), port=self.addr_soc[1]) as tcp:  # Connect to SoC
                printd(f"Connected with {self.addr_soc[0]}:{self.addr_soc[1]} as SoC.")

                # RF signal through DuT
                self.gen_rf.fsweep(self.start_freq, self.stop_freq, self.power, self.points, self.timestep)
                # LO signal to the mixers
                self.gen_lo.fsweep(
                    self.start_freq + self.ifreq, self.stop_freq + self.ifreq, self.lo_power, self.points, self.timestep
                )
                # Clock signal to the SoC (turns on immediately to process configuration)
                if self.gen_clk is not None:
                    self.gen_clk.continuous_wave(self.socclk_freq, self.socclk_power)
                    self.gen_clk.rf_on()

                printd("Configured generators!")

                # Configure SoC
                tcp.send_tpp(self.timestep)
                tcp.send_dead_time(self._deadtime)
                tcp.send_trigger_length(self._triglen)
                tcp.send_trigger_config(
                    trig_nr=0,
                    positive=self._rf_cap["trigger"]["polarity"],
                    sweep=self._rf_cap["trigger"]["first"],
                    step=self._rf_cap["trigger"]["remaining"]
                )
                tcp.send_trigger_config(
                    trig_nr=1,
                    positive=self._lo_cap["trigger"]["polarity"],
                    sweep=self._lo_cap["trigger"]["first"],
                    step=self._lo_cap["trigger"]["remaining"]
                )

                # Prepare empty data buffer
                data = np.empty((self.points, 4))

                # Log before acquisition
                start_temperature = tcp.get_server_cpu_temp()
                start_time = datetime.now()
                printd(f"Starting acquisition at {start_time}, ETA {start_time + timedelta(seconds=self.timestep*self.points)} "\
                      f"({self.timestep*self.points:.2f}s). SoC temperature {start_temperature}C.")

                # Enable output of the generators and start acquisition
                self.gen_rf.rf_on()
                self.gen_lo.rf_on()
                tcp.start_acquisition()

                # Request data via TCP and put it in the data buffer until we have received all points
                points_done = 0
                while points_done < self.points:
                    # Receive new data and check how many points we got
                    # (don't need to round because tcp.request_data() returns whole number of points)
                    voltages = np.array(tcp.request_data())
                    points_received = len(voltages) // 4

                    # Discard unnecessary data from last packet
                    points_todo = self.points - points_done
                    if points_received > points_todo:
                        voltages = voltages[:4 * points_todo]
                        points_received = points_todo

                    # Save data and update points_done
                    data[points_done:points_done + points_received] = voltages.reshape(points_received, 4)
                    points_done += points_received

                # Loop is done, stop acquisition and turn generators off again
                tcp.stop_acquisition()
                self.gen_rf.rf_off()
                self.gen_lo.rf_off()

                # Log end of acquisition
                stop_time = datetime.now()
                stop_temperature = tcp.get_server_cpu_temp()
                printd(f"Done acquiring at {stop_time}, took {stop_time-start_time} total. "\
                      f"SoC temperature {stop_temperature}C.")

                # Turn off SoC clock last
                if self.gen_clk is not None:
                    self.gen_clk.rf_off()

        # Calculate derived values
        t = np.arange(self.points, dtype=np.float64) * self.timestep
        f = np.linspace(self.start_freq, self.stop_freq, self.points)
        output = self._expand_data(t, f, data)

        # Construct metadata dataset
        meta = self.get_config_data()
        meta["start_time"] = str(start_time)
        meta["stop_time"] = str(stop_time)
        meta["start_temperature"] = start_temperature
        meta["stop_temperature"] = stop_temperature

        return output, meta

    # -- NON-BLOCKING ACQUISITION METHODS --
    def start(self) -> None:
        """Starts a non-blocking measurement. Use SLVNA.get() to get unread data. 
        Use SLVNA.running to check status, SLVNA.stop() to stop/cancel the measurement.
        The measurement stops automatically when the sweep is finished.
        IMPORTANT: this method is stateful! It is not allowed to make changes to the VNA object
        after calling this!"""
        raise NotImplementedError("SLVNA.start() is not implemented yet!")

    def get(self) -> xr.Dataset:
        """Gets unread data from the queue during a non-blocking measurement.
        IMPORTANT: this method is stateful, it can only be called between calls to start() and stop()!"""
        raise NotImplementedError("SLVNA.get() is not implemented yet!")

    def stop(self) -> xr.Dataset:
        """Stops a currently running measurement and returns any remaining samples.
        IMPORTANT: this method ends statefulness, changes may be made to the VNA object after calling this."""
        raise NotImplementedError("SLVNA.stop() is not implemented yet!")

    # -- OTHER --
    def setup_test(self) -> bool:
        """Run a quick frequency sweep and raise exception/warning if something looks off"""
        # Run _ready_checks() to verify all user parameters
        self._ready_checks()

        # Save parameters, perform a small sweep, restore parameters
        user_config = self.points, self.timestep, self.sweep_mode
        self.points, self.timestep, self.sweep_mode = 10, 0.005, "frequency"
        self._running.set()
        results = self._fsweep()[0]
        self._running.clear()
        self.points, self.timestep, self.sweep_mode = user_config

        # Analyse results from quick sweep
        assert np.all(results["DUT_mag_V"] > 1E-4), "Low power on DUT port!"
        assert np.all(results["REF_mag_V"] > 1E-4), "Low power on REF port!"
        assert np.all(results["S_21_mag"] < 1E2), "Higher DUT return than expected!"

        # If we made it this far the test was succesful!
        return True

    def __del__(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"SLVNA({self.__dict__})"

    def __str__(self) -> str:
        return f"SteeleLab VNA object, sweep mode {self.sweep_mode}"

    # -- INTERNAL --
    @staticmethod
    def _unwrap_phase(phase_array: np.ndarray, first_freq: float, last_freq: float) -> np.ndarray:
        """Unwraps the phase array in radians and adds the average slope to it."""
        ph_unwrapped = np.unwrap(phase_array)
        first_ph, last_ph = ph_unwrapped[[0, -1]]
        avg_slope = (last_ph - first_ph) / (last_freq - first_freq)
        return ph_unwrapped - np.linspace(0, last_freq - first_freq, num=ph_unwrapped.shape[0]) * avg_slope

    @staticmethod
    def _expand_data(t: np.ndarray, f: np.ndarray, data: np.ndarray) -> xr.Dataset:
        # Caculate phasors for DUT, REF and S21
        p_dut = (data[:, 0] + 1j * data[:, 1]).astype(np.complex128)
        p_ref = (data[:, 2] + 1j * data[:, 3]).astype(np.complex128)
        S_21 = (p_dut / p_ref) ** 2  # S_21 is a power and p (phasors) are voltages, so square the ratio.
        # TODO is phase correct? amount of peaks?

        # Derive values for DUT
        DUT_re_V = np.real(p_dut).astype(np.float64)  # Also I_dut
        DUT_im_V = np.imag(p_dut).astype(np.float64)  # Also Q_dut
        DUT_mag_V = np.abs(p_dut).astype(np.float64)
        DUT_mag_dBm = (20 * np.log10(DUT_mag_V) + 10).astype(np.float64)
        DUT_phase = np.angle(p_dut).astype(np.float64)

        # Derive values for REF
        REF_re_V = np.real(p_ref).astype(np.float64)  # Also I_ref
        REF_im_V = np.imag(p_ref).astype(np.float64)  # Also Q_ref
        REF_mag_V = np.abs(p_ref).astype(np.float64)
        REF_mag_dBm = (20 * np.log10(REF_mag_V) + 10).astype(np.float64)
        REF_phase = np.angle(p_ref).astype(np.float64)

        # Derive values for S21
        S_21_re = np.real(S_21).astype(np.float64)
        S_21_im = np.imag(S_21).astype(np.float64)
        S_21_mag = np.abs(S_21).astype(np.float64)
        S_21_mag_dB = 10 * np.log10(S_21_mag).astype(np.float64)
        S_21_phase = np.angle(S_21).astype(np.float64)
        S_21_phase_unwrapped = SLVNA._unwrap_phase(S_21_phase, *f[[0, -1]])

        # Other values
        # TODO: spectrum, group delay
        # Spectrum may need overlay change? (sync deadtime to IF to keep phase) (or not because internal IF is continuous??)

        # Combine into dataset
        return xr.Dataset({
            "f": f,
            "t": t,  # t maps 1:1 to f but I don't know how to do that in xarray :/
            "P_dut": ("f", p_dut),
            "P_ref": ("f", p_ref),
            "S_21": ("f", S_21),
            "DUT_re_V": ("f", DUT_re_V),
            "DUT_im_V": ("f", DUT_im_V),
            "DUT_mag_V": ("f", DUT_mag_V),
            "DUT_mag_dBm": ("f", DUT_mag_dBm),
            "DUT_phase": ("f", DUT_phase),
            "REF_re_V": ("f", REF_re_V),
            "REF_im_V": ("f", REF_im_V),
            "REF_mag_V": ("f", REF_mag_V),
            "REF_mag_dBm": ("f", REF_mag_dBm),
            "REF_phase": ("f", REF_phase),
            "S_21_re": ("f", S_21_re),
            "S_21_im": ("f", S_21_im),
            "S_21_mag": ("f", S_21_mag),
            "S_21_mag_dB": ("f", S_21_mag_dB),
            "S_21_phase": ("f", S_21_phase),
            "S_21_phase_unwrapped": ("f", S_21_phase_unwrapped),
        })
