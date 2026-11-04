# GeoIntelligenceCore

Reusable, provider-neutral geospatial intelligence foundation for multiple products. **Status: architecture and research baseline only (2026-11-04); no functional library, API, deployment or provider integration has yet been delivered.**

## Mission / 定位

Turn an independently verified location into traceable spatial facts: geocoding, catchments, nearby places and infrastructure, area-level statistics, source attribution, and quality indicators. GeoIntelligenceCore must **not** decide restaurant business causes or invent customer counts. Domain applications interpret the evidence.

First potential consumer: [RestaurantTrafficDiagnosis](https://github.com/augustunbear/RestaurantTrafficDiagnosis) (consultant-assisted low restaurant traffic diagnosis); other potential consumers include GastroPreisRadar and future site-selection products. No integration is implemented yet.

## Functional design baseline / 功能设计基线

Keep the core industry-neutral; industry selection is optional. Industry profiles and use-case templates are separate, versioned concepts. Begin with a food-service profile and three templates: surroundings, venue discovery, and location comparison. Validate generality with food-service, retail and education scenarios without building all three industry products. Business causation and scoring remain consumer responsibilities.

- [完整功能设计](docs/design/FUNCTIONAL_DESIGN.md) — numbered capabilities, shared rules, templates and acceptance scenarios
- [ADR-0002](docs/architecture/adr/ADR-0002-generic-core-industry-profiles.md) — confirmed direction and review clarifications
- [实施规划交接](docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md) — inputs and completion criteria for the next step-by-step plan

## Open-source selection baseline

- [逐项开源选型](docs/research/OPEN_SOURCE_SELECTION.md) — all functional requirements mapped to selected tools, alternatives and source evidence
- [31 项候选核验快照](docs/research/OPEN_SOURCE_VERIFICATION_2026-11-04.md) — observed releases, maintenance and license evidence; not a tested dependency lock
- [最佳接入方案](docs/architecture/INTEGRATION_BLUEPRINT.md) — optional dependencies, data flows, adapter boundaries and A01–A11 acceptance gates
- [ADR-0003](docs/architecture/adr/ADR-0003-open-source-selection.md) — research selection baseline, with explicit production activation conditions

## Repository documentation

- [AGENTS.md](AGENTS.md) — contribution and assistant workflow rules
- [Architecture](docs/architecture/ARCHITECTURE.md) — bounded contexts, package/service delivery and deployment evolution
- [ADR-0001](docs/architecture/adr/ADR-0001-independent-shared-repository.md) — confirmed independent repository decision
- [Open-source candidates](docs/research/OPEN_SOURCE_LANDSCAPE.md) — libraries, use/avoid decisions, license and operational caveats
- [Provider strategy](docs/architecture/PROVIDERS_AND_DATA.md) — German data sources and commercial restrictions
- [Data and API contract](docs/contracts/V1_CONTRACT.md) — initial proposed JSON contract and endpoints
- [Roadmap / acceptance criteria](docs/plans/ROADMAP.md) — staged delivery and tests
- [Project status](docs/project/status.md) — completed, pending, next step

## Key decisions

1. **Separate private GitHub repository**; versioned, Python-first installable package as the initial product. Do not copy entire third-party repositories into this one.
2. Pure domain/geospatial computations and stable contracts, independently of any restaurant/consumer domain. Provider adapters can be optional; local file/manual fallback is essential.
3. No microservice, GIS database cluster, self-hosted geocoder, dedicated routing cluster, queue, or always-running infrastructure before a justified use case. An authenticated HTTP service can be introduced later without changing core contracts.
4. Provider license and provenance are **part of the data model**, not an afterthought. Public OSM, Google and routing demo infrastructure are not unlimited commercial infrastructure.
5. Unit conventions: WGS84 EPSG:4326, longitude/latitude ordering made explicit at each boundary, distances in meters, durations in seconds, timestamps UTC ISO-8601, unknown distinct from zero.
6. No personal data or keys in repository, logs or sample payloads. Cross-tenant isolation enforced by the consumer or a future authenticated service.
7. German/Chinese/English consumer-facing UI and documentation where exposed; provider-neutral API property names remain English.

## Suggested delivery (earlier outline; reconcile in next planning step)

Next task: generate a traceable step-by-step implementation plan from the functional baseline and planning handoff before starting implementation. The outline below is historical planning input, not the complete scope.

Initial milestone: installable Python package and tests; geocode/search interface (Photon candidate), validated location contract and a manually selectable map location. Next: OSM POI and transportation evidence with deduplication and source quality, walking isochrones, Zensus spatial statistics. Validate all third-party licenses, cost, and coverage before enabling a provider in paid consultation products.

**No claim of production readiness or validated operational integration is made here.**
