"""Synthetic offline history contracts; not real E02 source acceptance."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from geo_intelligence_core.analysis import analyze
from geo_intelligence_core.evidence import snapshot
from geo_intelligence_core.models.analysis import Analysis
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.configuration import AnalyzeRequest, TopicSelection
from geo_intelligence_core.models.evidence import Evidence, Permission, Quality, Rights
from geo_intelligence_core.models.location import Confirmation, Location, Point
from geo_intelligence_core.models.places import Place, PlaceSet, SourceKey
from geo_intelligence_core.models.policy import UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.spatial import Region
from geo_intelligence_core.ports import ProviderRegistry
from geo_intelligence_core.providers.budget import InMemoryBudget


def evidence(id='e1', **updates):
    return Evidence(id=id, source_id='synthetic', source_type='fixture', source_ref='synthetic-query',
        retrieved_at=datetime(2026, 11, 10, tzinfo=timezone.utc), method_version='v1',
        rights=Rights(use=Permission.allowed, retain=Permission.allowed, permitted_purpose='planning'),
        quality=Quality()).model_copy(update=updates)


def place(id, **updates):
    return Place(source_key=SourceKey(source_id='synthetic', entity_type='site', entity_id=id),
        point=Point(longitude=11, latitude=49), evidence_ids=('e1',)).model_copy(update=updates)


def analysis(records=(), *, context=None, ev=None, status=Status.ok, coverage='complete:synthetic-area-v1'):
    context = context or RequestContext(request_id='run', location_versions={'site': 1},
        method_version='analysis-v1', effective_conditions={'query': 'synthetic-500m'})
    return Analysis(request_context=context, selected_topics=('places',), topic_results={
        'places': Result(status=status, data=PlaceSet(places=records, retrieved_count=len(records),
            unique_count=len(records), coverage=coverage), evidence=(ev or evidence(),), context=context)})


def snap(records=(), **kwargs):
    return snapshot(analysis(records, **kwargs), 'planning').data


def compare(before, after):
    from geo_intelligence_core.history import compare_snapshots
    return compare_snapshots(before, after)


def test_same_query_missing_record_is_not_real_world_closure():
    before, after = snap((place('1'), place('2'))), snap((place('1'),))
    result = compare(before, after)
    assert result.status == Status.ok
    assert len(result.data) == 1
    change = result.data[0]
    assert (change.kind, change.change, change.entity_ref) == (
        'source_record', 'source_record_missing', 'places/synthetic:site:2')
    assert change.before.source_key.entity_id == '2' and change.after is None
    assert change.evidence_ids == ('e1',) and change.verification == 'unverified'
    assert 'closed' not in result.model_dump_json()
    assert len(before.analysis.topic_results['places'].data['places']) == 2


def test_history_preserves_facts_for_same_instance_and_flags_a_serving_method_switch():
    class Provider:
        def __init__(self, instance, method, record):
            self.instance, self.method, self.record = instance, method, record

        async def search(self, query, context):
            enriched = context.model_copy(update={'effective_conditions': {
                **context.effective_conditions, 'provider_instance': self.instance,
                'provider_endpoint': 'https://example.org/api', 'provider_http_method': self.method,
            }})
            places = PlaceSet(places=(self.record,), retrieved_count=1, unique_count=1,
                              coverage='complete:synthetic-area-v1')
            return Result(status=Status.ok, data=places, evidence=(evidence(),), context=enriched)

    request = AnalyzeRequest(
        locations=(Location(id='site', version=1, point=Point(longitude=11, latitude=49),
                            confirmation=Confirmation(method='manual', at=evidence().retrieved_at,
                                                      evidence_ids=('e1',))),),
        regions=(Region(id='site-area', version='1', method='fixture', geometry={
            'type': 'Polygon', 'coordinates': [[[10, 48], [12, 48], [12, 50], [10, 50], [10, 48]]],
        }),),
        topics=(TopicSelection(id='places'),), explicit_parameters={'category_ids': ['restaurant']},
        scope_token='synthetic-case',
    )

    def run(instance, method, record):
        registry = ProviderRegistry()
        registry.register('places', Provider(instance, method, record))
        policy = UsagePolicy(allowed_capabilities=('places',), max_calls_per_run=1)
        analyzed = asyncio.run(analyze(request, registry, policy, InMemoryBudget(1, Decimal(0))))
        assert analyzed.status == Status.ok
        return snapshot(analyzed.data, 'planning').data

    before = run('synthetic-a', 'GET', place('1'))
    same = run('synthetic-a', 'GET', place('2'))
    changed = compare(before, same)
    assert changed.status == Status.ok
    assert {item.change for item in changed.data} == {'source_record_missing', 'source_record_added'}

    for switched in (run('synthetic-b', 'GET', place('2')), run('synthetic-a', 'POST', place('2'))):
        changed = compare(before, switched)
        assert changed.status == Status.ok
        assert [item.change for item in changed.data] == ['conditions_changed']


def retained_with_provenance(record, caller_value, instances):
    context = analysis().request_context.model_copy(update={
        'effective_conditions': {'topic/places/provider_instance': caller_value},
    })
    source = analysis((record,), context=context)
    topic = source.topic_results['places']
    topics = {}
    for name, instance in instances.items():
        conditions = dict(context.effective_conditions)
        if instance is not None:
            conditions['provider_instance'] = instance
        topics[name] = topic.model_copy(update={
            'context': context.model_copy(update={'effective_conditions': conditions}),
        })
    result = snapshot(source.model_copy(update={
        'selected_topics': tuple(topics), 'topic_results': topics,
    }), 'planning')
    assert result.status == Status.ok
    return result.data


def test_history_detects_caller_condition_change_with_same_named_topic_provenance():
    old = retained_with_provenance(place('1'), 'caller-before', {'places': 'instance-a'})
    new = retained_with_provenance(place('2'), 'caller-after', {'places': 'instance-a'})

    result = compare(old, new)
    assert result.status == Status.ok
    assert [entry.change for entry in result.data] == ['conditions_changed']
    change, = result.data
    assert change.before.effective_conditions == {'topic/places/provider_instance': 'caller-before'}
    assert change.after.effective_conditions == {'topic/places/provider_instance': 'caller-after'}
    assert change.before.topic_provenance == change.after.topic_provenance == {
        'places': {'provider_instance': 'instance-a'},
    }


@pytest.mark.parametrize('transport_instance', ('instance-b', 'instance-c', None))
def test_history_compares_same_provenance_field_for_each_topic(transport_instance):
    before = retained_with_provenance(
        place('1'), 'caller', {'places': 'instance-a', 'transport_places': 'instance-b'},
    )
    after = retained_with_provenance(
        place('2'), 'caller', {'transport_places': transport_instance, 'places': 'instance-a'},
    )

    result = compare(before, after)
    assert result.status == Status.ok
    if transport_instance == 'instance-b':
        assert [entry.change for entry in result.data] == [
            'source_record_missing', 'source_record_added',
            'source_record_missing', 'source_record_added',
        ]
    else:
        change, = result.data
        assert change.change == 'conditions_changed'
        assert change.before.topic_provenance == {
            'places': {'provider_instance': 'instance-a'},
            'transport_places': {'provider_instance': 'instance-b'},
        }
        expected = {'places': {'provider_instance': 'instance-a'}}
        if transport_instance is not None:
            expected['transport_places'] = {'provider_instance': transport_instance}
        assert change.after.topic_provenance == expected


def test_history_compares_legacy_snapshots_and_distinguishes_missing_provenance():
    old = retained_with_provenance(place('1'), 'instance-a', {'places': None})
    legacy = retained_with_provenance(place('2'), 'instance-a', {'places': None})
    enriched = retained_with_provenance(place('2'), 'instance-a', {'places': 'instance-a'})
    old = type(old).model_validate_json(old.model_dump_json())
    legacy = type(legacy).model_validate_json(legacy.model_dump_json())

    result = compare(old, legacy)
    assert result.status == Status.ok
    assert [entry.change for entry in result.data] == ['source_record_missing', 'source_record_added']

    for before, after in ((old, enriched), (enriched, old)):
        result = compare(before, after)
        assert result.status == Status.ok
        change, = result.data
        assert change.change == 'conditions_changed'
        assert change.before.model_dump(mode='json').get('topic_provenance') == (
            None if before is old else {'places': {'provider_instance': 'instance-a'}}
        )
        assert change.after.model_dump(mode='json').get('topic_provenance') == (
            None if after is old else {'places': {'provider_instance': 'instance-a'}}
        )


def test_added_and_changed_records_are_factual_and_deterministic():
    original = place('1', native_names={'de': 'Alt'})
    updated = place('1', native_names={'de': 'Neu'})
    result = compare(snap((original,)), snap((place('2'), updated)))
    assert result.status == Status.ok
    assert [(c.entity_ref, c.change) for c in result.data] == [
        ('places/synthetic:site:1', 'source_record_updated'),
        ('places/synthetic:site:2', 'source_record_added')]
    assert result.data[0].before.native_names == {'de': 'Alt'}
    assert result.data[0].after.native_names == {'de': 'Neu'}


def test_key_record_and_evidence_order_do_not_create_changes():
    a = place('1', native_names={'de': 'Name', 'en': 'Name'})
    b = place('1', native_names={'en': 'Name', 'de': 'Name'})
    assert compare(snap((a, place('2'))), snap((place('2'), b))).data == ()


def test_method_and_location_changes_suppress_record_deltas():
    base = analysis((place('1'),))
    for field, value in [('method_version', 'v2'), ('location_versions', {'site': 2}),
                         ('effective_conditions', {'query': 'different'}), ('profile_ref', 'retail@2')]:
        changed = base.model_copy(update={'request_context': base.request_context.model_copy(update={field: value})})
        result = compare(snapshot(base, 'planning').data, snapshot(changed, 'planning').data)
        assert result.status == Status.ok
        assert len(result.data) == 1
        assert (result.data[0].kind, result.data[0].change) == ('method', 'conditions_changed')
    source_change = compare(snap((place('1'),)), snap((place('2'),), ev=evidence(method_version='v2')))
    assert [c.kind for c in source_change.data] == ['method']
    coverage_change = compare(snap((place('1'),)), snap((place('2'),), coverage='complete:different-area'))
    assert [c.kind for c in coverage_change.data] == ['method']


@pytest.mark.parametrize('change_name', [False, True])
def test_record_evidence_method_switch_is_not_a_fact_update(change_name):
    first = evidence('e1', source_ref='synthetic-query-a', method_version='v1')
    second = evidence('e2', source_ref='synthetic-query-b', method_version='v2')
    def run(evidence_id, name):
        record = place('1', evidence_ids=(evidence_id,), native_names={'de': name})
        base = analysis((record,))
        topic = base.topic_results['places'].model_copy(update={'evidence': (first, second)})
        return snapshot(base.model_copy(update={'topic_results': {'places': topic}}), 'planning').data
    old = run('e1', 'Original')
    new = run('e2', 'Changed' if change_name else 'Original')
    result = compare(old, new)
    assert result.status == Status.ok
    assert len(result.data) == 1
    assert (result.data[0].kind, result.data[0].change) == ('method', 'conditions_changed')


def test_request_ids_and_retrieval_times_are_not_query_changes():
    base = analysis((place('1'),))
    changed = analysis((place('1'),), context=base.request_context.model_copy(update={'request_id': 'new-run'}),
        ev=evidence(retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc)))
    assert compare(snapshot(base, 'planning').data, snapshot(changed, 'planning').data).data == ()


from pydantic import ValidationError
from geo_intelligence_core.models.analysis import Metric, MetricConditions, Snapshot


def rehash(value):
    """Rehash synthetic fixtures to test validation beyond the integrity check."""
    import hashlib
    import json
    raw = json.dumps(value.model_dump(mode='json', exclude={'canonical_hash'}),
                     ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return value.model_copy(update={'canonical_hash': hashlib.sha256(raw.encode()).hexdigest()})


@pytest.mark.parametrize('field,value', [('purpose', ''), ('purpose', 'other-purpose'),
    ('canonical_hash', 'incorrect'), ('retained_evidence_ids', ()), ('schema_version', '2.0')])
def test_invalid_snapshot_metadata_is_rejected_without_payload(field, value):
    original = snap((place('1'),))
    changed = original.model_copy(update={field: value})
    if field != 'canonical_hash':
        changed = rehash(changed)
    result = compare(original, changed)
    assert result.status == Status.invalid_input and result.data is None


def test_redacted_history_never_turns_missing_sources_into_removals():
    original = snap((place('1'),))
    denied = evidence(rights=Rights(use=Permission.allowed, retain=Permission.denied, permitted_purpose='planning'))
    redacted = snap((place('1'),), ev=denied)
    assert redacted.redactions
    result = compare(original, redacted)
    assert result.status == Status.partial and result.data is None
    assert 'history_redacted' in [i.code for i in result.issues]


@pytest.mark.parametrize('status', [Status.partial, Status.unavailable, Status.unknown, Status.disabled,
                                   Status.rate_limited, Status.conflict])
def test_incomplete_topic_never_means_no_source_records(status):
    result = compare(snap((place('1'),)), snap((), status=status))
    assert result.status == Status.partial and result.data is None


def test_explicit_no_results_is_comparable_but_null_is_not():
    result = compare(snap((place('1'),)), snap((), status=Status.no_results))
    assert result.status == Status.ok and result.data[0].change == 'source_record_missing'
    source = analysis(())
    topic = source.topic_results['places'].model_copy(update={'data': None, 'status': Status.unknown})
    missing = snapshot(source.model_copy(update={'topic_results': {'places': topic}}), 'planning').data
    assert compare(snap((place('1'),)), missing).data is None


@pytest.mark.parametrize('updates', [
    {'coverage': None},
    {'coverage': 'unknown'},
    {'coverage': 'partial'},
    {'coverage': 'synthetic-complete'},
    {'coverage': 'complete:'},
    {'coverage': ' complete:synthetic-area-v1'},
])
def test_unknown_coverage_cannot_be_compared(updates):
    result = compare(snap((place('1'),)), snap((place('2'),), **updates))
    assert result.status == Status.partial and result.data is None


def test_duplicate_source_identity_is_invalid_not_silently_deduplicated():
    result = compare(snap((place('1'), place('1'))), snap((place('1'),)))
    assert result.status == Status.invalid_input and result.data is None


def test_nonempty_no_results_and_inconsistent_counts_are_invalid():
    assert compare(snap((place('1'),), status=Status.no_results), snap(())).status == Status.invalid_input
    source = analysis((place('1'),))
    topic = source.topic_results['places']
    bad = topic.model_copy(update={'data': topic.data.model_copy(update={'unique_count': 2})})
    broken = snapshot(source.model_copy(update={'topic_results': {'places': bad}}), 'planning').data
    assert compare(broken, snap(())).status == Status.invalid_input


def test_missing_query_conditions_and_unsupported_payload_are_explicit():
    context = analysis().request_context.model_copy(update={'effective_conditions': {}})
    assert compare(snap(context=context), snap(context=context)).status == Status.partial
    source = analysis()
    topic = source.topic_results['places'].model_copy(update={'data': {'arbitrary': 7}})
    unsupported = snapshot(source.model_copy(update={'topic_results': {'places': topic}}), 'planning').data
    result = compare(unsupported, unsupported)
    assert result.status == Status.unsupported and result.data is None


@pytest.mark.parametrize('permission', [Permission.denied, Permission.unknown])
def test_retention_does_not_grant_use(permission):
    ev = evidence(rights=Rights(use=permission, retain=Permission.allowed, permitted_purpose='planning'))
    original = snap((place('1'),), ev=ev)
    result = compare(original, original)
    assert result.status == Status.invalid_input and result.data is None


def test_record_evidence_must_be_authorized_in_its_topic():
    original = snap((place('1'),))
    raw = original.model_dump(mode='json')
    raw['analysis']['topic_results']['places']['data']['places'][0]['evidence_ids'] = ['missing']
    bad = rehash(Snapshot.model_validate(raw))
    result = compare(original, bad)
    assert result.status == Status.invalid_input and result.data is None


def metric_snapshot(value, *, conditions=None, unit='people', nature='measured'):
    context = analysis().request_context
    metric = Metric(value=value, unit=unit, nature=nature, evidence_ids=('e1',))
    source = Analysis(request_context=context, selected_topics=('population_reference',),
        topic_results={'population_reference': Result(status=Status.ok, data=None,
            evidence=(evidence(),), context=context)}, metrics={'population': metric},
        metric_conditions={'population': conditions or MetricConditions(
            **{name: 'synthetic' for name in MetricConditions.model_fields})})
    return snapshot(source, 'planning').data


def test_typed_metric_updates_preserve_zero_and_missing():
    result = compare(metric_snapshot(3), metric_snapshot(0))
    assert result.status == Status.ok and len(result.data) == 1
    change = result.data[0]
    assert change.change == 'metric_changed' and change.entity_ref == 'metrics/population'
    assert change.before.value == 3 and change.after.value == 0
    unknown = compare(metric_snapshot(3), metric_snapshot(None))
    assert unknown.status == Status.partial and unknown.data is None


def test_metric_units_nature_and_incomplete_conditions_suppress_numeric_comparison():
    for changed in [metric_snapshot(0, unit='households'), metric_snapshot(0, nature='estimated')]:
        result = compare(metric_snapshot(3), changed)
        assert result.status == Status.ok and [c.kind for c in result.data] == ['method']
    result = compare(metric_snapshot(3), metric_snapshot(4, conditions=MetricConditions()))
    assert result.status == Status.partial and result.data is None


def test_metric_evidence_method_switch_suppresses_numeric_delta():
    first = evidence('e1', source_ref='synthetic-query-a', method_version='v1')
    second = evidence('e2', source_ref='synthetic-query-b', method_version='v2')
    def run(evidence_id, value):
        base = metric_snapshot(value)
        topic = base.analysis.topic_results['population_reference'].model_copy(
            update={'evidence': (first, second)})
        metric = base.analysis.metrics['population'].model_copy(update={'evidence_ids': (evidence_id,)})
        analysis = base.analysis.model_copy(update={
            'topic_results': {'population_reference': topic}, 'metrics': {'population': metric}})
        return rehash(base.model_copy(update={
            'analysis': analysis, 'retained_evidence_ids': ('e1', 'e2')}))
    result = compare(run('e1', 3), run('e2', 4))
    assert result.status == Status.ok
    assert len(result.data) == 1
    assert (result.data[0].kind, result.data[0].change) == ('method', 'conditions_changed')


def test_watch_spec_is_only_typed_declarative_conditions():
    from geo_intelligence_core.models.change import WatchSpec
    spec = WatchSpec(topics=('places',), changes=('source_record_missing',))
    assert spec.topics == ('places',) and not hasattr(spec, 'start')
    for kwargs in [{'topics': ()}, {'topics': ('',)}, {'topics': ('places', 'places')},
                   {'topics': ('places',), 'interval_s': 60},
                   {'topics': ('places',), 'changes': ('closed',)}]:
        with pytest.raises(ValidationError):
            WatchSpec(**kwargs)


def test_validation_failure_does_not_echo_untrusted_snapshot_context():
    original = snap((place('1'),))
    context = original.analysis.request_context.model_copy(update={'effective_conditions': {'secret': 'UNTRUSTED-MARKER'}})
    changed = original.model_copy(update={'analysis': original.analysis.model_copy(update={'request_context': context})})
    result = compare(original, changed)
    assert result.status == Status.invalid_input
    assert 'UNTRUSTED-MARKER' not in result.model_dump_json()


def test_snapshot_topic_context_must_be_retained_context():
    original = snap((place('1'),))
    topic = original.analysis.topic_results['places']
    topic = topic.model_copy(update={'context': topic.context.model_copy(update={'scope_token': 'foreign-case'})})
    changed = rehash(original.model_copy(update={'analysis': original.analysis.model_copy(
        update={'topic_results': {'places': topic}})}))
    assert compare(original, changed).status == Status.invalid_input


def test_evidence_refresh_is_not_a_record_update():
    updated = place('1', evidence_ids=('e2',), categories=('b', 'a'))
    original = place('1', categories=('a', 'b'))
    assert compare(snap((original,)), snap((updated,), ev=evidence('e2'))).data == ()


def test_record_reference_escapes_separators():
    record = place('entity:part/one')
    result = compare(snap(()), snap((record,)))
    assert result.data[0].entity_ref == 'places/synthetic:site:entity%3Apart%2Fone'


def test_same_snapshot_roundtrip_is_stable_and_immutable():
    original = snap((place('1'),))
    restored = Snapshot.model_validate_json(original.model_dump_json())
    assert compare(original, restored).status == Status.ok
    assert compare(original, restored).data == ()
    from geo_intelligence_core.models.change import Change
    changes = compare(original, snap(())).data
    with pytest.raises(ValidationError):
        changes[0].verification = 'verified_real_world'
    with pytest.raises(ValidationError):
        Change(kind='verified_real_world', change='closed', entity_ref='place',
               before=None, after=None, evidence_ids=())


@pytest.mark.parametrize('industry', ['food-service@1', 'retail@1', 'education@1'])
def test_history_contract_is_industry_neutral(industry):
    context = analysis().request_context.model_copy(update={'profile_ref': industry})
    result = compare(snap((place('1'),), context=context), snap((), context=context))
    assert result.status == Status.ok
    assert result.data[0].change == 'source_record_missing'
    assert result.data[0].verification == 'unverified'


def test_change_schema_rejects_inconsistent_kind_and_typed_payload():
    from geo_intelligence_core.models.change import Change
    for fields in [
        dict(kind='method', change='source_record_missing', before=place('1'), after=None),
        dict(kind='source_record', change='source_record_added', before=place('1'), after=None),
        dict(kind='source_record', change='metric_changed', before=place('1'), after=place('2')),
        dict(kind='source_record', change='source_record_updated', before=place('1'), after=place('2')),
    ]:
        with pytest.raises(ValidationError):
            Change(entity_ref='fixture', evidence_ids=('e1',), **fields)


def test_unrelated_null_topic_cannot_borrow_metric_completeness():
    source = metric_snapshot(3).analysis
    topic = Result(status=Status.ok, data=None, evidence=(evidence('e2'),), context=source.request_context)
    changed = source.model_copy(update={'topic_results': {**source.topic_results, 'places': topic},
                                        'selected_topics': (*source.selected_topics, 'places')})
    retained = snapshot(changed, 'planning').data
    result = compare(retained, retained)
    assert result.status == Status.partial and result.data is None


def test_manual_verification_and_derived_comparisons_are_explicitly_outside_slice():
    from geo_intelligence_core.evidence import apply_correction
    from geo_intelligence_core.models.analysis import Comparison, Correction
    context = analysis().request_context.model_copy(update={'scope_token': 'case'})
    original = analysis((place('1'),), context=context)
    corrected = apply_correction(original, Correction(target_ref='places/synthetic:site:1',
        action='confirm', evidence_ids=('e1',), reason='manual source confirmation',
        scope_token='case', at='2026-11-10T00:00:00Z'), 'case').data
    for changed in [corrected, original.model_copy(update={'comparison': Comparison(rows=())})]:
        result = compare(snapshot(original, 'planning').data, snapshot(changed, 'planning').data)
        assert result.status == Status.unsupported and result.data is None
