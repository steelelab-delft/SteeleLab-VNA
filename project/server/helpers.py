"""Helper functions related to debugging the server"""

import os
from datetime import datetime
from struct import pack
from subprocess import run

VERBOSE = False
"""Whether to spam your console with messages"""


def printd(*args, **kwargs):
    """Prints date and time in front of message."""
    out = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if "flush" not in kwargs:
        print(out, *args, flush=True, **kwargs)
    else:
        print(out, *args, **kwargs)


def verbose(*args, **kwargs):
    """Does a printd() only if VERBOSE is True"""
    if VERBOSE: printd(*args, **kwargs)


def cpu_temp():
    """Returns cpu temperature of PYNQ server."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sh", "cpu_temp.sh")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Script '{path}' does not exist.")
    process = run(f"bash {path} -F", shell=True, capture_output=True, check=False)
    return float(process.stdout.decode())


def floats64_to_bytes(values):
    """Converts iterable of 64-bit Python floats to bytes object. Source:
    https://stackoverflow.com/questions/9940859/fastest-way-to-pack-a-list-of-floats-into-bytes-in-python.
    """
    return pack(f"{len(values)}d", *values)


def uint64_to_signed_int(unsigned):
    """Converts 64-bit unsigned integer to signed integer. By Bit Twiddling Hacks; see
    https://stackoverflow.com/questions/1375897/how-to-get-the-signed-integer-value-of-a-long-in-python.
    """
    unsigned &= (1 << 64) - 1  # Keep only the lowest 63 bits.
    return (unsigned ^ 0x8000000000000000) - 0x8000000000000000  # Swap and shift down.
