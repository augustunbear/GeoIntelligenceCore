"""Offline activation validation; no provider requests or real credentials."""
import json

import pytest

from .live_gate import require_live_activation


def activate(tmp_path, monkeypatch, *, provider='photon', **changes):
    record = dict.fromkeys((
        'approved_origin', 'instance_owner', 'instance_version', 'terms_ref',
        'rights_ref', 'quota_ref', 'pricing_ref', 'purpose', 'samples_ref',
        'thresholds_ref', 'currency',
    ), 'synthetic-reference')
    record.update(approved=True, max_calls=3, max_concurrency=1, deadline_s=5,
                  max_response_bytes=1024, cost_ceiling=0)
    record.update(changes)
    path = tmp_path / 'activation.json'
    path.write_text(json.dumps({provider: record}))
    monkeypatch.setenv('GEO_LIVE_TESTS', '1')
    monkeypatch.setenv('GEO_LIVE_ACTIVATION_FILE', str(path))
    return record


def allowed():
    try:
        return require_live_activation('photon')
    except pytest.skip.Exception as exc:
        pytest.fail(f'valid free configuration rejected: {exc}')


def test_free_public_record_needs_no_credential(tmp_path, monkeypatch):
    expected = activate(tmp_path, monkeypatch)
    assert allowed() == expected


def test_keyed_free_record_still_requires_key(tmp_path, monkeypatch):
    activate(tmp_path, monkeypatch, credential_env='SYNTHETIC_PROVIDER_KEY')
    monkeypatch.delenv('SYNTHETIC_PROVIDER_KEY', raising=False)
    with pytest.raises(pytest.skip.Exception):
        require_live_activation('photon')
    monkeypatch.setenv('SYNTHETIC_PROVIDER_KEY', 'synthetic-not-a-secret')
    assert allowed()['cost_ceiling'] == 0


@pytest.mark.parametrize('changes', [
    {'cost_ceiling': -1}, {'cost_ceiling': 'NaN'}, {'cost_ceiling': None},
    {'max_calls': 0}, {'max_calls': True}, {'deadline_s': float('inf')},
    {'max_concurrency': -1}, {'max_response_bytes': 0}, {'pricing_ref': ''},
    {'approved': False}, {'credential_env': ''},
])
def test_invalid_limits_remain_blocked(tmp_path, monkeypatch, changes):
    activate(tmp_path, monkeypatch, **changes)
    with pytest.raises(pytest.skip.Exception):
        require_live_activation('photon')


def test_hosted_ors_requires_explicit_key(tmp_path, monkeypatch):
    activate(tmp_path, monkeypatch, provider='ors')
    with pytest.raises(pytest.skip.Exception):
        require_live_activation('ors')


def test_explicit_no_key_self_hosted_ors(tmp_path, monkeypatch):
    expected = activate(tmp_path, monkeypatch, provider='ors', authentication_required=False)
    try:
        assert require_live_activation('ors') == expected
    except pytest.skip.Exception as exc:
        pytest.fail(f'explicit no-key instance rejected: {exc}')
