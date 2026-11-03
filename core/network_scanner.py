from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


def local_ipv4() -> str | None:
    """ Best-effort local IPv4 address used for outbound traffic. """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def subnet_hosts(ip: str, prefix: int = 24) -> list[str]:
    try:
        network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
    except ValueError:
        return []
    return [str(host) for host in network.hosts()]


# Common adb tcpip ports probed during a LAN scan. Random Android 11+
# wireless-debugging ports cannot be swept across a whole subnet, but they
# are covered through the "recent addresses" memory instead.
COMMON_PORTS = [5555, 5556, 5557, 5558, 5559, 5560]


def port_open(ip: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_hosts(hosts: list[str], port: int = 5555, timeout: float = 0.4, workers: int = 64) -> list[str]:
    found: list[str] = []
    if not hosts:
        return found
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(port_open, host, port, timeout): host for host in hosts}
        for future in as_completed(futures):
            if future.result():
                found.append(futures[future])
    return sorted(found, key=lambda value: tuple(int(part) for part in value.split(".")))


def discover(port: int = 5555) -> list[str]:
    local = local_ipv4()
    if not local:
        return []
    return scan_hosts(subnet_hosts(local), port=port)


def scan_ports(
    hosts: list[str],
    ports: list[int] | None = None,
    timeout: float = 0.3,
    workers: int = 128,
) -> list[str]:
    """Probe *hosts* across several ports; returns ``ip:port`` serials."""
    targets = ports or COMMON_PORTS
    found: list[str] = []
    if not hosts:
        return found
    combos = [(host, port) for host in hosts for port in targets]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(port_open, host, port, timeout): (host, port) for host, port in combos}
        for future in as_completed(futures):
            if future.result():
                host, port = futures[future]
                found.append(f"{host}:{port}")
    return sorted(found, key=_serial_sort_key)


def _serial_sort_key(serial: str) -> tuple:
    host, _, port = serial.rpartition(":")
    return tuple(int(part) for part in host.split(".")) + (int(port),)


def discover_serials(
    ports: list[int] | None = None,
    recent: list[str] | None = None,
) -> list[str]:
    """Discover adb tcpip serials on the local subnet, plus remembered ones.

    *recent* holds full ``ip:port`` strings from previous sessions; they are
    probed directly regardless of the current subnet sweep so any port
    (including random Android 11+ wireless-debugging ports) reconnects fast.
    """
    local = local_ipv4()
    serials: list[str] = []
    if local:
        serials = scan_ports(subnet_hosts(local), ports=ports)
    seen = set(serials)
    for serial in recent or []:
        text = (serial or "").strip()
        host, sep, port_text = text.rpartition(":")
        if not sep or not host or not port_text.isdigit() or text in seen:
            continue
        if port_open(host, int(port_text), timeout=0.6):
            serials.append(text)
            seen.add(text)
    return serials
