"""Public result envelope and validation diagnostics."""
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Status(StrEnum):
    ok = "ok"
    partial = "partial"
    no_results = "no_results"
    not_collected = "not_collected"
    disabled = "disabled"
    unconfigured = "unconfigured"
    unsupported = "unsupported"
    unavailable = "unavailable"
    rate_limited = "rate_limited"
    invalid_input = "invalid_input"
    conflict = "conflict"
    unknown = "unknown"


class Issue(FrozenModel):
    code: str
    message_key: str
    safe_params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


T = TypeVar("T")


class Result(FrozenModel, Generic[T]):
    schema_version: str = "1.0"
    status: Status
    data: T | None
    issues: list[Issue] = Field(default_factory=list)
    evidence: list["Evidence"] = Field(default_factory=list)
    context: "RequestContext"


from .evidence import Evidence  # noqa: E402
from .requests import RequestContext  # noqa: E402
Result.model_rebuild()
