"""Tiny path → handler registry used by ``server.py``.

We deliberately do not pull in a framework. Each handler receives a
``Request`` object (which exposes path, query, headers, json body, raw body
stream, and the underlying BaseHTTPRequestHandler for SSE) and returns
either a ``Response`` or ``None`` (None means the handler took over the
socket, e.g. for streaming).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Callable, Iterable
from urllib.parse import parse_qs, urlsplit


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    raw: BaseHTTPRequestHandler
    body_cache: bytes | None = None
    params: dict[str, str] = field(default_factory=dict)

    def body_bytes(self, max_bytes: int = 1 << 20) -> bytes:
        if self.body_cache is not None:
            return self.body_cache
        length = int(self.headers.get("content-length", "0") or "0")
        if length <= 0:
            self.body_cache = b""
            return self.body_cache
        if length > max_bytes:
            raise ValueError(f"request body too large: {length} > {max_bytes}")
        self.body_cache = self.raw.rfile.read(length)
        return self.body_cache

    def json(self) -> dict:
        raw = self.body_bytes()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def cookie(self, name: str) -> str | None:
        raw = self.headers.get("cookie")
        if not raw:
            return None
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def bearer(self) -> str | None:
        auth = self.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip() or None
        return None

    def client_ip(self) -> str:
        return self.raw.client_address[0] if self.raw.client_address else "?"


@dataclass
class Response:
    status: HTTPStatus = HTTPStatus.OK
    body: bytes | str | dict | None = None
    headers: list[tuple[str, str]] = field(default_factory=list)

    def add_header(self, name: str, value: str) -> "Response":
        self.headers.append((name, value))
        return self


Handler = Callable[[Request], Response | None]


@dataclass
class Route:
    method: str
    pattern: re.Pattern
    handler: Handler
    param_names: tuple[str, ...]


class Router:
    def __init__(self) -> None:
        self._routes: list[Route] = []

    def add(self, method: str, path: str, handler: Handler) -> None:
        names: list[str] = []

        def repl(m: re.Match) -> str:
            names.append(m.group(1))
            return r"(?P<%s>[^/]+)" % m.group(1)

        regex = re.sub(r"\{(\w+)\}", repl, path)
        pattern = re.compile(f"^{regex}/?$")
        self._routes.append(Route(method.upper(), pattern, handler, tuple(names)))

    def route(self, method: str, path: str):
        def deco(fn: Handler) -> Handler:
            self.add(method, path, fn)
            return fn
        return deco

    def extend(self, other: "Router") -> None:
        """Append every route from ``other`` to this router, preserving compiled patterns."""
        self._routes.extend(other._routes)

    def resolve(self, method: str, path: str) -> tuple[Handler, dict[str, str]] | None:
        for r in self._routes:
            if r.method != method.upper():
                continue
            if (m := r.pattern.match(path)):
                return r.handler, m.groupdict()
        return None

    def routes(self) -> Iterable[Route]:
        return iter(self._routes)


def make_request(raw: BaseHTTPRequestHandler) -> Request:
    sp = urlsplit(raw.path)
    headers = {k.lower(): v for k, v in raw.headers.items()}
    return Request(
        method=raw.command,
        path=sp.path,
        query=parse_qs(sp.query),
        headers=headers,
        raw=raw,
    )
