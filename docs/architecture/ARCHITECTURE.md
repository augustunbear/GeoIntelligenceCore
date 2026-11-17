# Architecture and module boundaries (proposal)

## Functional boundaries added by design review

See [ADR-0002](adr/ADR-0002-generic-core-industry-profiles.md) and [functional design](../design/FUNCTIONAL_DESIGN.md). The core is industry-neutral. Optional industry profiles define categories and defaults; independently versioned use-case templates compose capabilities. Effective parameters, provenance and versions remain visible. No silent semantic fallback or domain scoring. UI, durable storage, case permissions, scheduling and notifications remain consumer responsibilities; snapshot comparison is a core capability, not an authorization to operate a monitoring service. The package layout below is an earlier proposal. For current file ownership and implementation order, use [the implementation plan](../superpowers/plans/2026-11-04-core-implementation.md) and [target contract](../contracts/V1_CONTRACT.md); neither is implemented.

## Delivery
`geo_intelligence_core` shall be a Python package with `pyproject.toml` and typed public interfaces. Include an opt-in JavaScript mapping integration example, but map UI and identity belong to consumers. Later, optional authenticated FastAPI façade reuses the exact same application services; no HTTP service is required for initial delivery.

```text
Consumer A / Consumer B / future service
              |
      versioned Python API
              |
   Core domain models, validation, provenance
      |           |           |
 Geocoding    Catchments    POI / statistics
      |           |           |
    Provider ports and optional adapters
      |           |           |
 Photon/..    Routing/...  OSM/Zensus/...
```

## Bounded responsibilities
- **Location**: normalized independent coordinates/address candidates, confidence and manual verification; WGS84 point and stable provider references.
- **Geocode**: forward/reverse suggestions, localized queries, bounded search, candidate selection. A provider's `place_id` is not a universal ID.
- **Catchment**: Euclidean/geodesic circles, walking/driving/cycling isochrones, network parameters and confidence; geodesic circle != reachable area.
- **Places**: canonical facility categories, provider-specific tags, geographic spatial filtering, potentially duplicate matches; classification != competitor judgment.
- **Statistics**: aggregate documented census polygons/grids against target geometry; spatial allocation method and dataset reference year mandatory.
- **Evidence/provenance**: provenance at each result, source URI, observed/valid/retrieved time, provider license, attribution, quality tier, algorithm version, freshness, sampling/coverage caveat.

## Package layout: target, not yet created
```text
src/geo_intelligence_core/
  __init__.py
  contracts.py
  geometry.py
  geocoding.py
  places.py
  catchments.py
  statistics.py
  provenance.py
  providers/
    photon.py
    osm_overpass.py
    routing.py
    zensus_files.py
tests/{unit,contract,integration}/
examples/{python,fastapi,maplibre}/
```
Create files only alongside tested implementations; do not scaffold inert folders or claim a running feature.

## State and storage
Default computation package has **no mandatory database**. Application owns tenant/location/case data and persistence. Optional PostGIS adapter adds spatial index at scale after Neon extension support is tested. Dataset snapshots / large rasters and grids live in explicitly licensed object storage, never bundled into source control. Cache only where provider terms permit; cache key includes source, version, locale, query bounds, algorithm and time.

## Safety and interface robustness
Validate coordinates (lat -90..90; lon -180..180), geometry validity, maximum geographic bounds, units, known CRS, rate limits, SSRF/URL allowlisting, timeouts, and input size. Store time zone separately from UTC event timestamps where useful. Do not leak street addresses to third-party geocoders without explicit project policy. Retry idempotent reads with bounded backoff, never mask incomplete outcomes. API keys server-side only.

## Lifecycle
Prototype -> offline-tested package -> contract-tested pre-release -> tagged release -> pinned consumer integration -> optional shared hosted API once operational evidence justifies it. Compatibility: explicit semver, JSON `schema_version`, changelog, consumer fixtures and deprecation window.

## Consumer integration
RestaurantTrafficDiagnosis should retain `area_research` business orchestration, case/sources/diagnosis ownership and approval. It calls package APIs and converts neutral evidence to application evidence; no `restaurant_id` or customer scoring inside Geo core. GastroPreisRadar may share search and distances while retaining prices and their evidence model.

## Browser automation boundary (ADR-0004; accepted 2026-11-17)

Browser execution, Playwright, website discovery, menu/page extraction and website-specific scraping are outside the GeoIntelligenceCore boundary. Consumers or independent collectors may supply structured facts with explicit source, retrieval time, rights, attribution and verification status. Core geospatial provider adapters remain replaceable and must use permitted sources; Google Maps web scraping is not a substitute for an authorized API. AI webpage interpretation is likewise not a prerequisite for core geospatial analysis. See [ADR-0004](adr/ADR-0004-browser-automation-outside-core.md).

The existing optional `providers.browser` and `[browser]` extra are historical implementation that still requires a separate compatibility-reviewed migration PR. This ADR does not claim code removal.
