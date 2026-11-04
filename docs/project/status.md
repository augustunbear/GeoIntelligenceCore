# GeoIntelligenceCore project status

Updated: 2026-11-04.

- **Decision confirmed**: independent shared private repository `augustunbear/GeoIntelligenceCore`, separate from RestaurantTrafficDiagnosis.
- **Delivered**: initial documentation-only foundation: README, contributor instructions, architecture, ADR, open-source inventory, provider/data handling policy, draft contract, roadmap.
- **Not delivered**: Python package, source code integrations, runtime GIS APIs, CI, tests, releases, hosted infrastructure or consumer wiring. Do not claim otherwise.
- **Known risks**: German address match and POI coverage unverified; public OSM API operational restrictions; commercial geodata redistribution; PostGIS availability in target Neon not checked; census grids are historical.
- **Design baseline in this branch**: complete functional design F-01–F-13, shared rules G-01–G-10, food-service templates T-01–T-03, cross-industry scenarios V-01–V-08, ADR-0002 and planning handoff. This describes intended behavior, not implemented functionality.
- **Next task**: use docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md to generate a step-by-step implementation plan; map every requirement to an acceptance scenario and explicitly scoped work item. Reconcile the earlier roadmap and contract draft. Verify providers and rights before adopting them; do not start implementation merely because design documents exist.
- **Consumer boundary**: RestaurantTrafficDiagnosis retains consultant UI, case isolation, domain-specific reasons and evidence approval. GeoIntelligenceCore provides geospatial facts only.

## Open-source selection research (2026-11-04, this branch)

- Recorded 31 candidate projects, source-backed per-function selections, ADR-0003 and integration blueprint A01–A11.
- New findings: HeiGIT routing hostname migration; current ORS forum evidence says CC-BY-SA 4.0; OTP legacy TravelTime removal; R5py uses a paired JAR and emits isochrone lines.
- Research is desk verification only. No install, live-data quality benchmark, performance test, complete security scan or deployment has been performed.
- Current full ORS account terms/quotas were not readable through retrieval. Production activation requires those records and a permitted endpoint; no unlimited public-service dependency is approved.
- Next: generate detailed implementation steps using F/G/T/V requirements and A01–A11 gates, not a new unbounded library survey.
