# GeoIntelligenceCore project status

Updated: 2026-11-04.

- **Decision confirmed**: independent shared private repository `augustunbear/GeoIntelligenceCore`, separate from RestaurantTrafficDiagnosis.
- **Delivered**: initial documentation-only foundation: README, contributor instructions, architecture, ADR, open-source inventory, provider/data handling policy, draft contract, roadmap.
- **Not delivered**: Python package, source code integrations, runtime GIS APIs, CI, tests, releases, hosted infrastructure or consumer wiring. Do not claim otherwise.
- **Known risks**: German address match and POI coverage unverified; public OSM API operational restrictions; commercial geodata redistribution; PostGIS availability in target Neon not checked; census grids are historical.
- **Next task**: M1 spike: verify current upstream Photon / MapLibre / GeoPandas / OSMnx versions and provider license/quotas; implement independently tested Python location/geocoding core on feature branch, then review and PR. Establish deployment/consumer contract before installing into other repos.
- **Consumer boundary**: RestaurantTrafficDiagnosis retains consultant UI, case isolation, domain-specific reasons and evidence approval. GeoIntelligenceCore provides geospatial facts only.
