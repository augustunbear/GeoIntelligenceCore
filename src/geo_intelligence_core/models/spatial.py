"""Typed spatial data; geometric computations belong to P03."""
from datetime import datetime
from typing import Literal
from pydantic import Field, StrictFloat, StrictInt
from .common import FrozenModel
from .location import Location, Point


class Region(FrozenModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    geometry: dict[str, object]
    method: str = Field(min_length=1)
    source_ref: str | None = None
    boundary_rule: Literal['point_covers', 'point_within', 'geometry_intersects'] = 'point_covers'


class GeometryLimits(FrozenModel):
    max_area_m2: StrictFloat = Field(gt=0)
    max_vertices: StrictInt = Field(gt=0)


class CircleRequest(FrozenModel):
    center: Point
    radius_m: StrictFloat = Field(gt=0)


class SpatialOperation(FrozenModel):
    kind: Literal['union', 'intersection', 'difference']


class RouteRequest(FrozenModel):
    origin: Point
    destination: Point
    mode: str
    time: datetime | None = None
    time_kind: Literal['depart_at', 'arrive_by'] = 'depart_at'


class MatrixRequest(FrozenModel):
    origins: dict[str, Point]
    destinations: dict[str, Point]
    mode: str
    time: datetime | None = None
    time_kind: Literal['depart_at', 'arrive_by'] = 'depart_at'


class CatchmentRequest(FrozenModel):
    location: Location
    entrance_id: str | None = None
    direction: Literal['outbound', 'inbound']
    mode: str
    durations_s: tuple[StrictInt, ...]
    time: datetime | None = None


class Route(FrozenModel):
    distance_m: StrictFloat = Field(ge=0)
    duration_s: StrictFloat = Field(ge=0)
    geometry: dict[str, object] | None = None
    mode: str
    origin: Point
    destination: Point


class MatrixCell(FrozenModel):
    origin_id: str
    destination_id: str
    duration_s: StrictFloat | None = None
    status: str


class TravelMatrix(FrozenModel):
    cells: tuple[MatrixCell, ...]


class Catchment(FrozenModel):
    region: Region
    direction: Literal['outbound', 'inbound']
    mode: str
    duration_s: StrictInt
    time: datetime | None = None
