"""14 preset provider metadata — Phase 16."""

from __future__ import annotations

from .models import PRESET_KINDS, ProviderPreset

PRESETS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        "openai", "OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY", "bearer",
        default_models=["gpt-4o", "gpt-4o-mini", "gpt-4.1", "o4-mini"],
    ),
    "anthropic": ProviderPreset(
        "anthropic", "Anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "bearer",
        default_models=["claude-opus-4", "claude-sonnet-4", "claude-3-5-haiku-latest"],
    ),
    "google": ProviderPreset(
        "google", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta", "GOOGLE_API_KEY", "bearer",
        default_models=["gemini-2.5-pro", "gemini-2.5-flash"],
    ),
    "xai": ProviderPreset("xai", "xAI", "https://api.x.ai/v1", "XAI_API_KEY", "bearer", default_models=["grok-3", "grok-3-mini"]),
    "openrouter": ProviderPreset("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "bearer", default_models=["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"]),
    "nous_portal": ProviderPreset("nous_portal", "Nous Portal", "https://portal.nousresearch.com/api/v1", "NOUS_PORTAL_API_KEY", "oauth", scopes=["models", "chat"], default_models=["hermes-3-llama-3.1-405b"]),
    "qwen": ProviderPreset("qwen", "Qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1", "QWEN_API_KEY", "bearer", default_models=["qwen-plus", "qwen-max"]),
    "minimax": ProviderPreset("minimax", "MiniMax", "https://api.minimax.io/v1", "MINIMAX_API_KEY", "bearer", default_models=["abab6.5s-chat"]),
    "huggingface": ProviderPreset("huggingface", "Hugging Face", "https://api-inference.huggingface.co/v1", "HUGGINGFACE_API_KEY", "bearer", default_models=["meta-llama/Llama-3.1-8B-Instruct"]),
    "groq": ProviderPreset("groq", "Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "bearer", default_models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]),
    "lm_studio": ProviderPreset("lm_studio", "LM Studio", "http://127.0.0.1:1234/v1", "LM_STUDIO_API_KEY", "none", default_models=["local-model"]),
    "ollama": ProviderPreset("ollama", "Ollama", "http://127.0.0.1:11434", "OLLAMA_API_KEY", "none", default_models=["llama3.1", "mistral"]),
    "vllm": ProviderPreset("vllm", "vLLM", "http://127.0.0.1:8000/v1", "VLLM_API_KEY", "none", default_models=["local-vllm"]),
    "llama_cpp": ProviderPreset("llama_cpp", "llama.cpp", "http://127.0.0.1:8080/v1", "LLAMA_CPP_API_KEY", "none", default_models=["local-llama-cpp"]),
}

assert tuple(PRESETS.keys()) == PRESET_KINDS


def get_preset(kind: str) -> ProviderPreset | None:
    return PRESETS.get(kind)


def list_presets() -> list[ProviderPreset]:
    return [PRESETS[k] for k in PRESET_KINDS]
