from __future__ import annotations


def test_persona_presets_and_save(client):
    assert client('POST', '/api/auth/login', body={'password': 'test-pass'})[0] == 200
    sc, presets = client('GET', '/api/persona/presets')
    assert sc == 200
    assert [p['id'] for p in presets['presets']] == ['sage', 'trader', 'builder', 'scribe', 'ops', 'coder']

    sc, saved = client('PUT', '/api/persona', body={'soul_md': '# Coder\nBe strict.'})
    assert sc == 200
    assert saved['ok'] is True

    sc, persona = client('GET', '/api/persona')
    assert sc == 200
    assert persona['soul_md'] == '# Coder\nBe strict.'


def test_persona_rejects_large_soul(client):
    assert client('POST', '/api/auth/login', body={'password': 'test-pass'})[0] == 200
    sc, body = client('PUT', '/api/persona', body={'soul_md': 'x' * (101 * 1024)})
    assert sc == 413
    assert body['error'] == 'payload_too_large'
