# GeoIntelligenceCore project status

Updated: 2026-11-04.

- **Decision confirmed**: independent shared private repository `augustunbear/GeoIntelligenceCore`, separate from RestaurantTrafficDiagnosis.
- **Delivered**: initial documentation-only foundation: README, contributor instructions, architecture, ADR, open-source inventory, provider/data handling policy, draft contract, roadmap.
- **Not delivered**: Python package, source code integrations, runtime GIS APIs, CI, tests, releases, hosted infrastructure or consumer wiring. Do not claim otherwise.
- **Known risks**: German address match and POI coverage unverified; public OSM API operational restrictions; commercial geodata redistribution; PostGIS availability in target Neon not checked; census grids are historical.
- **Design baseline in this branch**: complete functional design F-01–F-13, shared rules G-01–G-10, food-service templates T-01–T-03, cross-industry scenarios V-01–V-08, ADR-0002 and planning handoff. This describes intended behavior, not implemented functionality.
- **Next task**: use docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md to generate a step-by-step implementation plan; map every requirement to an acceptance scenario and explicitly scoped work item. Reconcile the earlier roadmap and contract draft. Verify providers and rights before adopting them; do not start implementation merely because design documents exist.
- **Consumer boundary**: RestaurantTrafficDiagnosis retains consultant UI, case isolation, domain-specific reasons and evidence approval. GeoIntelligenceCore provides geospatial facts only.
