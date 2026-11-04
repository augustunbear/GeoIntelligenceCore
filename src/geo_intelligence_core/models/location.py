"""Immutable location identities and WGS84 coordinates."""
from datetime import datetime
from typing import Literal

from pydantic import Field, StrictFloat, StrictInt, field_validator, model_validator

from .common import FrozenModel
from .evidence import utc

Coordinate = StrictFloat | StrictInt


class Point(FrozenModel):
    longitude: Coordinate = Field(ge=-180, le=180)
    latitude: Coordinate = Field(ge=-90, le=90)


class Address(FrozenModel):
    country_code: str | None = None
    postcode: str | None = None
    locality: str | None = None
    street: str | None = None
    house_number: str | None = None
    native_names: dict[str, str] = Field(default_factory=dict)


class Candidate(FrozenModel):
    id: str = Field(min_length=1)
    point: Point
    address: Address | None = None
    source_ref: str = Field(min_length=1)
    precision: str | None = None


class Entrance(FrozenModel):
    id: str = Field(min_length=1)
    point: Point
    role: str = Field(min_length=1)
    modes: tuple[str, ...] = Field(default_factory=list)


class Confirmation(FrozenModel):
    method: Literal["manual", "candidate"]
    at: datetime
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("at")
    @classmethod
    def utc_at(cls, value):
        return utc(value)

    @model_validator(mode="after")
    def unique_evidence(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or any(not e for e in self.evidence_ids):
            raise ValueError("confirmation evidence IDs must be nonempty and unique")
        return self


class Location(FrozenModel):
    id: str = Field(min_length=1)
    version: StrictInt = Field(ge=1)
    point: Point
    address: Address | None = None
    entrances: tuple[Entrance, ...] = Field(default_factory=list)
    confirmation: Confirmation
