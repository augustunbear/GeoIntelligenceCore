"""Versioned, industry-neutral selection and effective configuration."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal
from pydantic import Field, StrictBool, StrictInt, StrictFloat, field_validator, model_validator
from .common import FrozenModel
from .evidence import utc
from .location import Location
from .spatial import Region

Language = Literal['de', 'zh-CN', 'en']


class TimeCondition(FrozenModel):
    kind: Literal['depart_at', 'arrive_by', 'interval', 'descriptive']
    instant: datetime | None = None
    start: datetime | None = None
    end: datetime | None = None
    timezone: str | None = None
    label: str | None = None

    @field_validator('instant', 'start', 'end', mode='before')
    @classmethod
    def explicit_instant(cls, value):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Pydantic otherwise interprets numeric strings as Unix timestamps.
            try:
                return datetime.fromisoformat(value[:-1] + 'Z' if value.endswith('z') else value)
            except ValueError as exc:
                raise ValueError('time must be an ISO-8601 instant with offset') from exc
        raise ValueError('time must be an ISO-8601 instant with offset')

    @model_validator(mode='after')
    def validate_time(self):
        for key in ('instant', 'start', 'end'):
            value = getattr(self, key)
            if value is not None:
                try:
                    object.__setattr__(self, key, utc(value))
                except OverflowError as exc:
                    raise ValueError('time outside supported UTC range') from exc
        if self.kind in ('depart_at', 'arrive_by') and self.instant is None:
            raise ValueError('instant required')
        if self.kind == 'interval' and (self.start is None or self.end is None or self.start >= self.end):
            raise ValueError('valid interval required')
        if self.kind != 'descriptive' and not self.timezone:
            raise ValueError('IANA timezone required')
        if self.timezone:
            try:
                ZoneInfo(self.timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError('invalid IANA timezone') from exc
        return self


class TopicSelection(FrozenModel):
    id: str = Field(min_length=1)
    required: StrictBool = False


class Profile(FrozenModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    category_ids: tuple[str, ...] = ()
    defaults: dict[str, object] = Field(default_factory=dict)
    display_groups: dict[str, tuple[str, ...]] = Field(default_factory=dict)


class Template(FrozenModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    profile_ref: str | None = None
    required_inputs: tuple[str, ...] = ()
    required_topics: tuple[str, ...] = ()
    optional_topics: tuple[str, ...] = ()
    defaults: dict[str, object] = Field(default_factory=dict)


class AnalyzeRequest(FrozenModel):
    locations: tuple[Location, ...] = ()
    topics: tuple[TopicSelection, ...]
    regions: tuple[Region, ...] = ()
    time: TimeCondition | None = None
    explicit_parameters: dict[str, object] = Field(default_factory=dict)
    profile_ref: str | None = None
    template_ref: str | None = None
    scope_token: str | None = None
    request_id: str | None = None


class EffectiveConfig(FrozenModel):
    values: dict[str, object]
    provenance_by_field: dict[str, Literal['profile', 'template', 'request']]
    profile_ref: str | None = None
    template_ref: str | None = None
