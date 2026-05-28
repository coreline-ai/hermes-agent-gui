from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from ..validation import ValidationError, parse_bounded_int, validation_response
from .extractor import extract
from .graph import list_edges, list_nodes, upsert
from .synthesizer import synthesize
from .traversal import query_graph


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/brain/ingest")
    def _ingest(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        extracted = extract(str(body.get("text") or ""), source=str(body.get("source") or "manual"))
        stats = upsert(extracted["nodes"], extracted["edges"])
        return Response(HTTPStatus.OK, {"extracted": extracted, "stats": stats})

    @router.route("POST", "/api/brain/query")
    def _query(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        question = str(body.get("q") or "")
        try:
            depth = parse_bounded_int(body.get("depth"), field="depth", default=3, min_value=1, max_value=5)
        except ValidationError as exc:
            return validation_response(exc)
        graph = query_graph(question, depth=depth)
        return Response(HTTPStatus.OK, {"graph": graph, "synthesis": synthesize(question, graph)})

    @router.route("GET", "/api/brain/nodes")
    def _nodes(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        q = (req.query.get("q") or [""])[0]
        return Response(HTTPStatus.OK, {"nodes": [n.to_dict() for n in list_nodes(q or None)]})

    @router.route("GET", "/api/brain/graph")
    def _graph(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"nodes": [n.to_dict() for n in list_nodes()], "edges": [e.to_dict() for e in list_edges()]})

    return router
