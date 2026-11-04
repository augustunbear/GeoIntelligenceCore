"""Public result envelope and validation diagnostics."""
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenDict(dict):
    """A JSON-serializable dictionary whose keys cannot change after creation."""
    def _immutable(self, *args, **kwargs):
        raise TypeError("model collections are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


def _freeze(value):
    if isinstance(value, dict):
        return FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def freeze_collections(self):
        for name in type(self).model_fields:
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        return self

    def model_copy(self, *, update=None, deep=False):
        """Revalidate copies so supplied collections remain immutable."""
        values = {name: getattr(self, name) for name in type(self).model_fields}
        if update:
            values.update(update)
        return type(self).model_validate(values)


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
    issues: tuple[Issue, ...] = Field(default_factory=list)
    evidence: tuple["Evidence", ...] = Field(default_factory=list)
    context: "RequestContext"


from .evidence import Evidence  # noqa: E402
from .requests import RequestContext  # noqa: E402
Result.model_rebuild()
