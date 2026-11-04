"""Optional, offline WGS84 geometry operations. No routing semantics are implied."""
from __future__ import annotations

import math
from uuid import uuid4

from .models.common import Issue, Result, Status
from .models.location import Point
from .models.requests import RequestContext
from .models.spatial import CircleRequest, GeometryLimits, Region, SpatialOperation


class _GeometryProblem(ValueError):
    def __init__(self, status: Status, code: str):
        self.status, self.code = status, code
        super().__init__(code)


def _deps():
    try:
        from pyproj import Geod
        from shapely.geometry import Point as ShapePoint, mapping, shape
        from shapely import orient_polygons
        from shapely.ops import unary_union
    except ImportError as exc:
        raise _GeometryProblem(Status.unavailable, "geometry_extra_missing") from exc
    return Geod(ellps="WGS84"), ShapePoint, mapping, shape, orient_polygons, unary_union


def _result(status: Status, data=None, code: str | None = None):
    return Result[Region](status=status, data=data,
                          issues=(Issue(code=code, message_key=f"geometry.{code}"),) if code else (),
                          context=RequestContext(request_id=str(uuid4()), method_version="geometry-v1"))


def distance_m(a: Point, b: Point) -> float:
    """Ellipsoidal shortest distance in meters, globally for valid WGS84 points."""
    geod, *_ = _deps()
    a, b = Point.model_validate(a), Point.model_validate(b)
    return geod.inv(a.longitude, a.latitude, b.longitude, b.latitude)[2]


def _coordinates(geometry):
    if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise _GeometryProblem(Status.invalid_input, "polygon_required")
    polygons = (geometry["coordinates"],) if geometry["type"] == "Polygon" else geometry["coordinates"]
    if not polygons:
        raise _GeometryProblem(Status.invalid_input, "empty_polygon")
    total = 0
    for polygon in polygons:
        if not polygon:
            raise _GeometryProblem(Status.invalid_input, "empty_polygon")
        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise _GeometryProblem(Status.invalid_input, "invalid_ring")
            total += len(ring)
            previous = None
            for point in ring:
                if len(point) != 2 or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in point):
                    raise _GeometryProblem(Status.invalid_input, "invalid_coordinate")
                x, y = point
                if not -180 <= x <= 180 or not -90 <= y <= 90:
                    raise _GeometryProblem(Status.invalid_input, "invalid_coordinate")
                if abs(y) > 80 or (previous is not None and abs(x - previous) > 180):
                    raise _GeometryProblem(Status.unsupported, "outside_local_extent")
                previous = x
    return total


def _area(geod, polygon, orient_polygons):
    return abs(geod.geometry_area_perimeter(orient_polygons(polygon))[0])


def _checked(region, limits, geod, shape, orient_polygons):
    if region.method.lower().startswith("administrative") and not region.source_ref:
        raise _GeometryProblem(Status.invalid_input, "boundary_source_required")
    if _coordinates(region.geometry) > limits.max_vertices:
        raise _GeometryProblem(Status.invalid_input, "vertex_limit")
    try:
        geometry = shape(region.geometry)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise _GeometryProblem(Status.invalid_input, "invalid_polygon") from exc
    if geometry.is_empty or not geometry.is_valid:
        raise _GeometryProblem(Status.invalid_input, "invalid_polygon")
    if _area(geod, geometry, orient_polygons) > limits.max_area_m2:
        raise _GeometryProblem(Status.invalid_input, "area_limit")
    return geometry


def point_in_region(point: Point, region: Region) -> bool:
    """Apply the region's explicit point boundary rule (intersects includes boundary)."""
    _, ShapePoint, _, shape, _, _ = _deps()
    point, region = Point.model_validate(point), Region.model_validate(region)
    _coordinates(region.geometry)
    polygon = shape(region.geometry)
    if not polygon.is_valid:
        raise ValueError("invalid_polygon")
    p = ShapePoint(point.longitude, point.latitude)
    if region.boundary_rule == "point_within":
        return polygon.contains(p)
    return polygon.covers(p)


def circle(request: CircleRequest, *, limits: GeometryLimits) -> Result[Region]:
    """Create a local straight-line radial boundary, not a walk or drive catchment."""
    try:
        request, limits = CircleRequest.model_validate(request), GeometryLimits.model_validate(limits)
        geod, _, mapping, shape, orient_polygons, _ = _deps()
        if abs(request.center.latitude) > 80:
            raise _GeometryProblem(Status.unsupported, "outside_local_extent")
        count = 72
        if count + 1 > limits.max_vertices:
            raise _GeometryProblem(Status.invalid_input, "vertex_limit")
        if math.pi * request.radius_m**2 > limits.max_area_m2:
            raise _GeometryProblem(Status.invalid_input, "area_limit")
        coords = [geod.fwd(request.center.longitude, request.center.latitude, i * 360 / count, request.radius_m)[:2]
                  for i in range(count)]
        coords.append(coords[0])
        geojson = {"type": "Polygon", "coordinates": [coords]}
        _coordinates(geojson)
        polygon = shape(geojson)
        if not polygon.is_valid:
            raise _GeometryProblem(Status.invalid_input, "invalid_polygon")
        if _area(geod, polygon, orient_polygons) > limits.max_area_m2:
            raise _GeometryProblem(Status.invalid_input, "area_limit")
        return _result(Status.ok, Region(id=str(uuid4()), version="1", geometry=geojson,
                                          method="geodesic_straight_line_circle", boundary_rule="point_covers"))
    except _GeometryProblem as exc:
        return _result(exc.status, code=exc.code)
    except (ValueError, TypeError, OverflowError):
        return _result(Status.invalid_input, code="invalid_request")


def combine(regions: list[Region], operation: SpatialOperation, *, limits: GeometryLimits) -> Result[Region]:
    """Perform local polygon union/intersection or ordered first-minus-rest difference."""
    try:
        operation, limits = SpatialOperation.model_validate(operation), GeometryLimits.model_validate(limits)
        if not regions:
            raise _GeometryProblem(Status.invalid_input, "regions_required")
        regions = [Region.model_validate(region) for region in regions]
        rules = {region.boundary_rule for region in regions}
        if len(rules) != 1:
            raise _GeometryProblem(Status.invalid_input, "boundary_rule_mismatch")
        geod, _, mapping, shape, orient_polygons, unary_union = _deps()
        # Check the aggregate coordinate budget before GEOS overlay, not just
        # each input in isolation. Closing vertices and holes count too.
        if sum(_coordinates(region.geometry) for region in regions) > limits.max_vertices:
            raise _GeometryProblem(Status.invalid_input, "vertex_limit")
        polygons = [_checked(region, limits, geod, shape, orient_polygons) for region in regions]
        if operation.kind == "union":
            output = unary_union(polygons)
        elif operation.kind == "intersection":
            output = polygons[0]
            for polygon in polygons[1:]:
                output = output.intersection(polygon)
        else:
            output = polygons[0].difference(unary_union(polygons[1:])) if len(polygons) > 1 else polygons[0]
        if output.is_empty:
            return _result(Status.no_results)
        if output.geom_type not in ("Polygon", "MultiPolygon"):
            raise _GeometryProblem(Status.unsupported, "non_area_result")
        geojson = mapping(output)
        if _coordinates(geojson) > limits.max_vertices:
            raise _GeometryProblem(Status.invalid_input, "vertex_limit")
        if not output.is_valid:
            raise _GeometryProblem(Status.invalid_input, "invalid_polygon")
        if _area(geod, output, orient_polygons) > limits.max_area_m2:
            raise _GeometryProblem(Status.invalid_input, "area_limit")
        return _result(Status.ok, Region(id=str(uuid4()), version="1", geometry=geojson,
                                          method=f"local_{operation.kind}", boundary_rule=regions[0].boundary_rule))
    except _GeometryProblem as exc:
        return _result(exc.status, code=exc.code)
    except (ValueError, TypeError, KeyError, OverflowError):
        return _result(Status.invalid_input, code="invalid_request")
