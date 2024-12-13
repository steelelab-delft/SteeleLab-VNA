"""Definitions for proper communication and programmable logic (PL) configuration parameters"""

from os.path import join

from numpy import uint32


class TCPCommandProtocol:
    """Defines the commands used for communication between Python TCP client
    and Python TCP server.
    """

    TCP_PORT = 2024
    """Port on which the Python TCP server listens for clients"""

    # PL CONFIG COMMANDS:
    RUN_PL = "r"
    """Enable data acquisition in programmable logic"""

    DEAD_TIME = "g"
    """Generator dead time in microseconds"""

    TPP = "p"
    """Time per point in microseconds for averaging inside the PL"""

    TRIG_LEN = "t"
    """Trigger pulse length in microseconds"""

    TRIG_0_CONF = "c"
    """Trigger output 0 configuration; expecting a 4-bit flags value"""

    TRIG_1_CONF = "o"
    """Trigger output 1 configuration; expecting a 4-bit flags value"""

    PPT = "a"
    """Points per DMA transfer"""

    IF_MULT = "i"
    """IF multiplier, IF = val*FCLK/256"""

    TCP_PL_CONFIG_CMDS = {DEAD_TIME, TPP, TRIG_LEN, TRIG_0_CONF, TRIG_1_CONF, PPT, IF_MULT}
    """All configuration commands used in client-server communication"""

    # DATA REQUEST COMMANDS:
    DATA = "d"
    """Request IQ data in volts"""

    CPU_TEMP = "T"
    """Request server cpu temperature in degrees Celsius"""

    QUEUE_SIZE = "q"
    """Request server data queue size"""

    TCP_REQUEST_CMDS = {DATA, CPU_TEMP, QUEUE_SIZE}
    """All commands a client can use to request data from the TCP server"""

    # MISC
    STOP_SERVER = "!"
    """Command to stop the TCP server remotely"""

    RESPONSE_OK = b"*"
    """Server understood client's command"""

    RESPONSE_ERR = b"?"
    """Server did not understand client's command or an internal error occured"""

    POINTS_PER_PACKET = 45
    """Number of IQ measurements (points) per TCP transfer; for optimal throughput and response time / interactivity"""


class PLConfig:
    """Defines programmable logic configuration parameters"""

    OVERLAY_PATH = join("/home", "xilinx", "bit", "slvna_v1_0.bit")
    """Path to .bit file to be used as overlay on programmable logic; .hwh file should also be in this directory"""

    MMIO_DEAD_TIME = 0
    """MMIO used for configuring generator dead time"""

    MMIO_TPP = 1
    """MMIO used for configuring time per point"""

    MMIO_TRIG = 2
    """MMIO used for configuring trigger output"""

    MMIO_GENERAL = 3
    """MMIO used for general programmable logic configuration"""

    MMIO_ADDRESSES_DICT = {MMIO_TRIG: 0x41200000, MMIO_GENERAL: 0x41200008, MMIO_DEAD_TIME: 0x42000000, MMIO_TPP: 0x42000008}
    """All MMIO interfaces to the PL"""

    FCLK = 125
    """Frequency of the main PL clock in MHz, used as conversion factor clockcycles/microsecond"""

    MMIO_FIELD_DICT = {
        TCPCommandProtocol.TPP: {
        "scale": FCLK,
        "mmio": MMIO_TPP,
        "mask": 0xFFFFFFFF
        },
        TCPCommandProtocol.DEAD_TIME: {
        "scale": FCLK,
        "mmio": MMIO_DEAD_TIME,
        "mask": 0xFFFFFFFF
        },
        TCPCommandProtocol.TRIG_LEN: {
        "scale": FCLK,
        "mmio": MMIO_TRIG,
        "mask": 0x00FFFFFF
        },
        TCPCommandProtocol.TRIG_0_CONF: {
        "scale": 1,
        "mmio": MMIO_TRIG,
        "mask": 0x0F000000
        },
        TCPCommandProtocol.TRIG_1_CONF: {
        "scale": 1,
        "mmio": MMIO_TRIG,
        "mask": 0xF0000000
        },
        TCPCommandProtocol.PPT: {
        "scale": 1,
        "mmio": MMIO_GENERAL,
        "mask": 0xFFFF0000
        },
        TCPCommandProtocol.IF_MULT: {
        "scale": 256 / FCLK,
        "mmio": MMIO_GENERAL,
        "mask": 0x0000FF00
        },
        TCPCommandProtocol.RUN_PL: {
        "scale": 1,
        "mmio": MMIO_GENERAL,
        "mask": 0x00000001
        },
    }
    """Translation dictionary between TCP commands and fields in PL MMIOs. (scale, mmio, mask)"""

    RAW_TO_VOLTS = 2 ** -25
    """Conversion of raw DMA output to volts"""

    DMA_PACKET_LENGTH = 12
    """Length (in nrs. of DMA_DTYPE) of data packet received via DMA"""

    DMA_DTYPE = uint32
    """Data type coming from DMA"""
