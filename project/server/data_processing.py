"""Classes and functions for fetching and storing acquired data from programmable logic (PL)"""

from queue import Full, Queue
from threading import Event
from time import sleep

from pynq import MMIO, Overlay, allocate

import helpers
import numpy as np
from protocol import PLConfig, TCPCommandProtocol


class PLInterface(PLConfig):
    """Functions related to the interface between the processing subsystem (PS) and programmable logic (PL)."""

    class DMANotAllowed(Exception):
        """Special exception raised when data transfer via DMA will hang due to PL being in reset"""

    DEBUG = True
    """Whether to print debugging information"""

    def __init__(self) -> None:
        # Load overlay
        self.ol = Overlay(PLInterface.OVERLAY_PATH)
        # Create MMIO objects for config registers
        self.mmios = {key: MMIO(value) for key, value in PLInterface.MMIO_ADDRESSES_DICT.items()}
        # Create DMA object and buffer
        self.dma_channel = self.ol.dma.recvchannel
        self.dma_output_buffer = allocate(shape=(PLConfig.DMA_PACKET_LENGTH + 4, ), dtype=PLInterface.DMA_DTYPE)
        # Set state to idle
        self._enabled = False
        self._first_dma = False
        self._dma_status = 2  # default: after DMA transfer

    @property
    def points_per_transfer(self):
        """Amount of points per DMA transfer."""
        # Integer divide rounds down the 4 extra words for overflow
        return len(self.dma_output_buffer) // 12

    @points_per_transfer.setter
    def points_per_transfer(self, value):
        # Make sure we don't brick ourselves too easily
        if value < 1: value = 1
        # Write to PL
        self.write_mmio(TCPCommandProtocol.PPT, value)
        # Change buffer size (aka delete and reallocate)
        if hasattr(self, "dma_output_buffer"): del self.dma_output_buffer
        # Allocate 4 more words than technically necessary to fit
        self.dma_output_buffer = allocate(shape=(value * PLConfig.DMA_PACKET_LENGTH + 4, ), dtype=PLInterface.DMA_DTYPE)

    @property
    def enable(self):
        """Checks whether the programmable logic is enabled."""
        return self._enabled

    @enable.setter
    def enable(self, value):
        """Enables the programmable logic data acquisition.
        Only change this if previous DMA requests are properly closed!
        """
        if not isinstance(value, bool) or (self._enabled and value):
            # If not a bool or already enabled, do nothing
            return

        self.write_mmio(TCPCommandProtocol.RUN_PL, value)

        # Prepare on disable because the very first run actually doesn't need to discard data
        if not value: self._first_dma = True
        self._enabled = value
        if value: helpers.printd("Started programmable logic data acquisition.")
        else: helpers.printd("Stopped programmable logic data acquisition.")

    def get_data(self) -> np.ndarray:
        """Get data from the DMA converted to volts. Returns numpy array of floats representing voltages."""
        # The first transfer has 4 words of garbage prepended because that stays stuck in the DMA during reset
        if not self.enable:
            raise PLInterface.DMANotAllowed("[DMA] Cannot do a DMA transfer if PL isn't enabled!")

        if self._first_dma:
            if PLInterface.DEBUG: helpers.printd("First DMA data request")
            self._first_dma = False
            return self.preprocess_raw_dma_data(self._raw_dma_request(first=True))
        return self.preprocess_raw_dma_data(self._raw_dma_request(first=False))

    def _raw_dma_request(self, first):
        """Reads data from a direct memory access channel.
        First read has to be different because of a quirk with the DMA controller for Zynq chips."""
        try:
            # No timeout available in `wait`; use dma_channel.stop() outside thread to stop.
            self._dma_status = 0
            self.dma_channel.transfer(self.dma_output_buffer)
            self._dma_status = 1
            self.dma_channel.wait()
            self._dma_status = 2
        except RuntimeError as err:
            # This occurs when the programmable logic just started after reset and did not yet configure the DMA channel.
            raise PLInterface.DMANotAllowed from err
        # Cut off garbage
        if first:
            # If first skip first 4 elements that were stuck in the DMA
            return self.dma_output_buffer[4:]
        else:
            # If not first skip last 4 that weren't overwritten this transfer
            return self.dma_output_buffer[:-4]

    @staticmethod
    def preprocess_raw_dma_data(buffer) -> np.ndarray:
        """Converts sets of 3 raw words from the DMA buffer to a float representing voltage.
        Every uint64 value is divided by the corresponding count and multiplied by a conversion factor.
        """
        # volts = [
        #     (
        #         helpers.uint64_to_signed_int(
        #             int(buffer[i])  # to Python integer(first entry: unsigned 32-bit integer
        #             + (int(buffer[i + 1]) << 32)  # adding second unsigned integer shifted left 32 bits)
        #         ) / buffer[i + 2]  # dividing by third entry (count)
        #         * PLInterface.RAW_TO_VOLTS  # scaling to units of volts
        #     ) for i in range(0, len(buffer), 3)  # i = 0, 3, 6, 9
        # ]

        assert len(buffer) % 3 == 0, "[DMA] Buffer length not a multiple of 3???"

        # Allocate new buffer of float64s, output
        volts = np.empty(len(buffer) // 3, dtype=np.float64)

        # Index into volts and buffer
        for i, j in enumerate(range(0, len(buffer), 3)):
            # Create a single signed int from the first two values in the buffer
            val = helpers.uint64_to_signed_int((int(buffer[j + 1]) << 32) + int(buffer[j]))
            # Divide by the amount of samples for this value and multiply to convert to volts
            volts[i] = val / buffer[j + 2] * PLConfig.RAW_TO_VOLTS

        return volts

    def _resolve_field(self, cmd) -> tuple:
        """Resolves the location in MMIO of the field corresponding to the provided TCP command."""
        # Get field info from dict
        dict = PLInterface.MMIO_FIELD_DICT.get(cmd)
        if dict is None:
            raise KeyError(f"[MMIO] Command {cmd} does not exist in MMIO_FIELD_DICT!")
        scalar, mmio_idx, mask = dict["scale"], dict["mmio"], dict["mask"]
        # Resolve MMIO
        mmio = self.mmios[mmio_idx]
        # Little bithack to get trailing zeros of mask (https://stackoverflow.com/a/63552117)
        bitshift = (mask & -mask).bit_length() - 1
        return scalar, mmio, bitshift, mask

    def write_mmio(self, cmd, value) -> None:
        """Resolves the provided MMIO field and writes a value there."""
        # Get field information
        scalar, mmio, bitshift, mask = self._resolve_field(cmd)
        # Scale value to internal arbitrary units
        if not float(value * scalar).is_integer():
            helpers.printd(f"[MMIO] Trying to write non-integer value {value*scalar:.2f} to field {cmd}, rounding!")
        value = round(value * scalar)
        if value > (mask >> bitshift):
            raise ValueError(f"[MMIO] Value {value} is too large for field {cmd}!")
        # Merge value with the data already there
        curr_data = mmio.read()
        new_data = (curr_data & ~mask) | (value << bitshift & mask)
        # Write out new data to the register
        mmio.write(offset=0, data=new_data)
        helpers.printd(f"Wrote 0x{new_data:08x} to 0x{mmio.base_addr:08x} (command {cmd})")

    def read_mmio(self, cmd) -> float:
        """Resolves the provided MMIO field and reads its value."""
        # Get field information
        scalar, mmio, bitshift, mask = self._resolve_field(cmd)
        # Extract value from the register
        curr_data = mmio.read()
        value = (curr_data & mask) >> bitshift
        # Scale value to real units and return
        value /= scalar
        helpers.printd(f"Read {value:.2f} from 0x{mmio.base_addr:08x} (command {cmd})")
        return value

    def get_mmio_status(self) -> dict:
        """Returns dictionary with hexadecimal addresses and corresponding current binary contents of all MMIO registers."""
        return {f"0x{m.base_addr:08x}": f"0b{m.read():>032b}" for m in self.mmios.values()}

    def verify_config(self) -> None:
        """Checks using assert statements that the current MMIO configuration does not cause problems in the PL,
        such as invalid counter values leading to DMA transfers becoming impossible to perform.
        """
        dead_time = self.mmios[PLConfig.MMIO_DEAD_TIME].read()
        trigger_length = self.mmios[PLConfig.MMIO_TRIG].read() & ((1 << 24) - 1)  # lowest 24 bits of register
        tpp = self.mmios[PLConfig.MMIO_TPP].read()
        ppt = self.read_mmio(TCPCommandProtocol.PPT)
        assert ppt > 0, f"points per transfer {ppt} should be greater than zero"
        assert tpp > 0, f"time per point {tpp} should be greater than zero"
        assert dead_time > 0, f"generator dead time {dead_time} should be greater than zero"
        assert tpp > dead_time, f"time per point {tpp} should be longer than generator dead time {dead_time}"
        assert tpp > trigger_length, f"time per point {tpp} should be longer than trigger pulse length {trigger_length}"

    @property
    def dma_status(self):
        """For debugging purposes. Status code 0: when a transfer is about to start; 1: when waiting
        for the data to become available; 2: when a transfer has been completed.
        """
        return self._dma_status


class DataQueue(Queue):
    """First-in first-out structure storing acquired data"""

    MAXSIZE_BITS = 16
    """Maximum size of the queue is 2 ** BITSIZE - 1"""

    QUEUE_TIMEOUT = 50E-3
    """Timeout in seconds for waiting while getting from and putting data into the queue"""

    DEBUG = True
    """Whether to print debugging information"""

    def __init__(self):
        super().__init__(2 ** DataQueue.MAXSIZE_BITS - 1)
        # Event for telling the DataQueue to start/stop fetching, default to paused
        self.fetch = Event()
        self.fetch.clear()
        # Event for telling other threads the DataQueue is/is not paused, default to paused
        self.paused = Event()
        self.paused.set()
        # Event for telling the DataQueue to exit, default to not exit
        self.exit = Event()
        self.exit.clear()

    @property
    def starting_or_started(self):
        """True if we're currently fetching or about to start"""
        return self.fetch.is_set() or not self.paused.is_set()

    def flush(self):
        """Removes all items in the queue."""
        with self.mutex:
            # TODO: The clear() method isn't documented so we should probably do this differently
            self.queue.clear()
        if not self.empty():
            raise RuntimeError(f"[QUEUE] Emptying queue failed; size is {self.queue.qsize()} > 0.")
        if DataQueue.DEBUG: helpers.printd("[QUEUE] Queue flushed.")

    def keep_fetching(self, fetch_func):
        """Fetch via a provided function and store in the queue.
        Obeys the self.fetch and self.exit events, updates self.paused event
        """
        # Keep fetching as long as we're not exiting
        while not self.exit.is_set():
            # If we're instructed to pause do so
            if not self.fetch.is_set():
                self.paused.set()
                # Wait to unpause or exit
                while not self.fetch.is_set() and not self.exit.is_set():
                    sleep(0)  # yield to other threads
                if self.exit.is_set():
                    break
                # Continue fetching
                self.paused.clear()

            # Try to fetch, should return an np.ndarray with voltages (length multiple of 4)
            try:
                new = fetch_func()
            except PLInterface.DMANotAllowed:
                helpers.verbose("[QUEUE] Got DMA error when trying to fetch!")

            # Put new data in queue as a tuple per point
            if len(new) % 4 != 0:
                raise ValueError("[QUEUE] fetch_func() returned a non-integer amount of points!")
            for i in range(0, len(new), 4):
                try:
                    self.put_nowait((new[i], new[i + 1], new[i + 2], new[i + 3]))
                except Full:
                    # If the queue is full it pauses fetching, the server should notice and reply error
                    helpers.printd("[QUEUE] Queue is full! Pausing DMA")
                    self.fetch.clear()
                    self.paused.set()

        # If we get here we're exiting the thread
        self.paused.set()  # Signal to the main server thread that we're not acquiring anymore! Hangs otherwise!
        return
