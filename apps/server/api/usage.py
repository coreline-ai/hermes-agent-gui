"""Usage rollup and cost calculation — Phase 17."""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .providers.models import ModelInfo
from .router import Request, Response, Router
from .sessions.lifecycle import SESSIONS_DB

PRICING_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "gemini-2.5-pro": (1.25, 10.0),
}


@dataclass(frozen=True)
class UsageTurn:
    id: str
    session_id: str
    profile: str
    provider_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_hit: bool
    created_at: int


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_turns (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              profile TEXT NOT NULL DEFAULT 'default',
              provider_id TEXT NOT NULL,
              model_id TEXT NOT NULL,
              input_tokens INTEGER NOT NULL,
              output_tokens INTEGER NOT NULL,
              cost_usd REAL NOT NULL,
              cache_hit INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_turns(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_turns(model_id)")


def calc_cost(usage_turn: UsageTurn, model_info: ModelInfo) -> float:
    in_cost = (usage_turn.input_tokens / 1_000_000) * model_info.pricing_in_per_1m_usd
    out_cost = (usage_turn.output_tokens / 1_000_000) * model_info.pricing_out_per_1m_usd
    if usage_turn.cache_hit:
        in_cost *= 0.5
    return round(in_cost + out_cost, 6)


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4)) if text else 0


def _model_info(model_id: str, provider_id: str = "auto") -> ModelInfo:
    price = PRICING_USD_PER_1M.get(model_id, (0.0, 0.0))
    return ModelInfo(model_id, provider_id, 128000, price[0], price[1], ["chat"])


def record_turn(
    *,
    session_id: str,
    profile: str = "default",
    provider_id: str = "auto",
    model_id: str = "auto",
    input_tokens: int,
    output_tokens: int,
    cache_hit: bool = False,
    created_at: int | None = None,
) -> UsageTurn:
    ensure_schema()
    created = int(time.time()) if created_at is None else created_at
    base = UsageTurn(uuid.uuid4().hex[:12], session_id, profile, provider_id, model_id, input_tokens, output_tokens, 0.0, cache_hit, created)
    cost = calc_cost(base, _model_info(model_id, provider_id))
    turn = UsageTurn(base.id, session_id, profile, provider_id, model_id, input_tokens, output_tokens, cost, cache_hit, created)
    with _conn() as c:
        c.execute(
            "INSERT INTO usage_turns(id,session_id,profile,provider_id,model_id,input_tokens,output_tokens,cost_usd,cache_hit,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (turn.id, turn.session_id, turn.profile, turn.provider_id, turn.model_id, turn.input_tokens, turn.output_tokens, turn.cost_usd, 1 if turn.cache_hit else 0, turn.created_at),
        )
    return turn


def _parse_date(raw: str | None, fallback: date) -> date:
    if not raw:
        return fallback
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _date_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def summary(from_date: date, to_date: date) -> dict:
    if from_date > to_date:
        raise ValueError("invalid_date_range")
    ensure_schema()
    start_ts = int(datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc).timestamp())
    end_ts = int((datetime(to_date.year, to_date.month, to_date.day, tzinfo=timezone.utc) + timedelta(days=1)).timestamp())
    with _conn() as c:
        rows = c.execute(
            "SELECT session_id,model_id,input_tokens,output_tokens,cost_usd,cache_hit,created_at FROM usage_turns WHERE created_at>=? AND created_at<?",
            (start_ts, end_ts),
        ).fetchall()
    total_in = sum(int(r[2]) for r in rows)
    total_out = sum(int(r[3]) for r in rows)
    total_cost = round(sum(float(r[4]) for r in rows), 6)
    sessions = len({r[0] for r in rows})
    by_model_map: dict[str, dict[str, float | int | str]] = {}
    daily_map: dict[str, dict[str, float | int | str]] = {}
    cursor = from_date
    while cursor <= to_date:
        key = cursor.isoformat()
        daily_map[key] = {"date": key, "cost_usd": 0.0, "tokens": 0}
        cursor += timedelta(days=1)
    for r in rows:
        model = str(r[1])
        tokens = int(r[2]) + int(r[3])
        entry = by_model_map.setdefault(model, {"model_id": model, "cost_usd": 0.0, "tokens": 0})
        entry["cost_usd"] = round(float(entry["cost_usd"]) + float(r[4]), 6)
        entry["tokens"] = int(entry["tokens"]) + tokens
        day = _date_key(int(r[6]))
        if day in daily_map:
            daily_map[day]["cost_usd"] = round(float(daily_map[day]["cost_usd"]) + float(r[4]), 6)
            daily_map[day]["tokens"] = int(daily_map[day]["tokens"]) + tokens
    days = max(1, (to_date - from_date).days + 1)
    return {
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_cost_usd": total_cost,
        "sessions": sessions,
        "avg_per_day": round(total_cost / days, 6),
        "cache_hit_rate": round(sum(1 for r in rows if int(r[5])) / len(rows), 4) if rows else 0.0,
        "by_model": sorted(by_model_map.values(), key=lambda x: float(x["cost_usd"]), reverse=True),
        "daily": [daily_map[k] for k in sorted(daily_map)],
    }


def register_routes(cfg: Config) -> Router:
    ensure_schema()
    router = Router()

    @router.route("GET", "/api/usage/summary")
    def _summary(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        today = date.today()
        try:
            from_d = _parse_date((req.query.get("from") or [None])[0], today - timedelta(days=29))
            to_d = _parse_date((req.query.get("to") or [None])[0], today)
            return Response(HTTPStatus.OK, summary(from_d, to_d))
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": str(exc) or "invalid_date_range"})

    return router
