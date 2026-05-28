"""Provider model discovery with 5-minute cache — Phase 16."""

from __future__ import annotations

import ipaddress
import json
import socket
import time
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import replace
from urllib.parse import urlsplit

from .catalog import get_preset
from .models import ModelInfo, Provider

CACHE_TTL_SECONDS = 300
_LOCAL_KINDS = {"lm_studio", "ollama", "vllm", "llama_cpp"}
_CACHE: dict[str, tuple[float, list[ModelInfo]]] = {}


class DiscoveryError(RuntimeError):
    def __init__(self, code: str, detail: str | None = None, status_code: int | None = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code
        self.status_code = status_code


def clear_cache() -> None:
    _CACHE.clear()


def _model(provider: Provider, model_id: str, *, context: int = 8000, caps: list[str] | None = None) -> ModelInfo:
    return ModelInfo(
        id=model_id,
        provider_id=provider.id,
        context_window=context,
        pricing_in_per_1m_usd=0.0,
        pricing_out_per_1m_usd=0.0,
        capabilities=(caps or ["chat"]),  # type: ignore[arg-type]
    )


def _static_models(provider: Provider) -> list[ModelInfo]:
    preset = get_preset(provider.kind)
    ids = preset.default_models if preset else []
    return [_model(provider, mid, context=200000 if provider.kind == "anthropic" else 128000) for mid in ids]


def _validate_fetch_url(provider: Provider, url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DiscoveryError("invalid_provider_url", "base_url must be http(s)")
    if provider.kind in _LOCAL_KINDS:
        return
    host = parsed.hostname
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        return
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise DiscoveryError("provider_private_ip_blocked", "provider base_url resolves to a private address")


def _validate_base_url(provider: Provider) -> None:
    _validate_fetch_url(provider, provider.base_url)


class _ProviderRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, provider: Provider) -> None:
        super().__init__()
        self.provider = provider

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        target = urllib.parse.urljoin(req.full_url, newurl.replace(" ", "%20"))
        _validate_fetch_url(self.provider, target)
        old_host = (urlsplit(req.full_url).hostname or "").lower()
        new_host = (urlsplit(target).hostname or "").lower()
        if old_host != new_host:
            raise DiscoveryError(
                "provider_redirect_blocked",
                "provider model discovery redirects must stay on the configured host",
            )
        return super().redirect_request(req, fp, code, msg, headers, target)


def discover_models(provider: Provider, api_key: str = "", *, now: float | None = None, use_cache: bool = True) -> tuple[list[ModelInfo], float, bool]:
    ts = time.time() if now is None else now
    if use_cache and provider.id in _CACHE:
        cached_at, models = _CACHE[provider.id]
        if ts - cached_at < CACHE_TTL_SECONDS:
            return models, cached_at, True

    if provider.kind == "anthropic":
        models = _static_models(provider)
    else:
        try:
            _validate_base_url(provider)
            if provider.kind == "google":
                models = _fetch_google_models(provider, api_key)
            elif provider.kind == "ollama":
                models = _fetch_ollama_tags(provider)
            else:
                models = _fetch_openai_compat(provider, api_key)
        except DiscoveryError:
            raise
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise DiscoveryError("provider_auth_failed", str(exc), exc.code) from exc
            if exc.code >= 500:
                raise DiscoveryError("provider_server_error", str(exc), exc.code) from exc
            models = _static_models(provider)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            models = _static_models(provider)

    _CACHE[provider.id] = (ts, models)
    return models, ts, False


def _headers(api_key: str) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _fetch_json(provider: Provider, url: str, api_key: str = "") -> dict:
    _validate_fetch_url(provider, url)
    req = urllib.request.Request(url, method="GET", headers=_headers(api_key))
    opener = urllib.request.build_opener(_ProviderRedirectHandler(provider))
    with opener.open(req, timeout=4.5) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def _fetch_openai_compat(provider: Provider, api_key: str) -> list[ModelInfo]:
    data = _fetch_json(provider, f"{provider.base_url.rstrip('/')}/models", api_key)
    items = data.get("data") if isinstance(data, dict) else []
    out: list[ModelInfo] = []
    for m in items if isinstance(items, list) else []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        out.append(
            _model(
                provider,
                str(m["id"]),
                context=int(m.get("context_length") or m.get("context_window") or 8000),
                caps=["chat", "tools"] if m.get("supports_tools") else ["chat"],
            )
        )
    return out or _static_models(provider)


def _fetch_google_models(provider: Provider, api_key: str) -> list[ModelInfo]:
    sep = "&" if "?" in provider.base_url else "?"
    url = f"{provider.base_url.rstrip('/')}/models"
    if api_key:
        url = f"{url}{sep}key={api_key}"
    data = _fetch_json(provider, url)
    models = data.get("models", []) if isinstance(data, dict) else []
    out = []
    for item in models if isinstance(models, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").split("/")[-1]
        if name:
            out.append(_model(provider, name, context=int(item.get("inputTokenLimit") or 32768)))
    return out or _static_models(provider)


def _fetch_ollama_tags(provider: Provider) -> list[ModelInfo]:
    data = _fetch_json(provider, f"{provider.base_url.rstrip('/')}/api/tags")
    items = data.get("models", []) if isinstance(data, dict) else []
    out = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and item.get("name"):
            out.append(_model(provider, str(item["name"]), context=8192))
    return out or _static_models(provider)
