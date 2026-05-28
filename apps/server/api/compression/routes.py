"""HTTP routes for Auto-Compress + RAG — Phase 18."""

from __future__ import annotations

from http import HTTPStatus
import logging

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from ..sessions import SessionStore
from ..validation import ValidationError, parse_bounded_int, validation_response
from .summarizer import summarize_messages
from .trigger import estimate_message_tokens, should_compact
from .vss_store import add_chunk, ensure_schema, list_chunks, search_chunks

logger = logging.getLogger(__name__)


def register_routes(cfg: Config, store: SessionStore) -> Router:
    ensure_schema()
    router = Router()

    @router.route("POST", "/api/sessions/{sid}/compact")
    def _compact(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        sess = store.get(req.params["sid"])
        if sess is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
        try:
            body = req.json()
        except ValueError:
            body = {}
        trigger = str(body.get("trigger") or "manual")
        tokens = estimate_message_tokens(sess.messages)
        if trigger != "manual" and not should_compact(sess, tokens, 128_000):
            return Response(HTTPStatus.OK, {"compacted_chunks": [], "tokens_saved": 0, "skipped": True})
        end = max(0, len(sess.messages) - 1)
        try:
            summary = summarize_messages(sess.messages)
        except Exception:  # noqa: BLE001 -- compaction must be non-fatal
            logger.exception("session compaction failed")
            return Response(HTTPStatus.OK, {"compacted_chunks": [], "tokens_saved": 0, "skipped": True, "error": "summarize_failed"})
        chunk = add_chunk(sess.id, 0, end, summary)
        return Response(HTTPStatus.OK, {"compacted_chunks": [chunk.to_dict()], "tokens_saved": tokens, "fallback": "lexical"})

    @router.route("GET", "/api/sessions/{sid}/memory")
    def _memory(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"chunks": [c.to_dict() for c in list_chunks(req.params["sid"])]})

    @router.route("POST", "/api/memory/search")
    def _search(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        q = str(body.get("q") or "")
        try:
            k = parse_bounded_int(body.get("k"), field="k", default=5, min_value=1, max_value=50)
        except ValidationError as exc:
            return validation_response(exc)
        sid = body.get("session_id_filter")
        results = [chunk.to_dict(score=score) for chunk, score in search_chunks(q, k=k, session_id_filter=str(sid) if sid else None)]
        return Response(HTTPStatus.OK, {"results": results})

    return router
