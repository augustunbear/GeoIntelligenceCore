"""Validation of network polygons; never infer a Euclidean substitute."""
from __future__ import annotations

from .geometry import _GeometryProblem, _checked, _deps
from .models.spatial import GeometryLimits, Region


def checked_network_polygon(geometry: dict, *, limits: GeometryLimits):
    """Return a GEOS polygon after P03's coordinate, validity and policy checks."""
    geod, _, _, shape, orient_polygons, _ = _deps()
    region = Region(id='upstream', version='1', geometry=geometry,
                    method='ors_isochrone_time', source_ref='ors')
    return _checked(region, limits, geod, shape, orient_polygons)


def nesting_violations(polygons) -> bool:
    """A shorter threshold must be covered by every successive longer one."""
    return any(not outer.covers(inner) for inner, outer in zip(polygons, polygons[1:]))
