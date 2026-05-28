"""Server-side slash command parser and stub executor — Phase 16."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from http import HTTPStatus

from . import __version__, auth as auth_module
from .config import Config
from .health import get_health
from .router import Request, Response, Router

COMMAND_NAMES = [
    "new", "clear", "compact", "compress", "undo", "retry",
    "help", "version", "status", "debug",
    "tools", "skills", "model", "memory", "persona",
    "usage", "fast", "web", "image", "browse", "code", "shell",
]


@dataclass(frozen=True)
class ParsedSlashCommand:
    raw: str
    command: str
    args: list[str]
    options: dict[str, str | bool]

    def to_dict(self) -> dict:
        return {"raw": self.raw, "command": self.command, "args": self.args, "options": self.options}


class SlashCommandError(ValueError):
    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


def parse_slash_command(text: str) -> ParsedSlashCommand:
    raw = text.strip()
    if not raw.startswith("/"):
        raise SlashCommandError("not_slash_command")
    try:
        parts = shlex.split(raw[1:])
    except ValueError as exc:
        raise SlashCommandError("invalid_slash_syntax", str(exc)) from exc
    if not parts:
        raise SlashCommandError("command_required")
    command, tokens = parts[0], parts[1:]
    if command not in COMMAND_NAMES:
        raise SlashCommandError("command_unknown", command)
    args: list[str] = []
    opts: dict[str, str | bool] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--") and len(tok) > 2:
            key = tok[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                opts[k] = v
            elif i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                opts[key] = tokens[i + 1]
                i += 1
            else:
                opts[key] = True
        else:
            args.append(tok)
        i += 1
    return ParsedSlashCommand(raw=raw, command=command, args=args, options=opts)


def execute_stub(parsed: ParsedSlashCommand) -> dict:
    if parsed.command in {"compact", "compress"}:
        return {"kind": "navigate", "to": "/rag", "text": "Open /rag to compact or search a saved session."}
    if parsed.command == "usage":
        return {"kind": "navigate", "to": "/usage", "text": "Open /usage for token and cost rollups."}
    if parsed.command == "version":
        return {"kind": "system", "text": __version__}
    if parsed.command == "help":
        return {"kind": "system", "text": "/" + ", /".join(COMMAND_NAMES)}
    if parsed.command == "model":
        if not parsed.args:
            return {"kind": "system", "text": "Usage: /model <model_id> [--temp 0.7]"}
        return {"kind": "system", "text": f"Model switched to {parsed.args[0]}", "model": parsed.args[0], "options": parsed.options}
    return {"kind": "intercept", "text": f"/{parsed.command} is registered; use the matching UI page or integration to execute it."}


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/slash/commands")
    def _commands(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"commands": COMMAND_NAMES})

    @router.route("POST", "/api/slash/parse")
    def _parse(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            parsed = parse_slash_command(str(body.get("text") or ""))
            return Response(HTTPStatus.OK, parsed.to_dict())
        except SlashCommandError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": exc.code, "detail": exc.detail})
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    @router.route("POST", "/api/slash/execute")
    def _execute(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            parsed = parse_slash_command(str(req.json().get("text") or ""))
            if parsed.command == "status":
                return Response(HTTPStatus.OK, {"kind": "system", "health": get_health()})
            return Response(HTTPStatus.OK, execute_stub(parsed))
        except SlashCommandError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": exc.code, "detail": exc.detail})
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    return router
