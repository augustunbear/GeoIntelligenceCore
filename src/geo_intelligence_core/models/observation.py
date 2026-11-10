"""Provider-neutral count observations, without rates or comparability claims."""
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, StrictInt, field_validator, model_validator

from .common import FrozenModel
from .evidence import Evidence, utc
from .location import Point
from .spatial import Region


class Observation(FrozenModel):
    """One source-described count over an explicit spatial and temporal scope.

    Instants are offset-aware and normalized to UTC; timezone is the IANA zone
    for local display, not an instruction to reinterpret either instant.
    Direction, method and dedupe are source descriptions, not verified claims.
    Unknown deduplication must be stated explicitly, e.g. ``dedupe='unknown'``.
    """

    id: str = Field(min_length=1)
    point: Point | None = None
    region: Region | None = None
    start: datetime
    end: datetime
    timezone: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    count_object: Literal['person', 'visit']
    count: StrictInt | None = Field(default=None, ge=0)
    missing_reason: str | None = None
    method: str = Field(min_length=1)
    dedupe: str = Field(min_length=1)
    evidence: tuple[Evidence, ...] = Field(min_length=1)

    @field_validator('id', 'direction', 'method', 'dedupe', 'missing_reason')
    @classmethod
    def nonblank_description(cls, value):
        if value is not None and not value.strip():
            raise ValueError('observation descriptions must not be blank')
        return value

    @field_validator('start', 'end', mode='before')
    @classmethod
    def explicit_instant(cls, value):
        if not isinstance(value, (datetime, str)):
            raise ValueError('observation instants require datetime or offset-aware text')
        # Pydantic also accepts numeric timestamp strings; those do not carry
        # an explicit offset and are deliberately outside this contract.
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    @field_validator('start', 'end')
    @classmethod
    def utc_instant(cls, value):
        return utc(value)

    @field_validator('timezone')
    @classmethod
    def iana_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('unknown IANA timezone') from exc
        return value

    @model_validator(mode='after')
    def observation_scope(self):
        if (self.point is None) == (self.region is None):
            raise ValueError('select exactly one point or region')
        if self.end <= self.start:
            raise ValueError('observation end must be after start')
        if (self.count is None) != (self.missing_reason is not None):
            raise ValueError('missing counts require a reason; measured counts forbid one')
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError('observation evidence IDs must be unique')
        return self
