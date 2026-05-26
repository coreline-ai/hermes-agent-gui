from __future__ import annotations

from api.slash_commands import COMMAND_NAMES, parse_slash_command


def test_slash_command_count_is_22():
    assert len(COMMAND_NAMES) == 22


def test_slash_model_parsing_splits_args_and_options():
    parsed = parse_slash_command('/model gpt-4 --temp 0.7 --stream')
    assert parsed.command == 'model'
    assert parsed.args == ['gpt-4']
    assert parsed.options == {'temp': '0.7', 'stream': True}
