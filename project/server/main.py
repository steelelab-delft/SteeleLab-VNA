#!/usr/local/share/pynq-venv/bin/python3
"""Main server script"""

from sys import argv

from helpers import printd

if len(argv) == 1:
    MOCK_PYNQ = False
elif argv[1] == "-M":
    MOCK_PYNQ = True
else:
    raise ValueError(f"Program argument {argv[1]} not understood. Options are:\n\t-M\tmock 'pynq' library")

if MOCK_PYNQ:  # mocking the pynq library
    printd("Mocking 'pynq' library...")
    from os import getcwd
    from sys import path
    path.insert(0, getcwd())
    from tests.server import mocked_pynq
    mocked_pynq.mock_pynq_module(mocked_pynq)

from tcp_server import TCPDataServer


def main():
    printd("Started main server script.")
    tds = TCPDataServer(host="", port=2024)
    tds.serve_one_client()
    printd("Stopped main server script.")


if __name__ == "__main__":
    main()
