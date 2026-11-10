"""Bounded, atomic import of caller-authorized transport facts, not live data."""
from datetime import datetime
import json
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, ValidationError, field_validator, model_validator

from ..models.common import FrozenModel, Issue, Result, Status
from ..models.evidence import Evidence, utc
from ..models.location import Point
from ..models.requests import RequestContext


class TransportFact(FrozenModel):
    """One explicit observation; validity is [valid_from, valid_until)."""

    id: str = Field(min_length=1, max_length=256)
    kind: Literal['parking_capacity', 'parking_free_spaces', 'parking_fee',
                  'accessibility', 'cycling_restriction', 'construction']
    value: StrictInt | str
    unit: Literal['spaces', 'statement']
    location: Point
    valid_from: datetime
    valid_until: datetime
    measured_at: datetime
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    segment_ref: str | None = Field(default=None, min_length=1, max_length=256)
    direction: Literal['forward', 'backward', 'both'] | None = None

    @field_validator('valid_from', 'valid_until', 'measured_at')
    @classmethod
    def aware_timestamp(cls, value):
        return utc(value)

    @field_validator('id', 'value', 'segment_ref')
    @classmethod
    def meaningful_text(cls, value):
        if isinstance(value, str) and (not value.strip() or len(value) > 4096):
            raise ValueError('text must be nonblank and bounded')
        return value

    @model_validator(mode='after')
    def explicit_semantics(self):
        if self.valid_until <= self.valid_from:
            raise ValueError('validity must have positive duration')
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or any(not e.strip() for e in self.evidence_ids):
            raise ValueError('evidence IDs must be unique and nonblank')
        if self.kind in ('parking_capacity', 'parking_free_spaces'):
            if type(self.value) is not int or self.value < 0 or self.unit != 'spaces':
                raise ValueError('counts require nonnegative integer spaces')
        elif not isinstance(self.value, str) or self.unit != 'statement':
            raise ValueError('other facts require an explicit statement')
        if self.kind in ('accessibility', 'cycling_restriction', 'construction'):
            if self.segment_ref is None or self.direction is None:
                raise ValueError('restriction requires explicit segment and direction')
        return self


def _preflight_size(records, evidence):
    """Reject huge fields/containers before model dumping or JSON allocation."""
    nodes = 0
    characters = 0

    def visit(value, depth=0):
        nonlocal nodes, characters
        nodes += 1
        if nodes > 50000 or depth > 16:
            raise ValueError('input structure too large')
        if isinstance(value, str):
            characters += len(value)
            if len(value) > 65536 or characters > 1048576:
                raise ValueError('input text too large')
        elif isinstance(value, BaseModel):
            for name in type(value).model_fields:
                visit(getattr(value, name), depth + 1)
        elif isinstance(value, dict):
            if len(value) > 1000:
                raise ValueError('object too large')
            for key, item in value.items():
                visit(key, depth + 1)
                visit(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            if len(value) > 1000:
                raise ValueError('collection too large')
            for item in value:
                visit(item, depth + 1)
    visit(records)
    visit(evidence)


def import_transport(records: list[dict], *, evidence: list[Evidence], purpose: str,
                     as_of: datetime, context: RequestContext) -> Result[tuple[TransportFact, ...]]:
    """Validate all records or return no facts. No implicit current time or rights.

    Limits are 1,000 records, 100 evidence records and 1 MiB encoded input in
    total. Permission for use does not imply permission to retain or export.
    Expired/future facts reject the whole batch rather than appearing current.
    """
    def result(status, code=None, facts=None, sources=()):
        return Result[tuple[TransportFact, ...]](
            status=status, data=facts, context=context, evidence=sources,
            issues=() if code is None else (Issue(code=code, message_key=code),))

    try:
        context = RequestContext.model_validate(context)
    except (ValueError, TypeError):
        context = RequestContext(request_id='transport-invalid-input')
        return result(Status.invalid_input, 'transport_invalid_context')

    try:
        if (type(records) is not list or len(records) > 1000 or
                type(evidence) not in (list, tuple) or len(evidence) > 100 or
                not isinstance(purpose, str) or not purpose.strip()):
            raise ValueError('invalid bounds or purpose')
        _preflight_size(records, evidence)
        when = utc(as_of)
        sources = tuple(Evidence.model_validate(item) for item in evidence)
        raw = {'records': records, 'evidence': [item.model_dump(mode='json') for item in sources]}
        if len(json.dumps(raw, allow_nan=False, ensure_ascii=True).encode('utf-8')) > 1048576:
            raise ValueError('input too large')
        facts = tuple(TransportFact.model_validate(item) for item in records)
        source_ids = [item.id for item in sources]
        if len(set(source_ids)) != len(source_ids) or len({f.id for f in facts}) != len(facts):
            raise ValueError('duplicate IDs')
        used = {eid for fact in facts for eid in fact.evidence_ids}
        if used != set(source_ids):
            raise ValueError('evidence must be present and used exactly')
        if any(f.measured_at > when for f in facts) or any(s.retrieved_at > when for s in sources):
            raise ValueError('future observations are not facts as of requested time')
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError, ValidationError):
        return result(Status.invalid_input, 'transport_invalid_input')
    if not facts:
        return result(Status.no_results, facts=())
    if any(not item.rights.allows('use', purpose) for item in sources):
        return result(Status.unavailable, 'transport_rights_restricted')
    if any(not (f.valid_from <= when < f.valid_until) for f in facts):
        return result(Status.unavailable, 'transport_outside_valid_period')
    return result(Status.ok, facts=facts, sources=sources)
