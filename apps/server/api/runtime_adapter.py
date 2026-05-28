"""Hermes Agent runtime adapters.

P0-#2,#3 hardening:
- ``EmbeddedAdapter`` tries a wider set of method names and inspects
  signatures (sync/async/generator) so it slots into more Hermes Agent
  releases. Async generators are run via ``asyncio.run`` with a small
  shim that pumps events back into our SSE iterator.
- ``GatewayAdapter`` understands not only ``/v1/chat/completions`` but
  also Hermes' richer streaming surface (the alternate endpoints found in
  ``hermes-agent`` releases — ``/v1/responses``, ``/v1/agent/stream``).
  Whichever responds first wins; we cache the working endpoint per
  adapter instance.

Adapter selection (unchanged):
  1. ``HERMES_GUI_FAKE_BACKEND=echo`` → EchoAdapter
  2. ``HERMES_API_URL`` set         → GatewayAdapter
  3. ``~/.hermes/hermes-agent`` dir → EmbeddedAdapter
  4. fallback                       → NoBackendAdapter
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from .config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatTurn:
    messages: list[dict]
    session_id: str | None = None
    model: str = "auto"
    provider_id: str = "auto"


class Adapter:
    name: str = "abstract"

    def stream(self, turn: ChatTurn) -> Iterable[tuple[str, dict]]:
        raise NotImplementedError


# ── 1. Echo (dev) ────────────────────────────────────────────────────────────


class EchoAdapter(Adapter):
    name = "echo"

    def stream(self, turn: ChatTurn) -> Iterable[tuple[str, dict]]:
        last_user = next(
            (m.get("content", "") for m in reversed(turn.messages) if m.get("role") == "user"),
            "",
        )
        tokens = re.findall(r"\S+\s*", last_user or "(empty message)") or ["(empty)"]
        for tok in tokens:
            yield "token", {"text": tok}
            time.sleep(0.03)
        yield "done", {
            "session_id": turn.session_id or "echo-session",
            "turn_id": f"echo-{int(time.time() * 1000)}",
            "adapter": self.name,
            "model": turn.model,
        }


# ── 2. Gateway (zero-fork) ───────────────────────────────────────────────────


class GatewayAdapter(Adapter):
    """Talks to a Hermes Agent gateway over HTTP+SSE.

    Tries the OpenAI-compatible endpoint first, then Hermes' richer
    streaming surfaces if the first returns 404. The chosen endpoint is
    cached per routing mode on the instance so subsequent turns skip the probe
    without letting an auto-routed OpenAI-compatible cache mask an explicitly
    selected provider's native agent endpoint.
    """

    name = "gateway"

    PROBE_ENDPOINTS = (
        ("/v1/chat/completions", "openai"),
        ("/v1/responses", "responses"),
        ("/v1/agent/stream", "agent"),
    )

    def __init__(self, base_url: str, token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._endpoint: tuple[str, str] | None = None  # (path, flavor)
        self._endpoint_by_mode: dict[str, tuple[str, str]] = {}

    # ── request helpers ────────────────────────────────────────────────────

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _payload(self, turn: ChatTurn, flavor: str) -> dict:
        explicit_provider = bool(turn.provider_id and turn.provider_id != "auto")
        if flavor == "openai":
            payload = {"model": turn.model or "auto", "messages": turn.messages, "stream": True}
            if explicit_provider:
                payload["provider_id"] = turn.provider_id
            return payload
        if flavor == "responses":
            payload = {
                "model": turn.model or "auto",
                "input": [
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in turn.messages
                ],
                "stream": True,
            }
            if explicit_provider:
                payload["provider_id"] = turn.provider_id
            return payload
        # agent flavor — pass-through with session id
        return {
            "session_id": turn.session_id,
            "model": turn.model or "auto",
            "provider_id": turn.provider_id,
            "messages": turn.messages,
            "stream": True,
        }

    def _open(self, path: str, flavor: str, turn: ChatTurn):
        body = json.dumps(self._payload(turn, flavor)).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path, data=body, method="POST", headers=self._headers()
        )
        return urllib.request.urlopen(req, timeout=120)

    # ── streaming ──────────────────────────────────────────────────────────

    def _probe_endpoints(self, turn: ChatTurn) -> tuple[tuple[str, str], ...]:
        """Prefer Hermes' native agent stream when a concrete provider is selected.

        OpenAI-compatible gateways may ignore non-standard routing fields. Trying
        the native endpoint first makes provider selection observable instead of
        silently falling back to a provider-agnostic chat/completions call.
        """
        if turn.provider_id and turn.provider_id != "auto":
            return (
                ("/v1/agent/stream", "agent"),
                ("/v1/chat/completions", "openai"),
                ("/v1/responses", "responses"),
            )
        return self.PROBE_ENDPOINTS

    @staticmethod
    def _routing_mode(turn: ChatTurn) -> str:
        return "provider" if turn.provider_id and turn.provider_id != "auto" else "default"

    def _try_endpoint(self, turn: ChatTurn) -> tuple[Any, tuple[str, str]] | None:
        mode = self._routing_mode(turn)
        cached = self._endpoint_by_mode.get(mode)
        if cached is not None:
            try:
                self._endpoint = cached
                return self._open(cached[0], cached[1], turn), cached
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                self._endpoint_by_mode.pop(mode, None)
                self._endpoint = None  # fall through to re-probe
        for path, flavor in self._probe_endpoints(turn):
            try:
                resp = self._open(path, flavor, turn)
                self._endpoint = (path, flavor)
                self._endpoint_by_mode[mode] = self._endpoint
                logger.info("gateway endpoint selected: %s (%s)", path, flavor)
                return resp, self._endpoint
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                continue
            except urllib.error.URLError as exc:
                logger.warning("gateway %s unreachable: %s", path, exc)
                return None
        return None

    def stream(self, turn: ChatTurn) -> Iterable[tuple[str, dict]]:
        try:
            picked = self._try_endpoint(turn)
        except urllib.error.URLError as exc:
            yield "error", {"error": "gateway_unreachable", "detail": str(exc)}
            return
        if picked is None:
            yield "error", {"error": "gateway_no_streaming_endpoint"}
            return
        resp, (path, flavor) = picked
        buf = b""
        try:
            for chunk in resp:
                buf += chunk
                while b"\n\n" in buf:
                    frame, buf = buf.split(b"\n\n", 1)
                    for evt in self._parse_frame(frame.decode("utf-8", errors="replace"), flavor):
                        yield evt
        except urllib.error.URLError as exc:
            yield "error", {"error": "gateway_stream_failed", "detail": str(exc)}
            return
        yield "done", {
            "session_id": turn.session_id or "gateway",
            "adapter": self.name,
            "endpoint": path,
        }

    @staticmethod
    def _parse_frame(frame: str, flavor: str) -> Iterable[tuple[str, dict]]:
        data_lines = [ln[5:].lstrip() for ln in frame.splitlines() if ln.startswith("data:")]
        for d in data_lines:
            if d in {"[DONE]", "DONE"}:
                return
            try:
                payload = json.loads(d)
            except json.JSONDecodeError:
                continue
            text = _extract_token_text(payload, flavor)
            if text:
                yield "token", {"text": text}


def _extract_token_text(payload: dict, flavor: str) -> str | None:
    if flavor == "openai":
        try:
            return payload["choices"][0]["delta"].get("content")
        except (KeyError, IndexError, TypeError):
            return None
    if flavor == "responses":
        # Two known shapes
        try:
            return payload["delta"]["text"]  # responses delta event
        except (KeyError, TypeError):
            pass
        try:
            return payload["output"][0]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return None
    if flavor == "agent":
        try:
            return payload.get("text") or payload.get("content")
        except AttributeError:
            return None
    return None


# ── 3. Embedded (P0-#2 hardening) ────────────────────────────────────────────


class EmbeddedAdapter(Adapter):
    """Direct AIAgent import + best-effort method dispatch.

    Searches the class for any of: ``stream``, ``respond_stream``, ``chat_stream``,
    ``arun_stream``, ``respond``, ``chat``. Detects sync vs async, generator vs
    single-shot, dict vs str return.
    """

    name = "embedded"
    METHOD_CANDIDATES = (
        "stream",
        "respond_stream",
        "chat_stream",
        "arun_stream",
        "respond",
        "chat",
        "arun",
    )

    def __init__(self, agent_dir: Path) -> None:
        self.agent_dir = agent_dir
        self._agent: object | None = None
        self._method: tuple[str, bool, bool] | None = None  # (name, is_async, is_generator)
        self._import_error: str | None = None
        self._try_import()

    def _try_import(self) -> None:
        import sys as _sys
        try:
            if str(self.agent_dir) not in _sys.path:
                _sys.path.insert(0, str(self.agent_dir))
            cls = None
            for module_name in ("agent", "hermes.agent", "hermes"):
                try:
                    mod = __import__(module_name, fromlist=["AIAgent", "HermesAgent"])
                    cls = getattr(mod, "AIAgent", None) or getattr(mod, "HermesAgent", None)
                    if cls is not None:
                        break
                except ImportError:
                    continue
            if cls is None:
                self._import_error = "Could not find AIAgent / HermesAgent class"
                return
            self._agent = cls()
            self._method = self._pick_method(self._agent)
            if self._method is None:
                self._import_error = (
                    "Agent has none of: " + ", ".join(self.METHOD_CANDIDATES)
                )
        except Exception as exc:  # noqa: BLE001
            self._import_error = f"{type(exc).__name__}: {exc}"

    def _pick_method(self, agent: object) -> tuple[str, bool, bool] | None:
        for name in self.METHOD_CANDIDATES:
            fn = getattr(agent, name, None)
            if not callable(fn):
                continue
            is_async = inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
            is_gen = (
                inspect.isgeneratorfunction(fn)
                or inspect.isasyncgenfunction(fn)
                or name.endswith("_stream")
                or name == "stream"
            )
            logger.info("embedded: using %s.%s (async=%s gen=%s)", type(agent).__name__, name, is_async, is_gen)
            return (name, is_async, is_gen)
        return None

    # ── streaming wrappers ─────────────────────────────────────────────────

    def stream(self, turn: ChatTurn) -> Iterable[tuple[str, dict]]:
        if self._agent is None or self._method is None:
            yield "error", {
                "error": "embedded_import_failed",
                "detail": self._import_error or "unknown",
                "agent_dir": str(self.agent_dir),
            }
            return
        name, is_async, is_gen = self._method
        fn = getattr(self._agent, name)
        last_user = next(
            (m.get("content", "") for m in reversed(turn.messages) if m.get("role") == "user"),
            "",
        )
        try:
            if is_async and is_gen:
                yield from _drain_async_gen(fn(last_user))
            elif is_async:
                result = asyncio.run(fn(last_user))
                yield from _yield_result(result)
            elif is_gen:
                for chunk in fn(last_user):
                    yield from _yield_result(chunk)
            else:
                yield from _yield_result(fn(last_user))
        except Exception as exc:  # noqa: BLE001
            yield "error", {"error": "embedded_runtime_error", "detail": str(exc)}
            return
        yield "done", {"session_id": turn.session_id or "embedded", "adapter": self.name}


def _yield_result(chunk: Any) -> Iterator[tuple[str, dict]]:
    """Normalize an arbitrary adapter return into token events."""
    if chunk is None:
        return
    if isinstance(chunk, str):
        if chunk:
            yield "token", {"text": chunk}
        return
    if isinstance(chunk, dict):
        # common shapes: {"content": ...}, {"text": ...}, {"delta": ...}
        for k in ("text", "content", "delta", "output"):
            v = chunk.get(k)
            if isinstance(v, str) and v:
                yield "token", {"text": v}
                return
        return
    # Iterable fallback (unlikely for non-string)
    try:
        for sub in chunk:
            yield from _yield_result(sub)
    except TypeError:
        yield "token", {"text": str(chunk)}


def _drain_async_gen(agen) -> Iterator[tuple[str, dict]]:
    """Bridge an ``async def __anext__`` generator into a sync iterator."""
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                chunk = loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                return
            yield from _yield_result(chunk)
    finally:
        loop.close()


# ── 4. Fallback ──────────────────────────────────────────────────────────────


class NoBackendAdapter(Adapter):
    name = "none"

    def stream(self, turn: ChatTurn) -> Iterable[tuple[str, dict]]:
        del turn
        yield "error", {
            "error": "hermes_agent_not_configured",
            "detail": "Set HERMES_API_URL, install hermes-agent under ~/.hermes/hermes-agent, "
            "or set HERMES_GUI_FAKE_BACKEND=echo for dev.",
        }


# ── Selection ────────────────────────────────────────────────────────────────


def select(cfg: Config) -> Adapter:
    if cfg.fake_backend == "echo":
        logger.info("runtime: EchoAdapter (HERMES_GUI_FAKE_BACKEND=echo)")
        return EchoAdapter()
    if cfg.hermes_api_url:
        logger.info("runtime: GatewayAdapter (%s)", cfg.hermes_api_url)
        return GatewayAdapter(cfg.hermes_api_url, cfg.hermes_api_token)
    agent_dir = Path.home() / ".hermes" / "hermes-agent"
    if agent_dir.exists():
        logger.info("runtime: EmbeddedAdapter (%s)", agent_dir)
        return EmbeddedAdapter(agent_dir)
    logger.warning("runtime: NoBackendAdapter")
    return NoBackendAdapter()
