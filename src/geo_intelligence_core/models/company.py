"""Additive caller-asserted company records, not verified operating sites."""
from typing import Literal

from pydantic import Field, StrictInt, field_validator, model_validator

from .common import FrozenModel
from .location import Address, Point


class WorkforceFact(FrozenModel):
    """One explicitly scoped source claim; no allocation or midpoint inference."""
    scope: Literal['site', 'legal_entity']
    count: StrictInt | None = Field(default=None, ge=0)
    lower: StrictInt | None = Field(default=None, ge=0)
    upper: StrictInt | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def exact_or_range(self):
        if self.count is not None:
            if self.lower is not None or self.upper is not None:
                raise ValueError('count and range are mutually exclusive')
        elif self.lower is None or self.upper is None or self.lower > self.upper:
            raise ValueError('a count or ordered complete range is required')
        return self


class ImportedCompanySite(FrozenModel):
    """Source assertions only; role never inferred from address or company name."""
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    site_role: Literal['unknown', 'registered_address', 'headquarters', 'branch', 'operating_site']
    point: Point | None = None
    address: Address | None = None
    legal_entity_ref: str | None = None
    industry: str | None = None
    workforce: WorkforceFact | None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator('id', 'source_id', 'source_ref', 'legal_entity_ref', 'industry')
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('blank text')
        return value

    @model_validator(mode='after')
    def explicit_location_and_scope(self):
        if self.point is None and (self.address is None or not any(
            isinstance(value, str) and value.strip()
            for value in self.address.model_dump().values()
        )):
            raise ValueError('a point or nonblank address is required')
        if self.workforce is not None and self.workforce.scope == 'legal_entity' and not self.legal_entity_ref:
            raise ValueError('legal entity workforce requires its entity reference')
        if any(not item.strip() for item in self.evidence_ids) or len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError('evidence references must be unique and nonblank')
        return self
