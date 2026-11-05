from geo_intelligence_core.comparison import compare
from geo_intelligence_core.models.analysis import Analysis, Metric, MetricConditions
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.requests import RequestContext


def sample(loc, value, **conditions):
    signature = dict(category_mapping_version='mapping-v1', category_selection='cafe', source_coverage='known',
                     reference_period='2025', scope_type='circle', scope_threshold='500m', scope_version='v1',
                     boundary_rule='point_covers', method='source-search-v1', time_condition='static')
    signature.update(conditions)
    return Analysis(request_context=RequestContext(request_id=loc, location_versions={loc: 1}),
        metrics={'sites': Metric(value=value, unit='places', nature='derived', evidence_ids=[f'{loc}-e'])} if value is not None else {},
        metric_conditions={'sites': MetricConditions(**signature)})


def test_strict_comparability_and_nullable_differences():
    a = sample('a', 2)
    b = sample('b', 4)
    result = compare([a, b], ['sites'])
    assert result.status == Status.ok
    assert [r.difference for r in result.data.rows] == [None, 2]
    for key, val in [('category_mapping_version', 'mapping-v2'), ('category_selection', 'shops'),
                     ('source_coverage', 'partial'), ('reference_period', '2024'),
                     ('scope_type', 'polygon'), ('scope_threshold', '1000m'),
                     ('scope_version', 'v2'), ('boundary_rule', 'point_within'),
                     ('method', 'other'), ('time_condition', 'weekend')]:
        mismatch = compare([a, sample('b', 4, **{key: val})], ['sites'])
        assert mismatch.data.rows[1].difference is None
        assert key + '_mismatch' in mismatch.data.rows[1].comparability_issues
    unknown = compare([a, sample('b', 4, reference_period=None)], ['sites'])
    assert unknown.data.rows[1].difference is None
    different_unit = sample('b', 4).model_copy(update={'metrics': {
        'sites': Metric(value=4, unit='people', nature='derived', evidence_ids=['b-e'])}})
    assert 'unit_mismatch' in compare([a, different_unit], ['sites']).data.rows[1].comparability_issues
    different_nature = sample('b', 4).model_copy(update={'metrics': {
        'sites': Metric(value=4, unit='places', nature='estimated', evidence_ids=['b-e'])}})
    assert 'nature_mismatch' in compare([a, different_nature], ['sites']).data.rows[1].comparability_issues


def test_missing_is_null_and_no_rank_or_score():
    result = compare([sample('a', 2), sample('b', None)], ['sites'])
    assert result.status == Status.partial
    assert result.data.rows[1].value is None and result.data.rows[1].difference is None
    assert 'missing_value' in result.data.rows[1].comparability_issues
    assert 'rank' not in result.data.model_dump_json() and 'score' not in result.data.model_dump_json()
    assert compare([sample('a', 2)], ['sites']).status == Status.invalid_input
