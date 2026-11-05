"""Analysis result shapes, without an executable analysis pipeline."""
from typing import Literal
from pydantic import Field, StrictFloat, StrictInt
from .common import FrozenModel, Result
from .requests import RequestContext

Number = StrictFloat | StrictInt


class Metric(FrozenModel):
    value: Number | None
    unit: str
    nature: Literal['measured', 'derived', 'estimated', 'unverified']
    numerator: Number | None = None
    denominator: Number | None = None
    evidence_ids: tuple[str, ...] = ()


class MetricConditions(FrozenModel):
    category_mapping_version: str | None = None
    category_selection: str | None = None
    source_coverage: str | None = None
    reference_period: str | None = None
    scope_type: str | None = None
    scope_threshold: str | None = None
    scope_version: str | None = None
    boundary_rule: str | None = None
    method: str | None = None
    time_condition: str | None = None

    @property
    def complete(self) -> bool:
        return all(bool(getattr(self, field)) for field in type(self).model_fields)


class Analysis(FrozenModel):
    request_context: RequestContext
    topic_results: dict[str, Result[object]] = Field(default_factory=dict)
    selected_topics: tuple[str, ...] = ()
    metrics: dict[str, Metric] = Field(default_factory=dict)
    metric_conditions: dict[str, MetricConditions] = Field(default_factory=dict)
    comparison: 'Comparison | None' = None
    location_statuses: dict[str, str] = Field(default_factory=dict)
    corrections: tuple['Correction', ...] = ()
    originals: dict[str, dict[str, object]] = Field(default_factory=dict)


class ComparisonRow(FrozenModel):
    location_version: str
    metric_id: str
    value: Number | None
    difference: Number | None
    unit: str
    evidence_ids: tuple[str, ...] = ()
    comparability_issues: tuple[str, ...] = ()


class Comparison(FrozenModel):
    rows: tuple[ComparisonRow, ...]
    union_counts: dict[str, StrictInt | None] = Field(default_factory=dict)
    union_issues: dict[str, tuple[str, ...]] = Field(default_factory=dict)


class Snapshot(FrozenModel):
    schema_version: str = '1.0'
    analysis: Analysis
    canonical_hash: str
    retained_evidence_ids: tuple[str, ...]
    redactions: tuple[str, ...] = ()
    purpose: str = ''


class Correction(FrozenModel):
    target_ref: str
    action: Literal['confirm', 'correct', 'exclude', 'attach']
    replacement: dict[str, object] | None = None
    attachments: tuple[dict[str, object], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason: str
    scope_token: str
    at: str


Analysis.model_rebuild()
