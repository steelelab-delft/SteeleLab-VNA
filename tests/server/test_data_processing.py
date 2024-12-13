"""Tests data processing classes and functions, also on systems that do not have `pynq` installed"""

from threading import Thread

from numpy import ndarray
from pytest import fail, raises

from tests.server import mocked_pynq

# Apply the mocked pynq module before importing the classes to be tested.
mocked_pynq.mock_pynq_module(mocked_pynq)
from project.server.data_processing import DataQueue, PLInterface


def test_dma_hang() -> None:
    # Create PL interface and do not enable acquisition but try a DMA request.
    pl_i = PLInterface()
    assert not pl_i.enable, "PL incorrectly enabled by default"
    with raises(PLInterface.DMANotAllowed):
        pl_i.get_data()
        fail("PL not enabled; wait for DMA transfer should hang.")


def test_dma_get_data() -> None:
    # Create PL interface and start mocked acquisition.
    pl_i = PLInterface()
    assert pl_i.dma_status == 2, "DMA status should be 2 since no transfer running"
    pl_i.enable = True
    assert pl_i.enable, "PL enable failed"

    # Request data via Direct Memory Access.
    raw_data = pl_i._raw_dma_request(True)
    assert pl_i.dma_status == 2, "DMA status should be 2 again after transfer finished"
    assert len(raw_data) == pl_i.DMA_PACKET_LENGTH, "raw data length incorrect"
    data = pl_i.preprocess_raw_dma_data(raw_data)
    assert len(data) == pl_i.points_per_transfer * 4
    assert isinstance(data, ndarray), "preprocess_raw_dma_data should return a numpy array"
    assert isinstance(data[0], float), "preprocess_raw_dma_data should return floatlikes"


def test_mmio() -> None:
    # Test writing and reading memory-mapped input/output registers.
    pl_i = PLInterface()
    test_data = 0x1
    # For all commands that have an MMIO field associated with them
    for cmd in PLInterface.MMIO_FIELD_DICT:
        # Write value and then read back. Skip PPT and IFF because they have different default values
        # TODO: This isn't a very good test! We should at least test if the value written is correct
        assert (cmd in {'a', 'i'} or pl_i.read_mmio(cmd) == 0), f"MMIO '{cmd}' didn't start cleared!"
        pl_i.write_mmio(cmd, test_data)
        assert (pl_i.read_mmio(cmd) != 0), f"MMIO write/read '{cmd}' returned 0 instead of data!"


def test_queue() -> None:
    # Create small data queue.
    DataQueue.MAXSIZE_BITS = 3
    dq = DataQueue()
    assert not dq.starting_or_started, "new data queue should be paused"
    assert not dq.exit.is_set(), "new data queue should not be exiting"

    # Fetch test data in thread and read it.
    test_data_func = lambda: (-1., -.5, .5, 1)
    thr = Thread(target=dq.keep_fetching, args=(test_data_func, ))
    thr.start()
    dq.fetch.set()
    assert dq.get(timeout=5) == test_data_func(), "queue is not filled with test data"

    # Send signal to thread and wait for response pause signal.
    dq.fetch.clear()
    assert dq.paused.wait(5), "pause signal still not received 5 seconds after `fetch` was cleared"

    # Send exit signal and check if thread ended.
    dq.exit.set()
    thr.join(timeout=5)
    assert not thr.is_alive(), "thread should exit after setting attribute `is_waiting` to False"
