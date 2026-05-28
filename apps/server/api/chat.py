"""POST /api/chat/stream — Phase 1 → Phase 2 (session-aware).

Request:
  { "messages":[{"role":"user","content":"..."}], "session_id"?, "save"?: true }

If ``session_id`` is supplied the turn is appended to the session and the
final ``done`` event carries the resolved session id. The user/assistant
turns are persisted in the SQLite store from sessions/lifecycle.py.
"""

from __future__ import annotations

import logging
from http import HTTPStatus

from . import auth as auth_module
from . import streaming
from . import pii
from .config import Config
from .router import Request, Response, Router
from .runtime_adapter import Adapter, ChatTurn
from .compression.inject import maybe_inject
from . import usage
from .sessions import Message, SessionStore, alias_resolve
from .sessions.events import events as session_events

logger = logging.getLogger(__name__)


def _session_title_from_messages(messages: list[dict]) -> str:
    last_user = next(
        (str(m.get("content") or "").strip() for m in reversed(messages) if isinstance(m, dict) and m.get("role") == "user"),
        "",
    )
    return (last_user[:60] or "New chat").replace("\n", " ")


def register_routes(cfg: Config, adapter: Adapter, store: SessionStore) -> Router:
    router = Router()

    @router.route("POST", "/api/chat/stream")
    def _stream(req: Request):
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

        messages_raw = body.get("messages")
        if not isinstance(messages_raw, list) or not messages_raw:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "messages_required"})

        session_id = body.get("session_id")
        save = bool(body.get("save", True))
        resolved_sid = alias_resolve(str(session_id)) if session_id else None
        sess = store.get(resolved_sid) if resolved_sid else None
        model = str(body.get("model") or "auto")
        provider_id = str(body.get("provider_id") or "auto")
        profile = str(body.get("profile") or "default")
        auto_created = False

        if save and sess is None and bool(body.get("auto_create_session")):
            sess = store.create(
                title=str(body.get("title") or _session_title_from_messages(messages_raw)),
                profile=profile,
            )
            resolved_sid = sess.id
            auto_created = True
            session_events.publish("session_list_changed", {"session_id": sess.id})

        def cleanup_auto_created(reason: str) -> None:
            if auto_created and sess is not None:
                store.delete(sess.id)
                session_events.publish(
                    "session_deleted",
                    {"session_id": sess.id, "reason": reason},
                )

        # Phase 19: redact PII from the adapter payload only. Server-side visible
        # session persistence keeps the original local transcript.
        redacted_messages: list[dict] = []
        pii_findings: list[dict] = []
        for message in messages_raw:
            if isinstance(message, dict):
                clean, findings = pii.redact_message(message)
                redacted_messages.append(clean)
                pii_findings.extend(findings)

        # Phase 18: inject compressed RAG context only into the adapter payload.
        adapter_messages = maybe_inject(redacted_messages or messages_raw, session_id=sess.id if sess is not None else resolved_sid)

        # Phase 2: hydrate from session if requested but body did not include history.
        # The body messages remain the authoritative visible new turn.
        turn = ChatTurn(messages=adapter_messages, session_id=resolved_sid, model=model, provider_id=provider_id)

        streaming.begin_sse(req.raw)
        if pii_findings:
            streaming.write_event(req.raw, "pii_redacted", {"redactions": pii_findings})
        assistant_buf: list[str] = []
        adapter_name = adapter.name
        stream_error = False
        for event, data in adapter.stream(turn):
            if event == "token":
                assistant_buf.append(str(data.get("text") or ""))
            if event == "error":
                stream_error = True
            if not streaming.write_event(req.raw, event, data):
                logger.debug("client gone — aborting stream")
                cleanup_auto_created("client_disconnected")
                return None
            if event in {"done", "error"}:
                break

        # Persist new turn (user + assistant) if a session was attached.
        if stream_error and auto_created:
            cleanup_auto_created("stream_error")
            return None
        if save and sess is not None:
            last_user = next(
                (m for m in reversed(messages_raw) if (m.get("role") == "user")),
                None,
            )
            new_messages: list[Message] = []
            if last_user and last_user.get("content"):
                new_messages.append(Message(role="user", content=str(last_user["content"])))
            if assistant_buf:
                new_messages.append(
                    Message(
                        role="assistant",
                        content="".join(assistant_buf),
                        tool_calls=[],
                    )
                )
            if new_messages:
                store.append_messages(sess.id, new_messages)
                session_events.publish(
                    "session_updated",
                    {"session_id": sess.id, "adapter": adapter_name},
                )
                try:
                    usage.record_turn(
                        session_id=sess.id,
                        profile=sess.profile,
                        provider_id=provider_id,
                        model_id=model,
                        input_tokens=sum(usage.estimate_tokens(str(m.get("content") or "")) for m in messages_raw),
                        output_tokens=usage.estimate_tokens("".join(assistant_buf)),
                    )
                except Exception:  # noqa: BLE001 -- usage accounting must not break chat
                    logger.exception("usage accounting failed")
            else:
                cleanup_auto_created("no_persisted_messages")
        return None

    return router
