"""Synthetic schedules only; no network, holiday or real-world freshness claims."""
from datetime import datetime
import importlib
import sys
from zoneinfo import ZoneInfo

import pytest

import geo_intelligence_core as core


def evaluate(raw='Mo 22:00-02:00', at='2026-11-10T00:30:00+00:00', timezone='Europe/Berlin'):
    assert hasattr(core, 'evaluate_opening_hours'), 'opening-hours public API is missing'
    return core.evaluate_opening_hours(raw, at=datetime.fromisoformat(at), timezone=timezone)


@pytest.mark.parametrize(('at', 'state'), [
    ('2026-11-09T20:59:00+00:00', 'closed'),
    ('2026-11-09T21:00:00+00:00', 'open'),
    ('2026-11-10T00:30:00+00:00', 'open'),
    ('2026-11-10T01:00:00+00:00', 'closed'),
])
def test_offset_aware_overnight_boundaries(at, state):
    result = evaluate(at=at)
    assert result.status == core.Status.ok
    assert result.data.state == state
    assert result.data.hours_raw == 'Mo 22:00-02:00'
    assert result.data.evaluated_at == datetime.fromisoformat(at)
    assert result.data.parser == 'opening-hours-py'
    assert result.data.parser_version == '2.1.5'
    assert result.context.method_version == 'opening-hours-evaluation-v1'
    assert result.evidence == ()  # Parsing does not invent source evidence or rights.


@pytest.mark.parametrize(('at', 'state'), [
    ('2026-03-29T00:30:00+00:00', 'closed'),
    ('2026-03-29T01:30:00+00:00', 'open'),
    ('2026-10-25T00:30:00+00:00', 'open'),
    ('2026-10-25T01:30:00+00:00', 'open'),
    ('2026-10-25T02:30:00+00:00', 'open'),
])
def test_berlin_dst_uses_instant_not_wall_time_guess(at, state):
    assert evaluate('Su 02:00-04:00', at=at).data.state == state


@pytest.mark.parametrize('raw', [None, '', 'garbage', 'Mo 99:00-99:30',
    '24/7; PH off', '24/7;PHoff', 'PH09:00-18:00', 'Mo,PH09:00-18:00',
    'PH,Mo 09:00-18:00', 'SH09:00-18:00', '24/7;SH off',
    'sunrise-sunset', '(sunrise+01:00)-sunset', 'dawn-dusk',
    'Mo 09:00+', 'Mo 09:00-17:00+', 'unknown', '"by appointment"'])
def test_unsupported_or_invalid_schedule_fails_closed(raw):
    result = evaluate(raw)
    assert result.status == core.Status.unknown
    assert result.data.state == 'unknown'
    assert result.data.hours_raw == raw
    assert result.issues


@pytest.mark.parametrize(('at', 'timezone'), [
    ('2026-10-25T02:30:00', 'Europe/Berlin'),
    ('2026-03-29T02:30:00', 'Europe/Berlin'),
    ('2026-11-10T12:00:00+00:00', ''),
    ('2026-11-10T12:00:00+00:00', 'Not/AZone'),
    ('1899-01-01T12:00:00+00:00', 'UTC'),
])
def test_missing_or_unsupported_context_is_unknown(at, timezone):
    assert evaluate('24/7', at=at, timezone=timezone).status == core.Status.unknown


def test_equivalent_offsets_and_zoneinfo_fold_represent_same_instants():
    utc = evaluate('Su 02:00-03:00', at='2026-10-25T01:30:00+00:00')
    assert evaluate('Su 02:00-03:00', at='2026-10-25T02:30:00+01:00').data.state == utc.data.state
    at = datetime(2026, 10, 25, 2, 30, tzinfo=ZoneInfo('Europe/Berlin'), fold=1)
    assert core.evaluate_opening_hours('Su 02:00-03:00', at=at, timezone='Europe/Berlin').data.state == 'open'


def test_optional_dependency_absent_returns_unknown(monkeypatch):
    monkeypatch.setitem(sys.modules, 'opening_hours', None)
    assert evaluate('24/7').status == core.Status.unknown


def test_wrong_parser_version_returns_unknown(monkeypatch):
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: '999.0')
    assert evaluate('24/7').status == core.Status.unknown


def test_parser_exception_returns_unknown(monkeypatch):
    import opening_hours
    def broken(*args, **kwargs):
        raise RuntimeError('synthetic backend failure')
    monkeypatch.setattr(opening_hours, 'OpeningHours', broken)
    assert evaluate('24/7').status == core.Status.unknown


@pytest.mark.parametrize('raw', ['easter 09:00-18:00', '24/7; easter off', 'easter -2 days off'])
def test_easter_holiday_selectors_are_unknown(raw):
    assert evaluate(raw).data.state == 'unknown'


def test_unavailable_or_unused_backend_does_not_claim_execution_provenance(monkeypatch):
    assert evaluate('PH09:00-18:00').data.parser is None
    assert evaluate('PH09:00-18:00').data.parser_version is None
    monkeypatch.setitem(sys.modules, 'opening_hours', None)
    result = evaluate('24/7')
    assert result.data.parser is None
    assert result.data.parser_version is None


def test_unverified_backend_version_has_no_execution_provenance(monkeypatch):
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: '999.0')
    assert evaluate('24/7').data.parser_version is None
