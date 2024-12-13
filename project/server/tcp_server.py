"""Simple TCP server that runs on the processing system (PS) to receive configuration and send acquired data"""

import socket
from queue import Empty
from threading import Thread
from time import sleep

import helpers
from data_processing import DataQueue, PLInterface
from protocol import TCPCommandProtocol


class TCPDataServer(TCPCommandProtocol):
    """Simple host:port socket server based on https://realpython.com/python-sockets"""

    class ServerStop(Exception):
        """Graceful stop for the TCP server"""

    class PLError(Exception):
        """Any kind of error relating to the Programmable Logic"""

    BUFSIZE = 16
    """Receiving buffer size"""

    QUEUE_TIMEOUT = 50E-3
    """How long to wait for additional data before deciding to send a halffull packet"""

    DEBUG = True
    """Whether to print debugging information"""

    def __init__(self, host, port):
        self.host, self.port = host, port
        if TCPDataServer.DEBUG: helpers.printd(f"[TCP] Loading PL overlay {PLInterface.OVERLAY_PATH}...")
        self.pl_interface = PLInterface()

        # Create DataQueue object and start fetching thread
        self.queue = DataQueue()
        helpers.printd("[TCP] Starting data fetch thread...")
        # Start the queue fetch method and point it to the PL interface get_data method
        self.fetch_thread = Thread(target=self.queue.keep_fetching, args=(self.pl_interface.get_data, ), name="vna_fetch_dma")
        self.fetch_thread.start()

    def get_data(self):
        """Reads the I and Q data (points) from the data queue,
        groups it into larger packets and converts to bytes.
        """
        if not self.pl_interface.enable:
            return TCPCommandProtocol.RESPONSE_ERR

        # List of float values to send
        data_packet = []

        # Assemble a response packet
        while (len(data_packet) // 4) < TCPDataServer.POINTS_PER_PACKET:
            # This gets data from the queue.
            try:
                # Get a single point from the queue as a tuple of 4 voltages (Idut, Qdut, Iref, Qref)
                point = self.queue.get(timeout=DataQueue.QUEUE_TIMEOUT)
            except Empty:
                # Timeout occured: send immediately if we have anything
                if len(data_packet) > 0:
                    helpers.verbose(f"[TCP] No data in queue; sending {len(data_packet) // 4} point(s) now")
                    break
                else:  # Else, check if the fetching paused
                    if self.queue.paused.is_set():
                        helpers.verbose("[TCP] No data in queue and fetching is paused! Probably filled the queue")
                        return TCPCommandProtocol.RESPONSE_ERR
                    helpers.verbose("[TCP] No data in queue; waiting for more data")
                    continue

            # Add point data to the packet
            data_packet.extend(point)

        # Convert floats to bytes so they can be transmitted
        return helpers.floats64_to_bytes(data_packet)

    def change_config(self, config: dict):
        """Changes fields in the hardware configuration of the PL according to the provided dictionary."""
        if self.pl_interface.enable:
            raise TCPDataServer.PLError("[TCP] Cannot change configuration while the DMA is active!")
        # Loop over all (command, value) pairs
        for cmd, value in config.items():
            # Use the setter for PPT because more stuff needs to change besides MMIO
            if cmd == TCPCommandProtocol.PPT:
                self.pl_interface.points_per_transfer = value
            else:
                self.pl_interface.write_mmio(cmd, value)
            if TCPDataServer.DEBUG:
                helpers.printd(f"Config {cmd} changed to {value}.")
        return TCPCommandProtocol.RESPONSE_OK

    def control_on_off(self, data):
        """Turns on or off the programmable logic and stops or starts fetching data into the queue via DMA.
        Argument `data` should be '0' or '1'.
        """
        if data not in {"0", "1"}:
            raise ValueError(f"Unknown value: {data} is not '0' or '1'.")
        enable_pl = (data == "1")

        try:
            if enable_pl: self.start_dma()
            else: self.pause_dma()
        except TCPDataServer.PLError:
            return TCPCommandProtocol.RESPONSE_ERR
        else:
            return TCPCommandProtocol.RESPONSE_OK

    def start_dma(self):
        """Enables or restarts DMA fetching."""
        # Check if the current PL configuration is valid before enabling
        try:
            self.pl_interface.verify_config()
        except AssertionError as err:
            raise TCPDataServer.PLError("[TCP] Requested to start DMA but MMIO failed to verify!") from err

        # Pause DMA transfers, empty the queue, enable PL and enable DMA fetching. The order is important!
        self.pause_dma()
        self.queue.flush()
        try:
            helpers.verbose("Current MMIO contents:", self.pl_interface.get_mmio_status())
            self.pl_interface.enable = True
            self.queue.fetch.set()
        except (RuntimeError, PLInterface.DMANotAllowed) as err:
            raise TCPDataServer.PLError(f"[TCP] Enabling PL/DMA failed; DMA not gracefully stopped?") from err

    def pause_dma(self):
        """Pauses DMA fetching, aborts current transfer"""
        self.queue.fetch.clear()  # Send signal to pause fetching
        # TODO: Find a way to abort the running DMA transfer here because now the server will take up to PPT*TPP seconds
        #       to respond to a start/stop command. dma_channel.stop() bricks the DMA >:(
        self.queue.paused.wait()  # Wait until the transfer has fully processed and the DMA is actually paused
        self.pl_interface.enable = False  # Disable the PL (after transfer is done!!!)

    def determine_response(self, data):
        """Logic for the server's response based on received decoded data"""
        # Requests (no argument)
        if data == TCPCommandProtocol.DATA:  # Data request
            return self.get_data()
        if data == TCPCommandProtocol.QUEUE_SIZE:  # Queue size request, TODO: a bit weird 'innit
            return self.queue.qsize().to_bytes(length=DataQueue.MAXSIZE_BITS // 8, byteorder="big")
        if data == TCPCommandProtocol.CPU_TEMP:  # SoC temperature request
            return helpers.floats64_to_bytes((helpers.cpu_temp(), ))

        if data[0] == TCPCommandProtocol.STOP_SERVER:  # Stop server
            self.stop()
            return TCPCommandProtocol.RESPONSE_OK

        # Commands (with argument)
        if len(data) <= 1:  # We didn't get such argument >:(
            helpers.printd(f"[TCP] Got command '{data[0]}' with no data!")
            return TCPCommandProtocol.RESPONSE_ERR
        if data[0] == TCPCommandProtocol.RUN_PL:  # Acquisition enable/disable
            return self.control_on_off(data[1:])
        if data[0] in PLInterface.MMIO_FIELD_DICT:  # Anything change_config() can deal with
            return self.change_config({data[0]: int(data[1:])})

        # Unknown command
        helpers.printd(f"[TCP] Got unknown command '{data}'!")
        return TCPCommandProtocol.RESPONSE_ERR

    def serve_one_client(self):
        """Sends acquired data to one client."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.sock:
                try:
                    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.sock.bind((self.host, self.port))
                    self.sock.listen(1)
                except OSError as err:
                    helpers.printd(f"Cannot start server: {str(err)}")
                    return self.stop()  # raises server stop which gets caught by the top level try
                if TCPDataServer.DEBUG:
                    helpers.printd(f"Started TCP data server on {self.host}:{self.port}.")

                # Wait until client accepts connection.
                while True:
                    server_waits_for_client = True
                    try:
                        helpers.verbose("[TCP] waiting for client.")
                        conn, addr = self.sock.accept()  # blocking
                        client = f"{addr[0]}:{addr[1]}"
                    except KeyboardInterrupt:
                        if TCPDataServer.DEBUG:
                            helpers.printd("Keyboard interrupt; stopping TCP server...")
                        return self.stop()  # raises server stop which gets caught by the top level try
                    with conn:
                        if TCPDataServer.DEBUG: helpers.printd(f"{client} connected to the TCP server.")

                        # Loop until client disconnects.
                        received_data = b""
                        while True:
                            try:
                                received_data = conn.recv(TCPDataServer.BUFSIZE)
                            except (ConnectionResetError, BrokenPipeError) as err:
                                if TCPDataServer.DEBUG:
                                    helpers.printd(f"{client} caused exception: {err}")
                                    continue
                            if not received_data:
                                if server_waits_for_client:
                                    sleep(0)
                                    continue
                                if TCPDataServer.DEBUG: helpers.printd(f"{client} disconnected.")
                                break

                            # Start processing commands when client sends them.
                            server_waits_for_client = False
                            try:
                                response = self.determine_response(received_data.decode())
                            except Exception as err:
                                if isinstance(err, TCPDataServer.ServerStop):
                                    return
                                response = TCPCommandProtocol.RESPONSE_ERR
                                if TCPDataServer.DEBUG:
                                    helpers.printd(
                                        f"Exception occured when processing command {received_data.decode()}: "
                                        f"{type(err).__name__}: {' '.join([str(a) for a in err.args])}"
                                    )

                            # Respond to the client.
                            try:
                                conn.sendall(response)
                            except (ConnectionResetError, BrokenPipeError):
                                if TCPDataServer.DEBUG:
                                    helpers.printd(f"{client} reset the connection.")

                        self.pause_dma()  # Close currently running DMA transfer (if any)
        except TCPDataServer.ServerStop:
            return

    def stop(self):
        """Closes the TCP server, stops the threads that were started and raises the ServerStop exception."""
        if not hasattr(self, "sock"):
            return
        if TCPDataServer.DEBUG: helpers.printd("[TCP] Stopping TCP server...")
        self.sock.close()
        if TCPDataServer.DEBUG: helpers.printd("[TCP] Stopping data fetch thread...")
        self.queue.exit.set()  # Exit DMA thread on next pause
        self.pause_dma()  # Stop requesting from DMA
        if TCPDataServer.DEBUG: helpers.printd("[TCP] Waiting for data fetch thread...")
        self.fetch_thread.join()  # Wait for DMA thread to exit
        if TCPDataServer.DEBUG: helpers.printd("[TCP] Stopping PL...")
        self.pl_interface.enable = False
        if TCPDataServer.DEBUG: helpers.printd("[TCP] Goodbye!")
        raise TCPDataServer.ServerStop
