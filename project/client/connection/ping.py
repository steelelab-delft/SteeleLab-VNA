from pythonping import ping


def network_ping_average(address: str, attempts: int = 4, timeout: float = 500.) -> float:
    """Finds average of given amount of ping round trip times to a network device.

    Args:
        address (str): network address of device (IP address, hostname, fqdn etc.);
        attempts (int): number of tries for ping;
        timeout (float): milliseconds before attempt is marked as timeout.

    Returns:
        float: average round trip time (milliseconds).
    """
    return ping(address, timeout=1 if timeout < 1 else int(timeout), count=attempts).rtt_avg_ms
