"""Tests for the TCP client"""

from time import perf_counter_ns

import numpy as np
import pytest

from project.client.connection.tcp_client import TCPClient
from project.server.protocol import TCPCommandProtocol

IP = "192.168.2.99"
"""IP address for direct connection to Red Pitaya."""

PORT = TCPCommandProtocol.TCP_PORT
"""Use default port from protocol."""


@pytest.mark.skip()
def test_performance_tcp_client() -> None:
    # Always use the `with` block to ensure proper connection closing. This is a test for vna v1_7_0.
    count = perf_counter_ns()
    with TCPClient(IP, PORT) as client:
        # Client sends config.
        client.send_tpp(1000)  # tpp = 1 ms
        client.send_dead_time(100)  # dead time = 0.1 ms
        client.send_trigger_length(10)  # trigger pulse length = 0.01 ms
        client.send_trigger_config(0, positive=True, sweep=True, step=True)  # trigger configuration 0
        client.send_trigger_config(1, positive=False, sweep=True, step=True)  # trigger configuration 1
        client.send_trigger_config(1, positive=False, sweep=False, step=True)  # trigger configuration 1 overwrite!
        print(f"sending PL config via TCP took {(perf_counter_ns() - count) * 1E-6} ms")

        count0 = perf_counter_ns()
        client.start_acquisition()  # do not run when testing with already full queue
        qs = client.get_queue_size()  # server should have flushed the queue
        print(f"server queue size = {qs}, should be zero after start acq cmd")

        arr = np.zeros((9991, 4))  # get 10000 data points (takes around 10 seconds at tpp = 1 ms)
        collected_points = 0
        done = False
        total_points = arr.shape[0]
        i = 0
        count1 = perf_counter_ns()  #Start timer
        while True:
            # Request new data.
            new = client.request_data()
            discard_points = 0
            if len(new) == arr.shape[1]:  # One data point received.
                arr[i] = new
                i += 1
                collected_points += 1
                if collected_points > total_points:
                    done = True
            elif len(new) % arr.shape[1] == 0:  # Divisible by 4 (multiple points sent).
                rows = len(new) // arr.shape[1]
                collected_points += rows
                if collected_points >= total_points:
                    done = True
                    discard_points = total_points - collected_points
                arr[i:i + rows] = np.array(new).reshape(rows, arr.shape[1])[-discard_points:]
                i += rows
            else:
                raise ValueError(f"Data has incorrect length {len(new)}; should be divisible by {arr.shape[1]}.")

            # Stop acquisition when all data points received.
            if done:
                count2 = perf_counter_ns()  #Time after everything has been sent
                client.stop_acquisition()
                print("acquisition stopped; server queue size =", client.get_queue_size())
                break

        # Print time statistics for the TCP transfer.
        count3 = perf_counter_ns()
        print("last IQ data:", arr[-3:], sep="\n")
        print(f"transfer time for {i + 1} data points =", (count2 - count1) * 1E-6, "ms")
        print(f"(starting / stopping acquisition took {(count1 - count0) * 1E-6} ms / {(count3 - count2) * 1E-6} ms)")
        print(f"cpu temperature Red Pitaya server = {client.get_server_cpu_temp()} deg C")
        client._stop_server(really=False)  #Stop TCP server (really?)
