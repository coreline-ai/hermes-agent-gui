"""Provider data models — Phase 16."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProviderKind = Literal[
    "openai", "anthropic", "google", "xai", "openrouter", "nous_portal",
    "qwen", "minimax", "huggingface", "groq",
    "lm_studio", "ollama", "vllm", "llama_cpp", "custom",
]
AuthType = Literal["bearer", "oauth", "none"]
Capability = Literal["chat", "embed", "vision", "tools"]

PRESET_KINDS: tuple[str, ...] = (
    "openai", "anthropic", "google", "xai", "openrouter", "nous_portal",
    "qwen", "minimax", "huggingface", "groq",
    "lm_studio", "ollama", "vllm", "llama_cpp",
)


@dataclass(frozen=True)
class ProviderPreset:
    kind: str
    label: str
    base_url: str
    api_key_env: str
    auth_type: AuthType
    scopes: list[str] = field(default_factory=list)
    default_models: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "auth_type": self.auth_type,
            "scopes": self.scopes,
            "default_models": self.default_models,
            "extra": self.extra,
        }


@dataclass(frozen=True)
class Provider:
    id: str
    kind: str
    label: str
    base_url: str
    api_key_env: str
    auth_type: AuthType
    enabled: bool = True
    extra: dict = field(default_factory=dict)
    test_status: str | None = None
    last_tested_at: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "auth_type": self.auth_type,
            "enabled": self.enabled,
            "extra": self.extra,
            "test_status": self.test_status,
            "last_tested_at": self.last_tested_at,
        }


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider_id: str
    context_window: int
    pricing_in_per_1m_usd: float
    pricing_out_per_1m_usd: float
    capabilities: list[Capability]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "context_window": self.context_window,
            "pricing_in_per_1m_usd": self.pricing_in_per_1m_usd,
            "pricing_out_per_1m_usd": self.pricing_out_per_1m_usd,
            "capabilities": self.capabilities,
        }
