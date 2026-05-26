from __future__ import annotations

from .claude_code import Bridge as ClaudeCode
from .codex import Bridge as Codex
from .gemini import Bridge as Gemini
from .opencode import Bridge as OpenCode
from .openclaw import Bridge as OpenClaw

BRIDGES = {b.name: b for b in [ClaudeCode(), Codex(), Gemini(), OpenCode(), OpenClaw()]}
