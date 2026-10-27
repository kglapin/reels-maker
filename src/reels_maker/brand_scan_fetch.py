"""Safe transport for the read-only website brand scanner."""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit, urlunsplit


class WebsiteScanError(ValueError):
    """A website is unsafe, inaccessible or incompatible with static scanning."""


def _safe_url(url: str) -> tuple[str, str, int, str]:
    if not isinstance(url, str) or len(url) > 2048:
        raise WebsiteScanError("URL must be a string of at most 2048 characters")
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise WebsiteScanError("Only absolute http(s) website URLs are supported")
    if parts.username or parts.password:
        raise WebsiteScanError("URLs containing credentials are not allowed")
    try:
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except (UnicodeError, ValueError) as exc:
        raise WebsiteScanError("Invalid website hostname or port") from exc
    if port != (443 if parts.scheme == "https" else 80):
        raise WebsiteScanError("Nonstandard website ports are not supported")
    if host in ("localhost",) or host.endswith((".local", ".internal")):
        raise WebsiteScanError("Local and internal hostnames are not allowed")
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    canonical = urlunsplit((parts.scheme, host, parts.path or "/", parts.query, ""))
    return canonical, host, port, path


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, *, timeout: int):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        sock = socket.create_connection((self._address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _fetch(url: str, *, limit: int, timeout: int = 7) -> tuple[str, bytes, str]:
    """Safe public-IP-pinned HTTP fetch; redirects are checked from scratch."""
    for _ in range(4):
        url, host, port, path = _safe_url(url)
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise WebsiteScanError(f"Website DNS lookup failed: {host}") from exc
        ips = {item[4][0] for item in addresses}
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise WebsiteScanError("Refusing private, loopback or non-public network address")
        ip = sorted(ips, key=lambda x: (":" in x, x))[0]
        connection = (_PinnedHTTPS(host, ip, timeout=timeout)
                      if url.startswith("https:")
                      else http.client.HTTPConnection(ip, port, timeout=timeout))
        try:
            connection.request("GET", path, headers={
                "Host": host,
                "User-Agent": "ReelsMakerBrandScanner/0.1 (+static CSS inspection)",
                "Accept": "text/html,text/css,image/svg+xml,image/png,image/webp,image/jpeg,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise WebsiteScanError("Website redirect is missing Location")
                url = urljoin(url, location)
                continue
            if not 200 <= response.status < 300:
                raise WebsiteScanError(f"Website returned HTTP {response.status}: {url}")
            content = response.read(limit + 1)
            if len(content) > limit:
                raise WebsiteScanError(f"Website resource exceeds {limit} bytes: {url}")
            return url, content, response.getheader("Content-Type", "")
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise WebsiteScanError(f"Cannot fetch website resource {url}: {exc}") from exc
        finally:
            connection.close()
    raise WebsiteScanError("Too many website redirects")
