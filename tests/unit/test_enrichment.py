"""Synthetic offline COMPANY import; no real source or rights acceptance."""
from copy import deepcopy

import pytest

from geo_intelligence_core.models.common import Status


def importer():
    # Missing operation is an assertion failure during the initial RED run.
    import importlib.util
    try:
        spec = importlib.util.find_spec('geo_intelligence_core.inputs.company')
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, 'offline company import operation is missing'
    from geo_intelligence_core.inputs.company import import_company
    return import_company


def evidence(synthetic_evidence, **rights):
    return synthetic_evidence.model_copy(update={
        'rights': synthetic_evidence.rights.model_copy(update={
            'use': 'allowed', 'permitted_purpose': 'site-study', **rights})})


def record(id='site-1', **updates):
    return dict(id=id, source_id='user', source_ref='synthetic fixture',
                site_role='branch', point={'longitude': 11, 'latitude': 49}, **updates)


def call(records, ev, purpose='site-study'):
    return importer()(records, ev, purpose=purpose)


def test_missing_branch_workforce_stays_null_and_hq_count_is_not_allocated(synthetic_evidence):
    hq = record('hq', workforce={'scope': 'legal_entity', 'count': 500}, legal_entity_ref='entity-1')
    hq['site_role'] = 'headquarters'
    branch = record(legal_entity_ref='entity-1')
    result = call([hq, branch], evidence(synthetic_evidence))
    assert result.status == Status.ok
    assert result.data[0].workforce.count == 500
    assert result.data[0].workforce.scope == 'legal_entity'
    assert result.data[1].workforce is None
    assert result.evidence[0] == evidence(synthetic_evidence)
    assert result.data[1].evidence_ids == (synthetic_evidence.id,)
    assert result.context.effective_conditions['purpose'] == 'site-study'


def test_registered_address_and_range_are_preserved_without_inference(synthetic_evidence):
    row = record(workforce={'scope': 'site', 'lower': 10, 'upper': 20})
    row.update(site_role='registered_address', point=None, address={'locality': 'Synthetic Town'})
    result = call([row], evidence(synthetic_evidence))
    assert result.status == Status.ok
    site = result.data[0]
    assert site.site_role == 'registered_address'
    assert site.point is None
    assert site.workforce.count is None
    assert (site.workforce.lower, site.workforce.upper) == (10, 20)


@pytest.mark.parametrize('rights,purpose', [({}, 'wrong'), ({'use': 'unknown'}, 'site-study'),
    ({'use': 'denied'}, 'site-study'), ({}, ''), ({}, ' ')])
def test_use_and_exact_nonblank_purpose_required(synthetic_evidence, rights, purpose):
    result = call([record()], evidence(synthetic_evidence, **rights), purpose)
    assert result.status == Status.disabled
    assert result.data is None


@pytest.mark.parametrize('update', [
    {'site_role': 'shop'}, {'site_role': None}, {'source_id': 'other'},
    {'source_ref': 'other'}, {'id': ' '}, {'point': {'latitude': 91, 'longitude': 11}},
    {'point': None}, {'workforce': {'scope': 'site', 'count': True}},
    {'workforce': {'scope': 'site', 'count': -1}},
    {'workforce': {'scope': 'site', 'count': 1.5}},
    {'workforce': {'scope': 'site', 'count': '10-20'}},
    {'workforce': {'scope': 'site', 'lower': 20, 'upper': 10}},
    {'workforce': {'scope': 'site', 'lower': 10}},
    {'workforce': {'scope': 'site', 'count': 15, 'lower': 10, 'upper': 20}},
    {'workforce': {'count': 500}}, {'workforce': {'scope': 'site'}},
    {'workforce': {'scope': 'legal_entity', 'count': 500}},
    {'evidence_ids': ['unrelated']}, {'unknown_field': 'not ignored'},
])
def test_invalid_record_rejects_whole_batch(synthetic_evidence, update):
    bad = record('bad')
    bad.update(update)
    result = call([record(), bad], evidence(synthetic_evidence))
    assert result.status == Status.invalid_input
    assert result.data is None


@pytest.mark.parametrize('records', [None, {}, (), ['https://example.invalid/data'],
    [record(), record()], [record(str(i)) for i in range(1001)]])
def test_invalid_or_unbounded_batch(synthetic_evidence, records):
    assert call(records, evidence(synthetic_evidence)).status == Status.invalid_input


def test_empty_authorized_batch_is_no_results(synthetic_evidence):
    result = call([], evidence(synthetic_evidence))
    assert result.status == Status.no_results
    assert result.data == ()


@pytest.mark.parametrize('industry', ['food-service', 'retail', 'education'])
def test_industry_neutral_source_assertions_and_zero(synthetic_evidence, industry):
    row = record(industry=industry, workforce={'scope': 'site', 'count': 0})
    original = deepcopy(row)
    ev = evidence(synthetic_evidence, export='denied', retain='unknown')
    result = call([row], ev)
    assert result.status == Status.ok
    assert result.data[0].industry == industry
    assert result.data[0].workforce.count == 0
    assert result.evidence[0].rights.export == 'denied'
    assert result.evidence[0].rights.retain == 'unknown'
    assert row == original
    with pytest.raises(ValueError):
        result.data[0].site_role = 'operating_site'


def test_nested_constructed_models_are_revalidated(synthetic_evidence):
    from geo_intelligence_core.models.location import Point
    row = record()
    row['point'] = Point.model_construct(latitude=100, longitude=11)
    assert call([row], evidence(synthetic_evidence)).status == Status.invalid_input


def test_nested_evidence_rights_cannot_bypass_validation(synthetic_evidence):
    from geo_intelligence_core.models.evidence import Rights
    ev = synthetic_evidence.model_construct(**{
        **evidence(synthetic_evidence).__dict__,
        'rights': Rights.model_construct(use='allowed', permitted_purpose='site-study', export='invented')})
    assert call([record()], ev).status == Status.invalid_input


@pytest.mark.parametrize('update', [{'address': {}}, {'address': {'locality': ' '}},
    {'address': {'native_names': {'en': 'Name only'}}}])
def test_blank_or_name_only_address_does_not_supply_a_location(synthetic_evidence, update):
    row = record()
    row.update(point=None, **update)
    assert call([row], evidence(synthetic_evidence)).status == Status.invalid_input


@pytest.mark.parametrize('field', ['point', 'workforce'])
def test_incomplete_constructed_nested_models_return_invalid_input(synthetic_evidence, field):
    from geo_intelligence_core.models.location import Point
    from geo_intelligence_core.models.company import WorkforceFact
    row = record()
    row[field] = (Point if field == 'point' else WorkforceFact).model_construct()
    result = call([record('valid'), row], evidence(synthetic_evidence))
    assert result.status == Status.invalid_input
    assert result.data is None
