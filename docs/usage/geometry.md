# Local geometry (P03)

Install `geo-intelligence-core[geometry]` to use Shapely 2.2.0 and pyproj 3.8.0. The base package imports and confirms locations without them. Geometry calls are offline; `circle` and `combine` return `unavailable` if the optional extra is missing.

```python
from geo_intelligence_core.geometry import circle, combine, distance_m, point_in_region
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.spatial import CircleRequest, GeometryLimits, SpatialOperation

limits = GeometryLimits(max_area_m2=10_000_000.0, max_vertices=500)
center = Point(longitude=11.0, latitude=49.0)
region = circle(CircleRequest(center=center, radius_m=1000.0), limits=limits).data
assert region is not None
assert point_in_region(center, region)
assert distance_m(center, Point(longitude=11.01, latitude=49.0)) > 0
```

`distance_m` is WGS84 ellipsoidal geodesic distance between global points. `circle` samples 72 geodesic bearings at the supplied radius; its polygon edges approximate a straight-line radial area. Neither operation implies walking, driving, road access, or a route duration. The output method is `geodesic_straight_line_circle`. `combine` supports union, intersection, and ordered difference (first region minus union of the rest), preserving polygon holes. A zero-area touch returns `unsupported`; an empty area returns `no_results`.

All polygons and multipolygons use GeoJSON `[longitude, latitude]` WGS84 coordinates. Rings must close and be topologically valid. Local polygon operations support latitude `[-80, 80]` and polygons whose edges do not cross the antimeridian. These limits do not constrain global point-to-point `distance_m`. Unsupported polar or antimeridian geometry returns `unsupported`; invalid/self-intersecting polygons return `invalid_input`. No convex hull, implicit topology repair, or administrative boundary download occurs. Administrative input regions need a source reference and version.

Every `circle` and `combine` invocation requires positive `GeometryLimits(max_area_m2, max_vertices)`. Circle checks estimated area before creating vertices. Combine checks all input vertex counts and geodesic areas before overlay, then checks the result. Vertex counts include closing and hole vertices. A limit violation returns `invalid_input`. A higher-level analysis must derive these limits from trusted policy ceilings; no network budget is required for direct local calls. Boundary rules: `point_covers` includes a point on an edge, `point_within` excludes it, and `geometry_intersects` includes a touching point. Combine requires equal rules across inputs.

The returned region is derived geometry. Keep the original regions and their evidence, rights, version and provenance in the calling context; a geometric overlay alone does not establish data usage rights or current administrative validity.
