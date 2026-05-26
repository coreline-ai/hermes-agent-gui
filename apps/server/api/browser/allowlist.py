from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

DEFAULT_ALLOWLIST = {"github.com", "example.com", "localhost", "127.0.0.1"}


def allowlist() -> set[str]:
    raw = os.environ.get("HERMES_GUI_BROWSER_ALLOWLIST")
    if not raw:
        return set(DEFAULT_ALLOWLIST)
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _private_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_link_local:
                return True
        except ValueError:
            continue
    return False


def validate_url(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False, "invalid_url"
    host = parsed.hostname.lower()
    allowed = allowlist()
    if not any(host == item or host.endswith(f".{item}") for item in allowed):
        return False, "domain_not_allowed"
    if host not in {"localhost", "127.0.0.1"} and _private_ip(host):
        return False, "private_ip_blocked"
    return True, None
