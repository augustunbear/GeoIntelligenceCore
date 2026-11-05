"""Provider-neutral place records; normalization belongs to P06."""
from typing import Literal
from pydantic import Field, StrictInt
from .common import FrozenModel
from .location import Address, Point
from .spatial import Region


class SourceKey(FrozenModel):
    source_id: str
    entity_type: str
    entity_id: str


class Place(FrozenModel):
    source_key: SourceKey
    native_names: dict[str, str] = Field(default_factory=dict)
    point: Point
    geometry: dict[str, object] | None = None
    point_role: str | None = None
    address: Address | None = None
    categories: tuple[str, ...] = ()
    raw_tags: dict[str, str] = Field(default_factory=dict)
    hours_raw: str | None = None
    contacts: dict[str, str] = Field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()


class PlaceQuery(FrozenModel):
    region: Region
    category_ids: tuple[str, ...]
    mapping_version: str
    boundary_rule: Literal['point_covers', 'point_within', 'geometry_intersects'] = 'point_covers'


class PlaceSet(FrozenModel):
    places: tuple[Place, ...]
    retrieved_count: StrictInt = Field(ge=0)
    unique_count: StrictInt = Field(ge=0)
    coverage: str | None = None
    duplicate_candidates: tuple[tuple[str, str], ...] = ()


class CompanySite(FrozenModel):
    place: Place
    site_role: str
    legal_entity_ref: str | None = None
    workforce: StrictInt | None = None
