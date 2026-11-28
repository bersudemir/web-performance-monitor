"""HTTP checks with DNS pinned to publicly routable addresses."""

import ipaddress
import socket
from time import perf_counter

import httpx
from httpcore._backends.sync import SyncBackend

MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 10


class UnsafeAddress(ValueError):
    pass


def public_addresses(host: str, port: int) -> list[str]:
    if not host or host.endswith(".local") or host.lower() == "localhost":
        raise UnsafeAddress("Yerel adres engellendi")
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise UnsafeAddress("DNS çözümlenemedi") from error
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise UnsafeAddress("Genel erişime açık olmayan IP engellendi")
    return addresses


class PinnedBackend(SyncBackend):
    """Resolve at connection time, then dial the checked IP while preserving TLS host."""

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        address = public_addresses(host, port)[0]
        return super().connect_tcp(address, port, timeout, local_address, socket_options)


def check_url(url: str) -> tuple[bool, int | None, int | None, str | None]:
    started = perf_counter()
    try:
        current = httpx.URL(url)
        for hop in range(MAX_REDIRECTS + 1):
            if current.scheme not in ("http", "https") or not current.host or current.userinfo:
                raise UnsafeAddress("HTTP/HTTPS dışı veya kimlik bilgili adres engellendi")
            transport = httpx.HTTPTransport(trust_env=False, retries=0)
            # HTTPX 0.28.1/httpcore 1.x: replace only the connection backend.
            transport._pool._network_backend = PinnedBackend()
            with httpx.Client(transport=transport, trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(TIMEOUT_SECONDS)) as client:
                with client.stream("GET", current) as response:
                    status = response.status_code
                    location = response.headers.get("location")
            if 300 <= status < 400 and location:
                if hop == MAX_REDIRECTS:
                    raise UnsafeAddress("Yönlendirme sınırı aşıldı")
                current = current.join(location)
                continue
            elapsed = max(0, round((perf_counter() - started) * 1000))
            return 200 <= status < 400, status, elapsed, None
    except (UnsafeAddress, httpx.HTTPError, httpx.InvalidURL, ValueError) as error:
        return False, None, None, f"{type(error).__name__}: {error}"[:500]
