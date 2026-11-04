# Open-source research: candidates and integration path

> Superseded for selection decisions by [detailed selection](OPEN_SOURCE_SELECTION.md), [verification snapshot](OPEN_SOURCE_VERIFICATION_2026-11-04.md) and [integration blueprint](../architecture/INTEGRATION_BLUEPRINT.md), researched on 2026-11-04. This earlier inventory is preserved as historical research, not the final provider/endpoint/version choice.

Date: 2026-11-04. Assessment = desk review of projects and prior RestaurantTrafficDiagnosis research, **not** tested compatibility or legal opinion. Validate current version, maintenance, security, runtime, license and terms before production. External links are upstream project URLs, not vendored code.

| Candidate | Source | Function | Integration recommendation | Caveats |
|---|---|---|---|---|
| Photon | https://github.com/komoot/photon | OSM-based forward geocoder/search/autocomplete | HTTP provider adapter, hosted subject to usage terms; self-host only at scale | public instance not SLA/unlimited; search quality varies by region |
| Pelias | https://github.com/pelias/pelias | modular geocoder/autocomplete | alternative adapter | complex self-host index and services |
| MapLibre GL JS | https://github.com/maplibre/maplibre-gl-js | browser vector map and overlays | consume via front-end dependency in consumer apps | tile hosting/attribution separate |
| PostGIS | https://github.com/postgis/postgis | spatial indexing and SQL | optional persistence capability | confirm Neon extension and privileges; not required for package core |
| openrouteservice | https://github.com/GIScience/openrouteservice | isochrones and routing | remote API adapter, permission/quota review | operation of own server is costly; public plans have limits |
| OSMnx | https://github.com/gboeing/osmnx | Python OSM roads and networks | Python optional dependency for analysis/validation | resource-intensive downloads and Overpass constraints |
| Overpass API | https://github.com/drolbr/Overpass-API | OSM POI filtering/query | HTTP provider adapter with polite limits | shared public endpoints capacity/data completeness |
| GeoPandas | https://github.com/geopandas/geopandas | spatial joins, geometry overlays | Python optional dependency for grid analysis | heavy geospatial dependencies; CRS and geometry pitfalls |
| Shapely | https://github.com/shapely/shapely | local geometry operations | Python optional/core geometry library if justified | planar geometry not geodesic distances |
| pyproj | https://github.com/pyproj4/pyproj | CRS transforms | optional analytics dependency | explicit CRS transformation required |
| H3 | https://github.com/uber/h3 | hierarchical hex indexing | later only if requirements justify grid abstraction | not a source of demographic data; audit exact repo/release license |
| Valhalla | https://github.com/valhalla/valhalla | routing/isochrones | future route backend choice | avoid deploying server early |
| QGIS | https://github.com/qgis/QGIS | GIS desktop analyst workflow | manual verification/export rather than embedding | desktop footprint; application licensing implications |

## Build vs reuse
- **Reuse** geocoding, geometry algorithms, network travel-time computation, OSM querying and visualization.
- **Build** normalized provider ports, high-integrity cross-provider contracts, provenance/licensing controls, deterministic catchment aggregation, repeatable tests and consumer-agnostic quality results.
- **Do not build** own map engine, routing engine, generic BI, visitor/mobile foot-traffic prediction or inferred restaurant performance.
- Related early-stage ecosystem ideas described in [RestaurantTrafficDiagnosis research](https://github.com/augustunbear/RestaurantTrafficDiagnosis/blob/development/docs/research/2026-10-29-existing-solutions-and-reuse.md): [MarketLens](https://github.com/GipsyDanger-dev/MarketLens) and [GeoWire](https://github.com/geowire/geowire). Their production maturity, repository availability and specific claims remain unverified: compare ideas only, no copied implementation.

## Selection spikes (required before pinning packages)
1. Address autocomplete for German diacritics, street/house-number and business names, short ambiguous queries, DE/EN/ZH locale behavior, stable normalized output; manual fallback.
2. 5/10/15-minute pedestrian catchment versus Euclidean circle with railway/river barriers, routability and service quota.
3. 500m/1km facilities: dedupe same venue across different OSM ways/nodes/providers and classify without pretending all nearby restaurants compete.
4. Zensus 100m/1km population grid overlays with exact/area-weighted/centroid choices, missing/suppressed values and correct vintage.
5. Runtime footprint and cold start under current intended hosting; license and contractual ability to cache, combine, and put results in paid reports.

A passing README example is not a tested integration. Test against exact upstream release commits and record versions.
