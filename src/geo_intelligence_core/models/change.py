"""Additive, immutable source-history facts, never real-world conclusions."""
from typing import Literal
from pydantic import Field, model_validator
from .analysis import Metric, MetricConditions
from .common import FrozenModel
from .places import Place


class SourceMethod(FrozenModel):
    source_id: str
    source_type: str
    source_ref: str
    method_version: str
    reference_period: str | None
    valid_period: str | None


class MetricMethod(FrozenModel):
    unit: str
    nature: str


class HistoryConditions(FrozenModel):
    location_versions: dict[str, int]
    effective_conditions: dict[str, str]
    profile_ref: str | None
    template_ref: str | None
    method_version: str
    selected_topics: tuple[str, ...]
    sources: dict[str, tuple[SourceMethod, ...]]
    coverage: dict[str, str | None]
    metric_conditions: dict[str, MetricConditions] = Field(default_factory=dict)
    metric_methods: dict[str, MetricMethod] = Field(default_factory=dict)


class Change(FrozenModel):
    kind: Literal['source_record', 'method']
    change: Literal['source_record_missing', 'source_record_added', 'source_record_updated', 'conditions_changed', 'metric_changed']
    entity_ref: str
    before: Place | Metric | HistoryConditions | None
    after: Place | Metric | HistoryConditions | None
    evidence_ids: tuple[str, ...]
    verification: Literal['unverified'] = 'unverified'

    @model_validator(mode='after')
    def consistent_change(self):
        if self.change == 'conditions_changed':
            valid = self.kind == 'method' and isinstance(self.before, HistoryConditions) and isinstance(self.after, HistoryConditions)
        elif self.change == 'metric_changed':
            valid = self.kind == 'source_record' and isinstance(self.before, Metric) and isinstance(self.after, Metric)
        elif self.change == 'source_record_added':
            valid = self.kind == 'source_record' and self.before is None and isinstance(self.after, Place)
        elif self.change == 'source_record_missing':
            valid = self.kind == 'source_record' and isinstance(self.before, Place) and self.after is None
        else:
            valid = (self.kind == 'source_record' and isinstance(self.before, Place) and
                     isinstance(self.after, Place) and self.before.source_key == self.after.source_key)
        if not valid or not self.entity_ref.strip() or not self.evidence_ids:
            raise ValueError('change kind, payload and evidence must agree')
        return self


class WatchSpec(FrozenModel):
    """Consumer-owned watch conditions only; no scheduling or side effects."""
    topics: tuple[str, ...] = Field(min_length=1)
    changes: tuple[Literal['source_record_missing', 'source_record_added',
        'source_record_updated', 'conditions_changed', 'metric_changed'], ...] = (
        'source_record_missing', 'source_record_added', 'source_record_updated',
        'conditions_changed', 'metric_changed')

    @model_validator(mode='after')
    def unique_conditions(self):
        if (any(not topic.strip() for topic in self.topics) or
                len(set(self.topics)) != len(self.topics) or
                not self.changes or len(set(self.changes)) != len(self.changes)):
            raise ValueError('watch topics and change conditions must be nonempty and unique')
        return self
