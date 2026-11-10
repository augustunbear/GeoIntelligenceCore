"""Offline source-record history; no real-world inferences or scheduling."""
import hashlib
import json
import re
from urllib.parse import quote

from pydantic import ValidationError

from .models.analysis import Snapshot
from .models.change import Change, HistoryConditions, MetricMethod, SourceMethod
from .models.common import Issue, Result, Status
from .models.places import PlaceSet
from .models.requests import RequestContext


class _NotComparable(Exception):
    def __init__(self, status: Status, code: str):
        self.status, self.code = status, code


def _fail(status: Status, code: str):
    raise _NotComparable(status, code)


def _prepare(snap: Snapshot) -> dict[str, PlaceSet]:
    """Validate retained rights and completeness before revealing any change payload."""
    canonical = json.dumps(snap.model_dump(mode='json', exclude={'canonical_hash'}),
                           ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if (snap.schema_version != '1.0' or not snap.purpose.strip() or
            snap.canonical_hash != hashlib.sha256(canonical.encode()).hexdigest()):
        _fail(Status.invalid_input, 'history_invalid_snapshot')
    if snap.redactions:
        _fail(Status.partial, 'history_redacted')
    analysis = snap.analysis
    context = analysis.request_context
    if analysis.corrections or analysis.originals or analysis.comparison is not None:
        _fail(Status.unsupported, 'history_unsupported_analysis')
    if context.scope_token is not None:
        _fail(Status.invalid_input, 'history_not_retained')
    if not context.location_versions or not context.effective_conditions:
        _fail(Status.partial, 'history_unknown_conditions')
    if not analysis.topic_results or not analysis.selected_topics:
        _fail(Status.partial, 'history_incomplete')
    if any(not any(name == selected or name.endswith('/' + selected)
                   for name in analysis.topic_results) for selected in analysis.selected_topics):
        _fail(Status.partial, 'history_missing_topic')
    all_evidence = {}
    topics = {}
    null_topics = False
    for name, topic in analysis.topic_results.items():
        if topic.context != context or topic.schema_version != '1.0':
            _fail(Status.invalid_input, 'history_invalid_topic_context')
        if topic.status not in (Status.ok, Status.no_results):
            _fail(Status.partial, 'history_incomplete_topic')
        ids = [e.id for e in topic.evidence]
        if not ids or len(set(ids)) != len(ids):
            _fail(Status.invalid_input, 'history_invalid_evidence')
        for e in topic.evidence:
            if not e.rights.allows('use', snap.purpose) or not e.rights.allows('retain', snap.purpose):
                _fail(Status.invalid_input, 'history_evidence_not_permitted')
            if e.id in all_evidence and all_evidence[e.id] != e:
                _fail(Status.invalid_input, 'history_ambiguous_evidence')
            all_evidence[e.id] = e
        if topic.data is None:
            null_topics = True
            continue
        try:
            places = PlaceSet.model_validate(topic.data)
        except ValidationError:
            _fail(Status.unsupported, 'history_unsupported_topic')
        if (len({p.source_key for p in places.places}) != len(places.places) or
                places.unique_count != len(places.places) or
                places.retrieved_count < places.unique_count or
                (topic.status == Status.no_results and places.unique_count != 0)):
            _fail(Status.invalid_input, 'history_invalid_places')
        # Normalized provider results default to "unknown". A record absence is
        # comparable only after an explicit complete source-query attestation.
        if not places.coverage or re.fullmatch(r'complete:[A-Za-z0-9][A-Za-z0-9._/-]{0,127}', places.coverage) is None:
            _fail(Status.partial, 'history_unknown_coverage')
        for place in places.places:
            if (not place.evidence_ids or not set(place.evidence_ids).issubset(ids) or
                    any(all_evidence[eid].source_id != place.source_key.source_id for eid in place.evidence_ids)):
                _fail(Status.invalid_input, 'history_invalid_record_evidence')
        topics[name] = places
    if set(snap.retained_evidence_ids) != set(all_evidence) or len(set(snap.retained_evidence_ids)) != len(snap.retained_evidence_ids):
        _fail(Status.invalid_input, 'history_invalid_retained_evidence')
    # A null topic is only an evidence container in an explicit metrics-only analysis.
    if null_topics and (topics or not analysis.metrics or len(analysis.topic_results) != 1 or
                        set(analysis.selected_topics) != set(analysis.topic_results)):
        _fail(Status.partial, 'history_missing_data')
    for name, metric in analysis.metrics.items():
        if not metric.evidence_ids or not set(metric.evidence_ids).issubset(all_evidence):
            _fail(Status.invalid_input, 'history_invalid_metric_evidence')
        if metric.value is None:
            _fail(Status.partial, 'history_missing_metric_value')
        conditions = analysis.metric_conditions.get(name)
        if conditions is None or not conditions.complete:
            _fail(Status.partial, 'history_unknown_metric_conditions')
    return topics


def _source_method(e):
    return SourceMethod(**{field: getattr(e, field) for field in SourceMethod.model_fields})


def _record_ref(name, key):
    ref = ':'.join(quote(part, safe='') for part in (key.source_id, key.entity_type, key.entity_id))
    return f'{quote(name, safe="")}/{ref}'


def _conditions(snap: Snapshot, topics: dict[str, PlaceSet], shared_records, shared_metrics) -> HistoryConditions:
    analysis = snap.analysis
    context = analysis.request_context
    sources = {}
    for name, topic in sorted(analysis.topic_results.items()):
        methods = {_source_method(e) for e in topic.evidence}
        sources[name] = tuple(sorted(methods, key=lambda m: m.model_dump_json()))
    evidence = {e.id: e for topic in analysis.topic_results.values() for e in topic.evidence}
    fact_methods = {}
    for name, keys in shared_records.items():
        places = {p.source_key: p for p in topics[name].places}
        for key in keys:
            methods = {_source_method(evidence[eid]) for eid in places[key].evidence_ids}
            fact_methods[_record_ref(name, key)] = tuple(sorted(methods, key=lambda m: m.model_dump_json()))
    for name in shared_metrics:
        methods = {_source_method(evidence[eid]) for eid in analysis.metrics[name].evidence_ids}
        fact_methods[f'metrics/{quote(name, safe="")}'] = tuple(sorted(methods, key=lambda m: m.model_dump_json()))
    return HistoryConditions(location_versions=context.location_versions,
        effective_conditions=context.effective_conditions, profile_ref=context.profile_ref,
        template_ref=context.template_ref, method_version=context.method_version,
        selected_topics=tuple(sorted(analysis.selected_topics)), sources=sources, fact_methods=fact_methods,
        coverage={name: topic.coverage for name, topic in topics.items()},
        metric_conditions=analysis.metric_conditions,
        metric_methods={name: MetricMethod(unit=metric.unit, nature=metric.nature)
                        for name, metric in analysis.metrics.items()})


def _same_fact(before, after):
    if before is None or after is None:
        return before is after
    # Retrieval evidence identifiers and category order are not changes in a source fact.
    old = before.model_dump(exclude={'evidence_ids'})
    new = after.model_dump(exclude={'evidence_ids'})
    if 'categories' in old:
        old['categories'] = sorted(old['categories'])
        new['categories'] = sorted(new['categories'])
    return old == new


def compare_snapshots(before: Snapshot, after: Snapshot) -> Result[tuple[Change, ...]]:
    """Return immutable factual changes, or no payload when comparison is unsafe.

    JSON encodes the immutable tuple as an array. Callers must authorize access
    to both snapshots in the same case; retained snapshots scrub case tokens.
    """
    context = RequestContext(request_id='snapshot-history', method_version='snapshot-history-v1')
    try:
        if before.purpose != after.purpose:
            _fail(Status.invalid_input, 'history_purpose_mismatch')
        old_topics, new_topics = _prepare(before), _prepare(after)
    except _NotComparable as error:
        return Result[tuple[Change, ...]](status=error.status, data=None, context=context,
            issues=(Issue(code=error.code, message_key=error.code),))
    shared_records = {name: ({p.source_key for p in old_topics[name].places} &
                             {p.source_key for p in new_topics[name].places})
                      for name in old_topics.keys() & new_topics.keys()}
    shared_metrics = before.analysis.metrics.keys() & after.analysis.metrics.keys()
    old_conditions = _conditions(before, old_topics, shared_records, shared_metrics)
    new_conditions = _conditions(after, new_topics, shared_records, shared_metrics)
    if old_conditions != new_conditions:
        change = Change(kind='method', change='conditions_changed', entity_ref='conditions',
            before=old_conditions, after=new_conditions,
            evidence_ids=tuple(sorted(set(before.retained_evidence_ids + after.retained_evidence_ids))))
        return Result[tuple[Change, ...]](status=Status.ok, data=(change,), context=context)
    changes = []
    for name, topic in sorted(old_topics.items()):
        old = {p.source_key: p for p in topic.places}
        new = {p.source_key: p for p in new_topics[name].places}
        for key in sorted(old.keys() | new.keys(), key=lambda k: (k.source_id, k.entity_type, k.entity_id)):
            previous, current = old.get(key), new.get(key)
            if _same_fact(previous, current):
                continue
            label = 'source_record_added' if previous is None else 'source_record_missing' if current is None else 'source_record_updated'
            ids = {eid for record in (previous, current) if record for eid in record.evidence_ids}
            changes.append(Change(kind='source_record', change=label,
                entity_ref=_record_ref(name, key),
                before=previous, after=current, evidence_ids=tuple(sorted(ids))))
    for name, metric in sorted(before.analysis.metrics.items()):
        current = after.analysis.metrics[name]
        if not _same_fact(metric, current):
            changes.append(Change(kind='source_record', change='metric_changed',
                entity_ref=f'metrics/{quote(name, safe="")}', before=metric, after=current,
                evidence_ids=tuple(sorted(set(metric.evidence_ids + current.evidence_ids)))))
    return Result[tuple[Change, ...]](status=Status.ok, data=tuple(changes), context=context)
