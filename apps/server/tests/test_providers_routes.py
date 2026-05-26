from __future__ import annotations


def test_provider_routes_create_list_models_and_errors(client):
    assert client('POST', '/api/auth/login', body={'password': 'test-pass'})[0] == 200

    sc, presets = client('GET', '/api/providers/presets')
    assert sc == 200
    assert len(presets['presets']) == 14

    sc, bad = client('POST', '/api/providers', body={'kind': 'openai', 'label': 'Bad', 'api_key': 'nope'})
    assert sc == 400
    assert bad['error'] == 'invalid_api_key_format'

    sc, provider = client('POST', '/api/providers', body={'kind': 'anthropic', 'label': 'Anthropic Main', 'api_key': 'sk-ant-abcdefghij'})
    assert sc == 201
    pid = provider['id']

    sc, dup = client('POST', '/api/providers', body={'kind': 'anthropic', 'label': 'anthropic main', 'api_key': 'sk-ant-abcdefghij'})
    assert sc == 409
    assert dup['error'] == 'provider_label_taken'

    sc, listed = client('GET', '/api/providers')
    assert sc == 200
    assert listed['providers'][0]['label'] == 'Anthropic Main'

    sc, models = client('GET', f'/api/providers/{pid}/models')
    assert sc == 200
    assert any(m['id'] == 'claude-opus-4' for m in models['models'])

    sc, parsed = client('POST', '/api/slash/parse', body={'text': '/model gpt-4 --temp 0.7'})
    assert sc == 200
    assert parsed['command'] == 'model'
    assert parsed['args'] == ['gpt-4']
    assert parsed['options'] == {'temp': '0.7'}
