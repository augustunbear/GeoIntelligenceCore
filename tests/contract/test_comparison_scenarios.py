import asyncio
from datetime import datetime, timezone
from geo_intelligence_core.analysis import analyze
from geo_intelligence_core.comparison import compare
from geo_intelligence_core.models.analysis import Analysis
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.configuration import AnalyzeRequest, TopicSelection
from geo_intelligence_core.models.evidence import Evidence, Quality, Rights, Permission
from geo_intelligence_core.models.location import Confirmation, Location, Point
from geo_intelligence_core.models.places import Place, PlaceSet, SourceKey
from geo_intelligence_core.models.policy import UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.ports import ProviderRegistry


def loc(id):
    return Location(id=id, version=1, point=Point(longitude=11, latitude=48),
        confirmation=Confirmation(method='manual', at=datetime(2026, 1, 1, tzinfo=timezone.utc), evidence_ids=['synthetic']))


def evidence(period='2025'):
    return Evidence(id='e', source_id='synthetic', source_type='fixture', source_ref='fixture',
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc), reference_period=period,
        method_version='v1', rights=Rights(use=Permission.allowed, permitted_purpose='research'), quality=Quality())


def place(id):
    return Place(source_key=SourceKey(source_id='synthetic', entity_type='site', entity_id=id),
        point=Point(longitude=11, latitude=48), evidence_ids=['e'])


def analysis(id, records, *, period='2025', coverage='known'):
    context = RequestContext(request_id=id, location_versions={id: 1}, effective_conditions={
        'config.category_ids': "('cafe',)", 'config.radius_m': '500', 'region_method': 'geodesic_straight_line_circle',
        'region_version': '1', 'boundary_rule': 'point_covers'})
    result = Result(status='ok', data=PlaceSet(places=records, retrieved_count=len(records),
        unique_count=len(records), coverage=coverage), context=context, evidence=[evidence(period)])
    return Analysis(request_context=context, topic_results={'places': result}, selected_topics=['places'])


def test_union_deduplicates_source_key_across_intersecting_regions():
    compared = compare([analysis('restaurant', [place('1'), place('2')]),
                        analysis('shop', [place('2'), place('3')])], ['places.unique_count'])
    assert compared.status == Status.ok
    assert compared.data.union_counts['places.unique_count'] == 3
    assert compared.data.rows[1].difference == 0
    assert 'best_location' not in compared.data.model_dump_json()
    school = compare([analysis('school-a', [place('1')]), analysis('school-b', [place('2')])], ['places.unique_count'])
    assert school.data.union_counts['places.unique_count'] == 2
    assert len(school.data.rows) == len(compared.data.rows)


def test_population_disabled_does_not_block_selected_places():
    compared = compare([analysis('a', [place('1')]), analysis('b', [place('2')])], ['places.unique_count'])
    assert compared.status == Status.ok and compared.data.rows[1].difference == 0
    missing = compare([analysis('a', [place('1')]), analysis('b', [place('2')], period='2024')], ['places.unique_count'])
    assert missing.data.rows[1].difference is None and missing.data.union_counts['places.unique_count'] is None
    uncovered = compare([analysis('a', [place('1')]), analysis('b', [place('2')], coverage=None)], ['places.unique_count'])
    assert uncovered.data.rows[1].value == 1 and uncovered.data.rows[1].difference is None


class Port:
    calls = 0
    async def search(self, query, context):
        self.calls += 1
        return Result(status='ok', data=PlaceSet(places=[place(str(self.calls))], retrieved_count=1,
            unique_count=1, coverage='known'), context=context, evidence=[evidence()])


class Budget:
    async def reserve(self, *args): return True
    async def record(self, *args): pass


def test_t03_runs_each_location_then_comparison():
    port = Port(); registry = ProviderRegistry(); registry.register('places', port)
    request = AnalyzeRequest(locations=[loc('a'), loc('b')], topics=[TopicSelection(id='places')],
        template_ref='location-comparison@1', explicit_parameters={'radius_m': 500, 'category_ids': ['cafe']})
    policy = UsagePolicy(allowed_capabilities=['places'], max_calls_per_run=2,
        max_area_m2=1_000_000.0, max_geometry_vertices=100)
    result = asyncio.run(analyze(request, registry, policy, Budget()))
    assert port.calls == 2
    assert result.data.comparison.rows[1].value == 1
    assert set(result.data.location_statuses) == {'a@1', 'b@1'}
    assert result.data.comparison.union_counts['places.unique_count'] == 2
    optional = request.model_copy(update={'topics': [TopicSelection(id='places'), TopicSelection(id='population_reference')]})
    with_population_disabled = asyncio.run(analyze(optional, registry, policy, Budget()))
    assert with_population_disabled.status == Status.partial
    assert with_population_disabled.data.comparison.rows[1].difference == 0
    assert all(with_population_disabled.data.topic_results[f'{id}@1/population_reference'].data is None for id in ('a', 'b'))


def test_comparison_snapshot_and_exports_filter_restricted_sources():
    from geo_intelligence_core.evidence import snapshot
    from geo_intelligence_core.export import export_result
    from geo_intelligence_core.models.analysis import Comparison, ComparisonRow
    restricted = evidence().model_copy(update={'id': 'restricted', 'rights': Rights(
        use=Permission.allowed, retain=Permission.allowed, export=Permission.denied,
        permitted_purpose='research')})
    open_source = evidence().model_copy(update={'id': 'open', 'rights': Rights(
        use=Permission.allowed, retain=Permission.allowed, export=Permission.allowed,
        permitted_purpose='research')})
    context = RequestContext(request_id='rights', location_versions={'a': 1, 'b': 1})
    from geo_intelligence_core.models.analysis import Metric, MetricConditions
    raw = Analysis(request_context=context, selected_topics=['places'], topic_results={
        'a@1/places': Result(status='ok', data={'sensitive': 'secret-marker'}, context=context, evidence=[restricted]),
        'b@1/places': Result(status='ok', data={'ordinary': 'public-marker'}, context=context, evidence=[open_source]),
    }, comparison=Comparison(rows=[
        ComparisonRow(location_version='a@1', metric_id='places.unique_count', value=999999,
                      difference=None, unit='places', evidence_ids=['restricted']),
        ComparisonRow(location_version='b@1', metric_id='places.unique_count', value=1,
                      difference=-999998, unit='places', evidence_ids=['open']),
    ], union_counts={'places.unique_count': 1000000}),
        metrics={'private': Metric(value=999999, unit='places', nature='derived', evidence_ids=['restricted'])},
        metric_conditions={'private': MetricConditions(reference_period='2025')})
    retained = snapshot(raw, 'research')
    assert retained.data.analysis.comparison.rows[0].value == 999999
    for format in ('json', 'csv', 'geojson'):
        exported = export_result(retained.data, format, 'en', 'research')
        assert exported.status == Status.partial
        assert 'secret-marker' not in exported.data
        assert '999999' not in exported.data and '1000000' not in exported.data
        assert 'public-marker' in exported.data if format != 'geojson' else True
    unknown = restricted.model_copy(update={'rights': Rights(retain=Permission.unknown,
        export=Permission.unknown, permitted_purpose='research')})
    hidden = raw.model_copy(update={'topic_results': {**raw.topic_results,
        'a@1/places': Result(status='ok', data={'sensitive': 'secret-marker'}, context=context, evidence=[unknown])}})
    retained_hidden = snapshot(hidden, 'research')
    assert retained_hidden.data.analysis.comparison.rows[0].value is None
    assert retained_hidden.data.analysis.comparison.union_counts['places.unique_count'] is None
    assert 'secret-marker' not in retained_hidden.data.model_dump_json()
    # Reused evidence IDs in a different topic cannot authorize a comparison cell.
    duplicate = raw.model_copy(update={'topic_results': {**raw.topic_results,
        'elsewhere': Result(status='ok', data={'other': 'hidden'}, context=context,
                            evidence=[restricted.model_copy(update={'id': 'open'})])}})
    duplicate_snapshot = snapshot(duplicate, 'research')
    duplicate_export = export_result(duplicate_snapshot.data, 'json', 'en', 'research')
    assert duplicate_export.data is not None
    import json
    assert json.loads(duplicate_export.data)['analysis']['comparison']['rows'][1]['value'] is None


def test_union_without_two_authorized_rows_is_redacted():
    import json
    from geo_intelligence_core.evidence import snapshot
    from geo_intelligence_core.export import export_result
    from geo_intelligence_core.models.analysis import Comparison, ComparisonRow
    context = RequestContext(request_id='orphan-union')
    for rows in ([], [ComparisonRow(location_version='a@1', metric_id='places.unique_count',
                                      value=1, difference=None, unit='places', evidence_ids=[]) ]):
        source = Analysis(request_context=context,
            comparison=Comparison(rows=rows, union_counts={'places.unique_count': 1234567}))
        retained = snapshot(source, 'research')
        assert retained.status == Status.partial
        assert retained.data.analysis.comparison.union_counts['places.unique_count'] is None
        output = export_result(retained.data, 'json', 'en', 'research')
        assert json.loads(output.data)['analysis']['comparison']['union_counts']['places.unique_count'] is None
        assert '1234567' not in output.data
