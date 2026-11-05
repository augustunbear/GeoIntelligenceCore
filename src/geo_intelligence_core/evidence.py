"""Scoped factual corrections and purpose-bound retained snapshots."""
import hashlib
import json
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_core import to_json

from .models.analysis import Analysis, Correction, Metric, Snapshot
from .models.common import Issue, Result, Status
from .models.evidence import Evidence
from .models.places import Place, PlaceSet


_DROP = object()


def _issue(code: str) -> Issue:
    return Issue(code=code, message_key=code)


def _records(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    return json.loads(to_json(value))


def _filter(value: Any, permitted: set[str], known: set[str], *, fallback: set[str]) -> Any:
    """Drop source-backed nodes unless every contributing evidence source grants access."""
    raw = _records(value)
    if isinstance(raw, dict):
        ids = raw.get('evidence_ids')
        if ids is not None:
            if not ids or not set(ids).issubset(permitted):
                return _DROP
            fallback = set(ids)
        if 'source_key' in raw and not fallback:
            return _DROP
        result = {}
        for key, item in raw.items():
            if key in ('evidence_ids',):
                result[key] = item
                continue
            filtered = _filter(item, permitted, known, fallback=fallback)
            if filtered is not _DROP:
                result[key] = filtered
        if not result and raw:
            return _DROP
        return result
    if isinstance(raw, (list, tuple)):
        return [item for v in raw if (item := _filter(v, permitted, known, fallback=fallback)) is not _DROP]
    if fallback and fallback.issubset(permitted):
        return raw
    if not known and raw is None:
        return raw
    return _DROP


def _sanitize(analysis: Analysis, purpose: str, action: str) -> tuple[Analysis, tuple[str, ...], tuple[str, ...]]:
    topics = {}
    retained = set()
    redactions = []
    allowed_by_topic = {}
    known_by_topic = {}
    for name, topic in analysis.topic_results.items():
        sources = {e.id: e for e in topic.evidence}
        known_by_topic[name] = set(sources)
        same_scope = topic.context.scope_token == analysis.request_context.scope_token
        allowed = {eid for eid, e in sources.items()
                   if sum(item.id == eid for item in topic.evidence) == 1 and
                   e.rights.allows(action, purpose)} if same_scope else set()
        allowed_by_topic[name] = allowed
        retained.update(allowed if action == 'retain' else sources)
        filtered = _filter(topic.data, allowed, set(sources), fallback=set(sources)) if topic.data is not None and same_scope else None
        if filtered is _DROP:
            filtered = None
        original = _records(topic.data)
        if filtered != original or len(allowed) != len(sources) or not same_scope:
            redactions.append(name)
        topic_evidence = tuple(e for e in topic.evidence if e.id in allowed)
        topics[name] = topic.model_copy(update={'data': filtered, 'evidence': topic_evidence,
                                                  'status': Status.partial if filtered != original and topic.data is not None else topic.status})
    context = analysis.request_context.model_copy(update={'scope_token': None})
    topics = {name: topic.model_copy(update={'context': context}) for name, topic in topics.items()}
    corrections = []
    for item in analysis.corrections:
        valid_scope = (item.scope_token == analysis.request_context.scope_token if action == 'retain'
                       else item.scope_token == '[redacted]' and analysis.request_context.scope_token is None)
        target_topic = item.target_ref.split('/', 1)[0]
        permitted = allowed_by_topic.get(target_topic, set())
        known = known_by_topic.get(target_topic, set())
        if (not valid_scope or not item.evidence_ids or
                not set(item.evidence_ids).issubset(permitted)):
            redactions.append(f'correction:{item.target_ref}')
            continue
        replacement = _filter(item.replacement, permitted, known, fallback=set(item.evidence_ids)) if item.replacement else None
        if item.replacement is not None and replacement is _DROP:
            redactions.append(f'correction:{item.target_ref}')
            continue
        if item.replacement is not None and replacement != _records(item.replacement):
            redactions.append(f'correction:{item.target_ref}')
        attachments = []
        for attachment in item.attachments:
            try:
                verified = Evidence.model_validate(attachment)
            except ValidationError:
                redactions.append(f'attachment:{item.target_ref}')
                continue
            if verified.id in permitted:
                attachments.append(verified.model_dump(mode='json'))
            else:
                redactions.append(f'attachment:{item.target_ref}')
        corrections.append(item.model_copy(update={'scope_token': '[redacted]',
                                                'replacement': replacement, 'attachments': tuple(attachments)}))
    accepted_refs = {item.target_ref for item in corrections}
    originals = {}
    for ref, original in analysis.originals.items():
        target_topic = ref.split('/', 1)[0]
        permitted = allowed_by_topic.get(target_topic, set())
        known = known_by_topic.get(target_topic, set())
        raw = _records(original)
        kept = _filter(raw, permitted, known, fallback=set(raw.get('evidence_ids', ())))
        if ref in accepted_refs and kept is not _DROP and kept == raw:
            originals[ref] = kept
        else:
            redactions.append(f'original:{ref}')
    clean = analysis.model_copy(update={'request_context': context, 'topic_results': topics,
                                        'originals': originals, 'corrections': tuple(corrections)})
    return clean, tuple(sorted(retained)), tuple(sorted(set(redactions)))


def apply_correction(analysis: Analysis, correction: Correction, scope_token: str) -> Result[Analysis]:
    context = analysis.request_context
    invalid = Result[Analysis](status=Status.invalid_input, data=None, issues=(_issue('invalid_correction'),), context=context)
    if not scope_token or context.scope_token != scope_token or correction.scope_token != scope_token:
        return invalid
    if correction.action in ('confirm', 'exclude') and correction.replacement is not None:
        return invalid
    if correction.action == 'correct' and correction.replacement is None:
        return invalid
    if correction.action == 'attach' and not correction.attachments:
        return invalid
    if correction.action == 'attach':
        try:
            attached = tuple(Evidence.model_validate(a) for a in correction.attachments)
        except ValidationError:
            return invalid
    else:
        attached = ()
    if correction.action != 'correct' and correction.replacement is not None:
        return invalid
    try:
        topic_id, key = correction.target_ref.split('/', 1)
        topic = analysis.topic_results[topic_id]
        if isinstance(topic.data, dict):
            record = topic.data[key]
            index = None
        elif isinstance(topic.data, PlaceSet):
            matches = [(i, place) for i, place in enumerate(topic.data.places)
                       if key == f'{place.source_key.source_id}:{place.source_key.entity_type}:{place.source_key.entity_id}']
            if len(matches) != 1:
                return invalid
            index, record = matches[0]
        else:
            return invalid
    except (ValueError, KeyError, TypeError):
        return invalid
    if record is None or not isinstance(record, (Metric, Place)):
        return invalid
    known_ids = {e.id for e in topic.evidence} | {e.id for e in attached}
    if not correction.evidence_ids or not set(correction.evidence_ids).issubset(known_ids):
        return invalid
    if correction.action == 'correct':
        raw = correction.replacement
        if not isinstance(raw, dict) or any(k in raw for k in ('rights', 'source_id', 'source_ref', 'source_type')):
            return invalid
        try:
            new = type(record).model_validate(raw)
        except ValidationError:
            return invalid
        if new.evidence_ids != record.evidence_ids or (isinstance(record, Place) and new.source_key != record.source_key):
            return invalid
        if index is None:
            data = dict(topic.data)
            data[key] = new
        else:
            places = list(topic.data.places)
            places[index] = new
            data = topic.data.model_copy(update={'places': tuple(places)})
        topic = topic.model_copy(update={'data': data})
        originals = dict(analysis.originals)
        originals.setdefault(correction.target_ref, record.model_dump(mode='json'))
    else:
        originals = dict(analysis.originals)
        originals.setdefault(correction.target_ref, record.model_dump(mode='json'))
    if attached:
        if {e.id for e in attached} & {e.id for e in topic.evidence}:
            return invalid
        topic = topic.model_copy(update={'evidence': (*topic.evidence, *attached)})
    if correction.action == 'exclude':
        if index is None:
            data = dict(topic.data)
            data.pop(key)
        else:
            places = list(topic.data.places)
            places.pop(index)
            data = topic.data.model_copy(update={'places': tuple(places),
                                                 'unique_count': topic.data.unique_count - 1})
        topic = topic.model_copy(update={'data': data, 'status': Status.partial})
    topics = dict(analysis.topic_results)
    topics[topic_id] = topic
    updated = analysis.model_copy(update={'topic_results': topics, 'originals': originals,
                                          'corrections': (*analysis.corrections, correction)})
    return Result[Analysis](status=Status.ok, data=updated, context=context)


def snapshot(analysis: Analysis, purpose: str) -> Result[Snapshot]:
    if not purpose:
        return Result[Snapshot](status=Status.invalid_input, data=None, issues=(_issue('purpose_required'),), context=analysis.request_context)
    clean, ids, redactions = _sanitize(analysis, purpose, 'retain')
    provisional = Snapshot(analysis=clean, canonical_hash='', retained_evidence_ids=ids, redactions=redactions, purpose=purpose)
    canonical = json.dumps(provisional.model_dump(mode='json', exclude={'canonical_hash'}), ensure_ascii=False,
                           sort_keys=True, separators=(',', ':'))
    snap = provisional.model_copy(update={'canonical_hash': hashlib.sha256(canonical.encode()).hexdigest()})
    return Result[Snapshot](status=Status.partial if redactions else Status.ok, data=snap,
                            issues=(_issue('redacted'),) if redactions else (), context=clean.request_context)
