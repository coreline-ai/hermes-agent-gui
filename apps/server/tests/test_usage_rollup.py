from __future__ import annotations

from datetime import date, datetime, timezone

from api.providers.models import ModelInfo
from api.usage import UsageTurn, calc_cost


def test_usage_cost_gpt4o_one_million_input_tokens():
    turn = UsageTurn('u1', 's1', 'default', 'openai', 'gpt-4o', 1_000_000, 0, 0.0, False, 0)
    model = ModelInfo('gpt-4o', 'openai', 128000, 2.5, 10.0, ['chat'])
    assert calc_cost(turn, model) == 2.5


def test_usage_daily_rollup_fills_empty_days(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_GUI_STATE_DIR', str(tmp_path / 'state'))
    from importlib import reload
    import api.config as config_mod
    import api.sessions.lifecycle as lifecycle
    import api.usage as usage_mod

    reload(config_mod)
    reload(lifecycle)
    reload(usage_mod)
    ts = int(datetime(2026, 5, 24, tzinfo=timezone.utc).timestamp())
    usage_mod.record_turn(
        session_id='s1',
        model_id='gpt-4o',
        input_tokens=1_000_000,
        output_tokens=0,
        created_at=ts,
    )
    out = usage_mod.summary(date(2026, 5, 23), date(2026, 5, 25))

    assert [d['date'] for d in out['daily']] == ['2026-05-23', '2026-05-24', '2026-05-25']
    assert out['daily'][0]['tokens'] == 0
    assert out['daily'][1]['tokens'] == 1_000_000
    assert out['total_cost_usd'] == 2.5
