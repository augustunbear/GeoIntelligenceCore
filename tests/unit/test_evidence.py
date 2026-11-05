"""Scoped corrections and purpose-aware, immutable snapshots."""
from datetime import datetime, timezone

from geo_intelligence_core.models.analysis import Analysis, Correction, Metric
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.evidence import Evidence, Permission, Quality, Rights
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.evidence import apply_correction, snapshot

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def evidence(id='e1', *, retain=Permission.allowed, export=Permission.allowed):
    return Evidence(id=id, source_id='synthetic', source_type='test', source_ref='fixture',
                    retrieved_at=NOW, method_version='v1', quality=Quality(),
                    rights=Rights(use=Permission.allowed, retain=retain,
                                  display=Permission.allowed, export=export,
                                  permitted_purpose='planning'))


def analysis(value=4, *, items=None, ev=None):
    context = RequestContext(request_id='run-1', scope_token='case-A', template_ref='template-v1')
    ev = ev or evidence()
    data = items if items is not None else {'count': Metric(value=value, unit='items', nature='measured', evidence_ids=(ev.id,))}
    topic = Result(status=Status.ok, data=data, evidence=(ev,), context=context)
    return Analysis(request_context=context, selected_topics=('places',), topic_results={'places': topic})


def correction(action, replacement=None, scope='case-A'):
    return Correction(target_ref='places/count', action=action, replacement=replacement,
                      evidence_ids=('e1',), reason='manual verification', scope_token=scope,
                      at=NOW.isoformat())


def test_correction():
    original = analysis()
    replacement = {'value': 7, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']}
    changed = apply_correction(original, correction('correct', replacement), 'case-A')
    assert changed.status == Status.ok
    assert changed.data.topic_results['places'].data['count'].value == 7
    assert original.topic_results['places'].data['count'].value == 4
    assert changed.data.corrections[0].target_ref == 'places/count'
    assert changed.data.originals['places/count']['value'] == 4
    assert apply_correction(original, correction('correct'), 'case-A').status == Status.invalid_input
    assert apply_correction(original, correction('confirm', replacement), 'case-A').status == Status.invalid_input
    assert apply_correction(original, correction('exclude', replacement), 'case-A').status == Status.invalid_input
    assert apply_correction(original, correction('correct', {**replacement, 'source_id': 'forged'}), 'case-A').status == Status.invalid_input
    assert apply_correction(original, correction('correct', replacement, scope='case-B'), 'case-A').status == Status.invalid_input
    assert original.topic_results['places'].data['count'].value == 4


def test_conflict():
    a, b = evidence('a'), evidence('b')
    source = analysis(items={'a': Metric(value=4, unit='items', nature='measured', evidence_ids=('a',)),
                             'b': Metric(value=9, unit='items', nature='measured', evidence_ids=('b',))})
    source = source.model_copy(update={'topic_results': {'places': Result(status=Status.conflict,
               data=source.topic_results['places'].data, evidence=(a, b), context=source.request_context)}})
    retained = snapshot(source, 'planning')
    assert retained.status == Status.ok
    assert retained.data.analysis.topic_results['places'].data['a']['value'] == 4
    assert retained.data.analysis.topic_results['places'].data['b']['value'] == 9


def test_snapshot():
    original = analysis()
    first = snapshot(original, 'planning')
    second = snapshot(original, 'planning')
    assert first.status == second.status == Status.ok
    assert first.data.canonical_hash == second.data.canonical_hash
    upgraded = original.model_copy(update={'request_context': original.request_context.model_copy(update={'template_ref': 'template-v2'})})
    assert first.data.analysis.request_context.template_ref == 'template-v1'
    assert first.data.canonical_hash != snapshot(upgraded, 'planning').data.canonical_hash


def test_snapshot_does_not_retain_unknown_or_denied_source():
    denied = analysis(items={'secret': Metric(value=42, unit='items', nature='measured', evidence_ids=('e1',))},
                      ev=evidence(retain=Permission.unknown))
    snap = snapshot(denied, 'planning')
    assert snap.status == Status.partial
    assert '42' not in snap.data.analysis.model_dump_json()
    assert snap.data.redactions
    assert not snap.data.retained_evidence_ids


def test_correction_rejects_unproven_replacement_and_invalid_attachment():
    original = analysis()
    replacement = {'value': 8, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['unverified']}
    assert apply_correction(original, correction('correct', replacement), 'case-A').status == Status.invalid_input
    invalid = Correction(target_ref='places/count', action='attach', attachments=({'id': 'claim'},),
                         reason='source', scope_token='case-A', at=NOW.isoformat())
    assert apply_correction(original, invalid, 'case-A').status == Status.invalid_input


def test_exclusion_preserves_original_history():
    original = analysis()
    excluded = apply_correction(original, correction('exclude'), 'case-A').data
    assert 'count' not in excluded.topic_results['places'].data
    assert excluded.originals['places/count']['value'] == 4
    assert original.topic_results['places'].data['count'].value == 4


def test_snapshot_removes_foreign_scope_correction_and_original():
    source = analysis()
    foreign = correction('correct', {'value': 999001, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']}, scope='case-B')
    forged = source.model_copy(update={'corrections': (foreign,),
                                       'originals': {'places/count': {'value': 999002, 'evidence_ids': ['e1']}}})
    snap = snapshot(forged, 'planning')
    assert snap.status == Status.partial
    assert '999001' not in snap.data.analysis.model_dump_json()
    assert '999002' not in snap.data.analysis.model_dump_json()
    assert 'case-B' not in snap.data.model_dump_json()


def test_place_correction_preserves_source_identity():
    from geo_intelligence_core.models.location import Point
    from geo_intelligence_core.models.places import Place, SourceKey
    place = Place(source_key=SourceKey(source_id='synthetic', entity_type='node', entity_id='1'),
                  native_names={'de': 'Alt'}, point=Point(longitude=11, latitude=49), evidence_ids=('e1',))
    original = analysis(items={'site': place})
    valid = place.model_dump(mode='json')
    valid['native_names'] = {'de': 'Neu'}
    fix = Correction(target_ref='places/site', action='correct', replacement=valid,
                     evidence_ids=('e1',), reason='name verified', scope_token='case-A', at=NOW.isoformat())
    assert apply_correction(original, fix, 'case-A').status == Status.ok
    changed = dict(valid)
    changed['source_key'] = {**valid['source_key'], 'entity_id': '2'}
    assert apply_correction(original, fix.model_copy(update={'replacement': changed}), 'case-A').status == Status.invalid_input


def test_correction_on_p09_placeset_preserves_counts_and_identity():
    import asyncio
    from geo_intelligence_core.analysis import analyze
    from geo_intelligence_core.models.configuration import AnalyzeRequest, TopicSelection
    from geo_intelligence_core.models.location import Confirmation, Location, Point
    from geo_intelligence_core.models.places import Place, PlaceSet, SourceKey
    from geo_intelligence_core.models.policy import UsagePolicy
    from geo_intelligence_core.models.spatial import Region
    from geo_intelligence_core.ports import ProviderRegistry
    place = Place(source_key=SourceKey(source_id='synthetic', entity_type='node', entity_id='1'),
                  native_names={'de': 'Alt'}, point=Point(longitude=11, latitude=49), evidence_ids=('e1',))
    ev = evidence()
    class Provider:
        async def search(self, query, context):
            return Result(status=Status.ok, data=PlaceSet(places=(place,), retrieved_count=1, unique_count=1),
                          evidence=(ev,), context=context)
    class Budget:
        async def reserve(self, *args): return True
        async def record(self, *args): pass
    location = Location(id='loc', version=1, point=Point(longitude=11, latitude=49),
                        confirmation=Confirmation(method='manual', at=NOW, evidence_ids=('e1',)))
    region = Region(id='r', version='1', method='fixture', geometry={'type': 'Polygon',
              'coordinates': [[[10,48], [12,48], [12,50], [10,50], [10,48]]]})
    request = AnalyzeRequest(locations=(location,), regions=(region,), topics=(TopicSelection(id='places'),),
                             explicit_parameters={'category_ids': ['restaurant']}, scope_token='case-A')
    registry = ProviderRegistry(); registry.register('places', Provider())
    original = asyncio.run(analyze(request, registry, UsagePolicy(allowed_capabilities=('places',),
                               max_calls_per_run=1), Budget())).data
    assert isinstance(original.topic_results['places'].data, PlaceSet)
    replacement = place.model_dump(mode='json'); replacement['native_names'] = {'de': 'Neu'}
    fix = Correction(target_ref='places/synthetic:node:1', action='correct', replacement=replacement,
                     evidence_ids=('e1',), reason='verified', scope_token='case-A', at=NOW.isoformat())
    changed = apply_correction(original, fix, 'case-A')
    assert changed.status == Status.ok
    assert changed.data.topic_results['places'].data.places[0].native_names['de'] == 'Neu'
    assert changed.data.topic_results['places'].data.retrieved_count == 1
    assert changed.data.topic_results['places'].data.unique_count == 1
    assert original.topic_results['places'].data.places[0].native_names['de'] == 'Alt'
    excluded = apply_correction(original, fix.model_copy(update={'action': 'exclude', 'replacement': None}), 'case-A')
    assert excluded.status == Status.ok
    assert excluded.data.topic_results['places'].data.unique_count == 0
    assert excluded.data.topic_results['places'].data.retrieved_count == 1
    assert excluded.data.originals['places/synthetic:node:1']['native_names']['de'] == 'Alt'


def test_snapshot_filters_nested_restricted_correction_payload():
    allowed = evidence('e1')
    denied = evidence('closed', retain=Permission.denied)
    source = analysis(ev=allowed)
    topic = source.topic_results['places'].model_copy(update={'evidence': (allowed, denied)})
    forged = Correction(target_ref='places/count', action='correct',
                        replacement={'public': {'text': 'ordinary', 'evidence_ids': ['e1']},
                                     'private': {'text': 'SENSITIVE-LEAK', 'evidence_ids': ['closed']}},
                        evidence_ids=('e1',), reason='verified', scope_token='case-A', at=NOW.isoformat())
    source = source.model_copy(update={'topic_results': {'places': topic}, 'corrections': (forged,)})
    snap = snapshot(source, 'planning')
    assert snap.status == Status.partial
    assert 'SENSITIVE-LEAK' not in snap.data.model_dump_json()


def test_correction_rejects_unknown_correction_evidence():
    source = analysis()
    bad = correction('correct', {'value': 99, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']})
    bad = bad.model_copy(update={'evidence_ids': ('nonexistent',)})
    assert apply_correction(source, bad, 'case-A').status == Status.invalid_input
    assert source.topic_results['places'].data['count'].value == 4


def test_snapshot_correction_authorizes_evidence_within_target_topic():
    open_source = evidence('e1')
    denied_source = evidence('e1', retain=Permission.denied)
    source = analysis(ev=denied_source)
    context = source.request_context
    other = Result(status=Status.ok, data={'count': Metric(value=2, unit='items', nature='measured', evidence_ids=('e1',))},
                   evidence=(open_source,), context=context)
    forged = correction('correct', {'value': 909090, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']})
    source = source.model_copy(update={'topic_results': {'places': source.topic_results['places'], 'other': other},
                                       'corrections': (forged,)})
    snap = snapshot(source, 'planning')
    assert snap.status == Status.partial
    assert '909090' not in snap.data.model_dump_json()


def test_snapshot_drops_topic_from_foreign_scope():
    source = analysis()
    foreign_context = source.request_context.model_copy(update={'scope_token': 'case-B'})
    foreign = Result(status=Status.ok, data={'count': Metric(value=444444, unit='items', nature='measured', evidence_ids=('e1',))},
                     evidence=(evidence(),), context=foreign_context)
    source = source.model_copy(update={'topic_results': {**source.topic_results, 'foreign': foreign}})
    snap = snapshot(source, 'planning')
    assert snap.status == Status.partial
    assert '444444' not in snap.data.model_dump_json()
    assert 'case-B' not in snap.data.model_dump_json()


def test_snapshot_duplicate_evidence_id_in_same_topic_fails_closed():
    allowed = evidence('e1')
    denied = evidence('e1', retain=Permission.denied)
    source = analysis(ev=allowed)
    topic = source.topic_results['places'].model_copy(update={'evidence': (denied, allowed)})
    snap = snapshot(source.model_copy(update={'topic_results': {'places': topic}}), 'planning')
    assert snap.status == Status.partial
    assert '"value":4' not in snap.data.analysis.model_dump_json()
    assert not snap.data.analysis.topic_results['places'].evidence
