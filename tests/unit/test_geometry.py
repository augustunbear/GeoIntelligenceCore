"""Offline geometry acceptance cases, using only synthetic coordinates."""
import pytest

from geo_intelligence_core.geometry import circle, combine, distance_m, point_in_region
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.spatial import CircleRequest, GeometryLimits, Region, SpatialOperation


LIMITS = GeometryLimits(max_area_m2=1_000_000_000.0, max_vertices=500)


def region(coords, name="synthetic", rule="point_covers"):
    return Region(id=name, version="v1", geometry={"type": "Polygon", "coordinates": [coords]},
                  method="synthetic_boundary", source_ref="synthetic:v1", boundary_rule=rule)


def test_geodesic():
    a, b = Point(longitude=0, latitude=0), Point(longitude=1, latitude=0)
    assert distance_m(a, b) == pytest.approx(111_319.49, abs=1)
    assert distance_m(a, a) == 0


def test_boundary():
    square = region([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])
    edge = Point(longitude=0, latitude=0.005)
    assert point_in_region(edge, square) is True
    assert point_in_region(edge, square.model_copy(update={"boundary_rule": "point_within"})) is False


def test_union():
    # Equatorial equal-area projected squares have areas 4 and overlap 2 m².
    from pyproj import Transformer
    tx = Transformer.from_crs(6933, 4326, always_xy=True)
    def square(x):
        return region([tx.transform(*p) for p in [(x, 0), (x+2, 0), (x+2, 2), (x, 2), (x, 0)]], str(x))
    result = combine([square(0), square(1)], SpatialOperation(kind="union"), limits=LIMITS)
    assert result.status == Status.ok
    from shapely import transform
    from shapely.geometry import shape
    back = Transformer.from_crs(4326, 6933, always_xy=True)
    assert transform(shape(result.data.geometry), back.transform, interleaved=False).area == pytest.approx(6, abs=1e-5)


def test_invalid_or_unsupported():
    bowtie = region([(0, 0), (0.01, 0.01), (0, 0.01), (0.01, 0), (0, 0)])
    antimeridian = region([(179, 0), (-179, 0), (-179, 1), (179, 1), (179, 0)])
    polar = region([(0, 81), (1, 81), (1, 82), (0, 82), (0, 81)])
    small = region([(0, 0), (.01, 0), (.01, .01), (0, .01), (0, 0)])
    op = SpatialOperation(kind="union")
    assert combine([bowtie], op, limits=LIMITS).status == Status.invalid_input
    assert combine([antimeridian], op, limits=LIMITS).status == Status.unsupported
    assert combine([polar], op, limits=LIMITS).status == Status.unsupported
    assert combine([small], op, limits=GeometryLimits(max_area_m2=1.0, max_vertices=100)).status == Status.invalid_input
    assert combine([small], op, limits=GeometryLimits(max_area_m2=1e9, max_vertices=4)).status == Status.invalid_input
    assert combine([small, small], op, limits=GeometryLimits(max_area_m2=1e9, max_vertices=9)).status == Status.invalid_input


def test_circle():
    center = Point(longitude=11, latitude=49)
    result = circle(CircleRequest(center=center, radius_m=1000.0), limits=LIMITS)
    assert result.status == Status.ok
    assert result.data.method == "geodesic_straight_line_circle"
    vertices = result.data.geometry["coordinates"][0][:-1]
    assert all(abs(distance_m(center, Point(longitude=p[0], latitude=p[1])) - 1000) <= 1 for p in vertices)
    assert result.data.geometry["type"] == "Polygon"
    assert circle(CircleRequest(center=center, radius_m=1000.0), limits=GeometryLimits(max_area_m2=1.0, max_vertices=500)).status == Status.invalid_input


def test_holes_difference_and_empty_result():
    outer = region([(0, 0), (.03, 0), (.03, .03), (0, .03), (0, 0)], "outer")
    inner = region([(.01, .01), (.02, .01), (.02, .02), (.01, .02), (.01, .01)], "inner")
    result = combine([outer, inner], SpatialOperation(kind="difference"), limits=LIMITS)
    assert result.status == Status.ok
    assert len(result.data.geometry["coordinates"]) == 2
    assert point_in_region(Point(longitude=.015, latitude=.015), result.data) is False
    empty = combine([inner, outer], SpatialOperation(kind="difference"), limits=LIMITS)
    assert empty.status == Status.no_results and empty.data is None
