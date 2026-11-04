# V1 contract proposal — draft, not implemented

## Canonical conventions
- GeoJSON uses `[longitude, latitude]` WGS84, CRS EPSG:4326; typed Python point objects expose explicit `latitude` and `longitude`. Never silently reverse them.
- Distance meters; routing time seconds; UTC RFC3339 timestamps with offsets; IDs opaque; business-specific IDs are **outside** this package.
- Every response has `schema_version`, `status`, `provenance` and `warnings`. `null` means unknown/not measured; numeric zero is measured/confirmed zero with source.
- Suggested statuses: `ok`, `partial`, `no_results`, `not_collected`, `disabled`, `unconfigured`, `unavailable`, `rate_limited`, `invalid_input`. Provider-specific errors are mapped to typed errors and safe details.

## Example: generic nearby search output
```json
{
  "schema_version": "1.0",
  "status": "not_collected",
  "location": {"latitude": 49.4521, "longitude": 11.0767, "crs": "EPSG:4326"},
  "query": {"capability": "nearby_places", "category": "restaurant", "radius_m": 1000},
  "result": {"count": null, "places": null},
  "provenance": {
    "provider": "openstreetmap",
    "source_url": "https://www.openstreetmap.org",
    "retrieved_at": null,
    "dataset_as_of": null,
    "license": "ODbL-1.0",
    "attribution": "© OpenStreetMap contributors",
    "method": "not_run"
  },
  "warnings": ["Illustrative coordinate; no data collected"]
}
```
Illustrative coordinates are not a verified business location.

## Proposed Python ports
```python
class Geocoder(Protocol):
    async def search(self, query: str, *, language: str, near: Point | None = None) -> GeocodeResult: ...
    async def reverse(self, point: Point, *, language: str) -> GeocodeResult: ...

class PlaceProvider(Protocol):
    async def nearby(self, center: Point, radius_m: int, categories: tuple[str, ...]) -> PlacesResult: ...

class CatchmentProvider(Protocol):
    async def isochrone(self, origin: Point, mode: str, duration_s: int) -> GeometryResult: ...

class StatisticsProvider(Protocol):
    def aggregate(self, polygon: GeoJSONPolygon, dataset: DatasetRef, method: str) -> StatisticsResult: ...
```
Illustrative interfaces, not importable code. Final types and provider error contracts must be established with tests.

## Possible future REST façade (not yet authorized or implemented)
`POST /v1/geocode/search`, `POST /v1/locations/resolve`, `POST /v1/catchments`, `POST /v1/places/search`, `POST /v1/statistics/aggregate`, `GET /v1/analysis-runs/{id}`. If implemented: authenticated tenant scope, quotas, request IDs, versioning, safe logs and explicit asynchronous task lifecycle.

## Validation cases
Coordinates bounds, meter/second positive and capped, ambiguous address result, provider unavailable/rate limit, duplicate POI, 180th meridian, invalid polygons, geodesic vs projected area, partial grid overlap, censored/missing population, temporal mismatch, legal caching restrictions, same input/snapshot producing same deterministic calculation.
