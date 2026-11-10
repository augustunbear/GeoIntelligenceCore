"""Synthetic caller-supplied facts, never live transport coverage."""
from datetime import datetime, timezone
import json

import pytest

from geo_intelligence_core import Evidence, Quality, RequestContext, Rights, Status
from geo_intelligence_core.inputs.transport import import_transport, TransportFact

NOW = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
CONTEXT = RequestContext(request_id='synthetic-transport')


def evidence(**changes):
    values = dict(id='e1', source_id='synthetic', source_type='manual', source_ref='fixture',
                  retrieved_at=NOW, method_version='synthetic-v1',
                  rights=Rights(use='allowed', permitted_purpose='research'), quality=Quality())
    values.update(changes)
    return Evidence(**values)


def record(**changes):
    values = dict(id='parking-1', kind='parking_capacity', value=80, unit='spaces',
                  location={'longitude': 11, 'latitude': 49},
                  valid_from='2026-11-10T10:00:00Z', valid_until='2026-11-10T14:00:00Z',
                  measured_at='2026-11-10T10:00:00Z', evidence_ids=['e1'])
    values.update(changes)
    return values


def run(records, **changes):
    args = dict(evidence=[evidence()], purpose='research', as_of=NOW, context=CONTEXT)
    args.update(changes)
    return import_transport(records, **args)


def test_capacity_does_not_create_current_free_spaces():
    result = run([record()])
    assert result.status == Status.ok
    assert len(result.data) == 1
    assert result.data[0].kind == 'parking_capacity'
    assert result.data[0].value == 80
    assert result.evidence == (evidence(),)
    assert TransportFact.model_validate(result.data[0].model_dump(mode='json')) == result.data[0]


@pytest.mark.parametrize('kind', ['parking_free_spaces', 'parking_capacity'])
@pytest.mark.parametrize('value', [-1, True, 1.2, '80'])
def test_counts_are_nonnegative_strict_integers(kind, value):
    assert run([record(kind=kind, value=value)]).status == Status.invalid_input


@pytest.mark.parametrize('changes', [dict(valid_until='2026-11-10T12:00:00Z'),
    dict(valid_from='2026-11-11T00:00:00Z', valid_until='2026-11-12T00:00:00Z')])
def test_noncurrent_free_spaces_are_not_returned(changes):
    result = run([record(kind='parking_free_spaces', **changes)])
    assert result.status == Status.unavailable
    assert result.data is None and result.evidence == ()


@pytest.mark.parametrize('kind', ['accessibility', 'cycling_restriction', 'construction'])
def test_restrictions_require_explicit_segment_direction_and_period(kind):
    scoped = record(kind=kind, value='restricted', unit='statement', segment_ref='segment-A', direction='forward')
    assert run([scoped]).status == Status.ok
    for field in ['segment_ref', 'direction', 'valid_from', 'valid_until']:
        assert run([{k: v for k, v in scoped.items() if k != field}]).status == Status.invalid_input
    assert run([dict(scoped, direction='unknown')]).status == Status.invalid_input


@pytest.mark.parametrize('changes', [dict(kind='child_safe', value=True), dict(child_safe=True),
    dict(kind='ordinary_route'), dict(evidence_ids=[]), dict(evidence_ids=['missing']),
    dict(evidence_ids=['e1', 'e1']), dict(id=' '), dict(unit='cars'),
    dict(measured_at='2026-11-11T00:00:00Z'), dict(measured_at='2026-11-10T10:00:00'),
    dict(valid_until='2026-11-10T09:00:00Z')])
def test_invalid_or_inferred_claim_rejects_entire_batch(changes):
    result = run([record(), record(id='other', **changes)] if 'id' not in changes else [record(**changes)])
    assert result.status == Status.invalid_input
    assert result.data is None and result.evidence == ()


@pytest.mark.parametrize('rights', [Rights(), Rights(use='denied', permitted_purpose='research'),
    Rights(use='allowed', permitted_purpose='other')])
def test_rights_and_purpose_fail_closed(rights):
    result = run([record()], evidence=[evidence(rights=rights)])
    assert result.status == Status.unavailable and result.data is None


def test_evidence_duplicates_and_unused_sources_rejected():
    assert run([record()], evidence=[evidence(), evidence()]).status == Status.invalid_input
    assert run([record()], evidence=[evidence(), evidence(id='unused')]).status == Status.invalid_input


def test_empty_and_bounded_inputs():
    assert run([], evidence=[]).status == Status.no_results
    assert run([record()] * 1001).status == Status.invalid_input
    assert run([record(id='x' * 1048576)]).status == Status.invalid_input
    assert run([record(), record()]).status == Status.invalid_input
    assert run([record(value=float('nan'))]).status == Status.invalid_input
    assert run([record()], purpose=' ').status == Status.invalid_input
    assert run([record()], as_of=NOW.replace(tzinfo=None)).status == Status.invalid_input


def test_fee_is_explicit_and_not_a_free_space_count():
    result = run([record(kind='parking_fee', value='EUR 2/hour', unit='statement')])
    assert result.status == Status.ok
    assert json.loads(result.model_dump_json())['data'][0]['value'] == 'EUR 2/hour'


def test_additional_evidence_and_scope_validation():
    assert run([record()], evidence=[evidence()] * 101).status == Status.invalid_input
    assert run([record()], evidence=[evidence(retrieved_at=datetime(2027, 1, 1, tzinfo=timezone.utc))]).status == Status.invalid_input
    assert run([record(kind='construction', value='closed', unit='statement',
                       segment_ref=' ', direction='both')]).status == Status.invalid_input
    assert run([record(kind='parking_fee', value='', unit='statement')]).status == Status.invalid_input
    assert run([record(location={'longitude': 200, 'latitude': 49})]).status == Status.invalid_input


def test_validity_starts_inclusively_and_result_is_immutable():
    result = run([record(valid_from=NOW.isoformat())])
    assert result.status == Status.ok
    with pytest.raises(Exception):
        result.data[0].value = 90


def test_empty_batch_cannot_discard_supplied_evidence():
    assert run([]).status == Status.invalid_input


@pytest.mark.parametrize('field', ['source_ref', 'attribution'])
def test_oversized_evidence_is_rejected_before_serialization(monkeypatch, field):
    huge = 'x' * 1048577
    source = evidence(source_ref=huge) if field == 'source_ref' else evidence(
        rights=Rights(use='allowed', permitted_purpose='research', attribution=huge))
    def forbidden_dump(*args, **kwargs):
        raise AssertionError('oversized evidence must not be serialized')
    monkeypatch.setattr(Evidence, 'model_dump', forbidden_dump)
    assert run([record()], evidence=[source]).status == Status.invalid_input


@pytest.mark.parametrize('context', [None, {'request_id': ''}, {'unexpected': True}])
def test_malformed_context_returns_safe_invalid_input(context):
    result = run([record()], context=context)
    assert result.status == Status.invalid_input
    assert result.data is None and result.evidence == ()
    assert result.context.request_id == 'transport-invalid-input'
