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


class Analysis(FrozenModel):
    request_context: RequestContext
    topic_results: dict[str, Result[object]] = Field(default_factory=dict)
    selected_topics: tuple[str, ...] = ()


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


class Snapshot(FrozenModel):
    schema_version: str = '1.0'
    analysis: Analysis
    canonical_hash: str
    retained_evidence_ids: tuple[str, ...]
    redactions: tuple[str, ...] = ()


class Correction(FrozenModel):
    target_ref: str
    action: Literal['confirm', 'correct', 'exclude', 'attach']
    replacement: dict[str, object] | None = None
    attachments: tuple[dict[str, object], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason: str
    scope_token: str
    at: str
