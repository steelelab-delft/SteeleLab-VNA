"""Part of a mocked version of the pynq libary for testing on systems that do not have it installed"""

import os
import sys
from types import ModuleType
from typing import Any

from numpy import array, empty, ndarray, uint32, zeros, concatenate

from project.server import helpers, protocol


def mock_pynq_module(mocked_module: ModuleType) -> None:
    # Add directory to path to be able to find 'helpers.py'.
    sys.path.insert(0, os.path.dirname(helpers.__file__))

    # Reassign pynq module to the given mocked module.
    sys.modules["pynq"] = mocked_module


def allocate(shape: Any, dtype: str = "u4", **kwargs) -> Any:
    """Mocked version of pynq.allocate."""
    helpers.printd(f"[TEST] MockedPynq: allocated array of shape {shape}.")
    ALLOCATED_BUFFER = zeros(shape, dtype)
    return ALLOCATED_BUFFER


ALLOCATED_BUFFER = empty(protocol.PLConfig.DMA_PACKET_LENGTH, dtype=protocol.PLConfig.DMA_DTYPE)
"""Returned upon calling `pynq.allocate`"""


class Overlay:
    """Mocked version of pynq.Overlay"""

    PL_ENABLED = False
    """Whether the PL is enabled or in reset at the moment"""

    PPT = 1
    """How many points the DMA will return every transfer"""

    FIRST_TRANSFER = True
    """If this is the first point transfer in this sweep"""

    FIRST_SWEEP = True
    """If this is the first sweep after loading the overlay"""

    def __init__(self, bitfile_name, *args) -> None:
        helpers.printd(f"[TEST] MockedPynq: loaded overlay {bitfile_name}; PL {'not ' if Overlay.PL_ENABLED else ''}enabled.")

    class dma:
        """Mocked dma class"""

        class recvchannel:
            """Mocked recvchannel class"""

            BUFFER = array((
                4289555807, 4294967295, 14383, 1139606, 0, 14383, 4291721347, 4294967295, 14383, 4292855430, 4294967295, 14383
            ),
                dtype=protocol.PLConfig.DMA_DTYPE)
            """Example point from programmable logic"""

            def transfer(buffer: ndarray[uint32]) -> None:
                """Simulates that the PL writes data into the allocated buffer."""
                if len(buffer) < len(Overlay.dma.recvchannel.BUFFER) * Overlay.PPT:
                    raise RuntimeError("[TEST] MockedPynq: DMA buffer too short to contain transfer, DMA will crash!")

                # Construct a buffer of points
                new = Overlay.dma.recvchannel.BUFFER.repeat(Overlay.PPT)
                rest = zeros(len(buffer) - len(new))
                if Overlay.FIRST_TRANSFER and not Overlay.FIRST_SWEEP:
                    # On the first transfer of a sweep there's garbage pre-pended
                    buffer[:] = concatenate((rest, new))
                else:
                    # On all others it's the last couple words of the buffer that aren't overwritten
                    buffer[:] = concatenate((new, rest))
                helpers.printd("[TEST] MockedPynq: started DMA transfer.")

                Overlay.FIRST_SWEEP = False
                Overlay.FIRST_TRANSFER = False

            @staticmethod
            def wait() -> None:
                """When testing, wait returns immediately unless an error occured."""
                if not Overlay.PL_ENABLED:
                    raise RuntimeError("[TEST] MockedPynq: PL still in reset, DMA will hang!")

            @staticmethod
            def stop() -> None:
                """Stops the current DMA transfer"""
                helpers.printd("[TEST] MockedPynq: stopped DMA transfer.")
                raise RuntimeError("[TEST] MockedPynq: DMA is now bricked, congrats")


class MMIO:
    """Mocked version of pynq.MMIO"""

    def __init__(self, base_addr: int, length: int = 4, device: None = None, **kwargs):
        self.base_addr = base_addr
        self.content = 0x0
        # If the general register
        if self.base_addr == protocol.PLConfig.MMIO_ADDRESSES_DICT[protocol.PLConfig.MMIO_GENERAL]:
            self.content = 0x00011000
        helpers.printd(f"[TEST] MockedPynq: MMIO object initialised at address 0x{base_addr:8x}.")

    def write(self, offset: int, data: int | bytes):
        helpers.printd(f"[TEST] MockedPynq: writing {data} to MMIO address 0x{self.base_addr:8x}.")
        if isinstance(data, bytes):
            data = int.from_bytes(data)
        self.content = data
        # If we're writing to the general MMIO check the fields (affects result of DMA)
        if self.base_addr == protocol.PLConfig.MMIO_ADDRESSES_DICT[protocol.PLConfig.MMIO_GENERAL]:
            Overlay.PL_ENABLED = (data & 0x1) == 1
            if not Overlay.PL_ENABLED:
                Overlay.FIRST_TRANSFER = True
            Overlay.PPT = (data & 0xFFFF0000) >> 16

    def read(self, offset: int = 0, length: int = 4, word_order="little") -> int:
        helpers.printd(f"[TEST] MockedPynq: reading value from MMIO address 0x{self.base_addr:8x}.")
        return self.content
