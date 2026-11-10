"""Synthetic-only observation contracts: no attendance inference or provider I/O."""
from datetime import datetime, timezone
import json
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from geo_intelligence_core import Observation, normalize_observation
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.evidence import Rights
from geo_intelligence_core.models.evidence import Evidence
from geo_intelligence_core.models.spatial import Region
from geo_intelligence_core.models.location import Point


def payload(source_evidence, **updates):
    value = dict(id='synthetic-observation', point={'longitude': 11, 'latitude': 49},
                 start='2026-10-25T02:30:00+02:00', end='2026-10-25T02:30:00+01:00',
                 timezone='Europe/Berlin', direction='northbound', count_object='visit',
                 count=0, method='synthetic-manual-v1', dedupe='unknown', evidence=[source_evidence])
    value.update(updates)
    return value


def test_zero_and_dst_instants_are_preserved_without_inference(synthetic_evidence):
    original = Observation(**payload(synthetic_evidence))
    result = normalize_observation(original)
    assert result.status == Status.ok
    assert result.data.count == 0
    assert result.data.count_object == 'visit'
    assert result.data.dedupe == 'unknown'
    assert result.data.direction == 'northbound'
    assert result.data.start == datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)
    assert result.data.end == datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)
    assert result.data.timezone == 'Europe/Berlin'
    assert result.data == original
    assert result.evidence == original.evidence
    assert result.data.evidence[0].rights == Rights()
    assert not result.data.evidence[0].rights.allows('export', 'research')
    assert result.context.method_version == 'observation-normalization-v1'


@pytest.mark.parametrize('omit_count', [False, True])
def test_missing_count_is_unknown_never_zero(synthetic_evidence, omit_count):
    values = payload(synthetic_evidence, count=None, missing_reason='sensor_not_running')
    if omit_count:
        del values['count']
    result = normalize_observation(values)
    assert result.status == Status.unknown
    assert result.data.count is None
    assert result.data.missing_reason == 'sensor_not_running'
    assert [issue.code for issue in result.issues] == ['observation_count_missing']
    assert result.evidence == (synthetic_evidence,)


@pytest.mark.parametrize('updates', [
    {'count': -1}, {'count': True}, {'count': '0'}, {'count': 1.5},
    {'count': None}, {'missing_reason': 'absent'}, {'count': None, 'missing_reason': '  '},
    {'start': '2026-10-25T02:30:00'}, {'end': '2026-10-25T03:30:00'},
    {'start': '2026-10-25T03:30:00+01:00'}, {'end': '2026-10-25T02:30:00+02:00'},
    {'start': 1792888200}, {'end': True}, {'timezone': 'Invalid/Zone'}, {'timezone': ''}, {'count_object': 'population'},
    {'point': None}, {'evidence': []}, {'method': ' '}, {'dedupe': ''},
    {'direction': ' '}, {'unknown': 1},
])
def test_invalid_input_is_explicit_and_sanitized(synthetic_evidence, updates):
    values = payload(synthetic_evidence, **updates)
    with pytest.raises(ValidationError):
        Observation(**values)
    result = normalize_observation(values)
    assert result.status == Status.invalid_input
    assert result.data is None
    assert result.evidence == ()
    assert [issue.code for issue in result.issues] == ['invalid_observation']
    assert result.issues[0].safe_params == {}


def test_exactly_one_point_or_region_and_unique_evidence(synthetic_evidence):
    region = Region(id='synthetic-area', version='1', method='synthetic',
                    geometry={'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [0, 1], [0, 0]]]})
    result = normalize_observation(payload(synthetic_evidence, point=None, region=region))
    assert result.status == Status.ok
    assert result.data.region == region
    assert normalize_observation(payload(synthetic_evidence, region=region)).status == Status.invalid_input
    assert normalize_observation(payload(synthetic_evidence, evidence=[synthetic_evidence] * 2)).status == Status.invalid_input


def test_spring_dst_interval_uses_elapsed_seconds(synthetic_evidence):
    result = normalize_observation(payload(synthetic_evidence, start='2026-03-29T01:30:00+01:00',
                                           end='2026-03-29T03:30:00+02:00'))
    assert result.status == Status.ok
    assert (result.data.end - result.data.start).total_seconds() == 3600


def test_aware_zoneinfo_fold_instants_stay_distinct(synthetic_evidence):
    zone = ZoneInfo('Europe/Berlin')
    result = normalize_observation(payload(synthetic_evidence,
        start=datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0),
        end=datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)))
    assert result.status == Status.ok
    assert (result.data.end - result.data.start).total_seconds() == 3600


@pytest.mark.parametrize('count_object', ['person', 'visit'])
def test_counting_objects_and_durations_are_not_converted(synthetic_evidence, count_object):
    short = normalize_observation(payload(synthetic_evidence, count=12, count_object=count_object))
    long = normalize_observation(payload(synthetic_evidence, count=12, count_object=count_object,
                                         end='2026-10-25T03:30:00+01:00'))
    assert short.data.count == long.data.count == 12
    assert short.data.count_object == long.data.count_object == count_object
    assert long.data.end - long.data.start == 2 * (short.data.end - short.data.start)
    assert 'rate' not in long.data.model_dump()
    assert 'comparable' not in long.data.model_dump()


def test_immutable_roundtrip_and_schema(synthetic_evidence):
    observation = Observation(**payload(synthetic_evidence))
    with pytest.raises(ValidationError):
        observation.count = 99
    with pytest.raises(ValidationError):
        observation.model_copy(update={'count': True})
    assert Observation.model_validate_json(observation.model_dump_json()) == observation
    result = normalize_observation(observation)
    assert Result[Observation].model_validate_json(result.model_dump_json()) == result
    schema = json.loads((Path(__file__).parents[2] / 'schemas/v1/observation.json').read_text())
    assert schema == Observation.model_json_schema()


@pytest.mark.parametrize('start,end', [('1792888200', '1792891800'),
                                      ('1792888200000', '1792891800000')])
def test_numeric_text_is_not_an_offset_aware_instant(synthetic_evidence, start, end):
    result = normalize_observation(payload(synthetic_evidence, start=start, end=end))
    assert result.status == Status.invalid_input
    assert result.data is None


def test_full_provenance_and_restricted_rights_are_not_rewritten(synthetic_evidence):
    rights = Rights(use='denied', retain='unknown', cache='denied', display='allowed',
                    export='denied', redistribute='denied', permitted_purpose='synthetic-review',
                    attribution='Synthetic source', license_url='https://example.invalid/license',
                    source_url='https://example.invalid/source', checked_at='2026-11-01T10:00:00+01:00')
    evidence = synthetic_evidence.model_copy(update={
        'rights': rights, 'reference_period': 'synthetic-autumn',
        'valid_period': 'synthetic-hour', 'source_type': 'synthetic-counter',
        'method_version': 'counter-protocol-v3',
    })
    observation = Observation(**payload(evidence, count=9, count_object='person', dedupe='within-interval'))
    result = normalize_observation(observation)
    assert result.status == Status.ok  # Validation is not authorization to use or export.
    assert result.evidence == (evidence,)
    assert result.data.evidence == (evidence,)
    assert result.data.method == observation.method
    assert result.data.dedupe == 'within-interval'
    assert result.data.count_object == 'person'
    assert result.data.evidence[0].rights == rights
    assert not result.data.evidence[0].rights.allows('use', 'synthetic-review')
    assert not result.data.evidence[0].rights.allows('export', 'synthetic-review')


def test_unvalidated_model_instance_is_revalidated(synthetic_evidence):
    unvalidated = Observation.model_construct(**payload(synthetic_evidence, count=-1))
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        result = normalize_observation(unvalidated)
    assert not captured
    assert result.status == Status.invalid_input
    assert result.data is None


def test_nested_unvalidated_point_instance_is_revalidated(synthetic_evidence):
    point = Point.model_construct(longitude=999, latitude=49)
    with pytest.raises(ValidationError):
        Observation(**payload(synthetic_evidence, point=point))
    result = normalize_observation(payload(synthetic_evidence, point=point))
    assert result.status == Status.invalid_input
    assert result.data is None


def test_nested_unvalidated_evidence_rights_are_revalidated(synthetic_evidence):
    bad_rights = Rights.model_construct(use='granted')
    bad_evidence = Evidence.model_construct(**{
        **synthetic_evidence.model_dump(), 'rights': bad_rights,
    })
    with pytest.raises(ValidationError):
        Observation(**payload(bad_evidence))
    assert normalize_observation(payload(bad_evidence)).status == Status.invalid_input


@pytest.mark.parametrize('field,value', [
    ('start', '0001-01-01T00:00:00+01:00'),
    ('end', '9999-12-31T23:59:59-01:00'),
])
def test_out_of_range_utc_conversion_is_invalid_input(synthetic_evidence, field, value):
    values = payload(synthetic_evidence, **{field: value})
    with pytest.raises(ValidationError):
        Observation(**values)
    result = normalize_observation(values)
    assert result.status == Status.invalid_input
    assert result.data is None


def test_out_of_range_nested_evidence_date_is_invalid_input(synthetic_evidence):
    evidence = synthetic_evidence.model_dump()
    evidence['retrieved_at'] = '0001-01-01T00:00:00+01:00'
    result = normalize_observation(payload(synthetic_evidence, evidence=[evidence]))
    assert result.status == Status.invalid_input
    assert result.data is None
