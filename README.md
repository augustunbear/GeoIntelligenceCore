# GeoIntelligenceCore

Reusable, provider-neutral geospatial intelligence foundation for multiple products. **Status: P01 and P02 implementation PRs open (2026-11-04); offline core and configuration preflight are under review. No release, deployment, live-data provider or analysis execution has been delivered.**

## Mission / 定位

Turn an independently verified location into traceable spatial facts: geocoding, catchments, nearby places and infrastructure, area-level statistics, source attribution, and quality indicators. GeoIntelligenceCore must **not** decide restaurant business causes or invent customer counts. Domain applications interpret the evidence.

First potential consumer: [RestaurantTrafficDiagnosis](https://github.com/augustunbear/RestaurantTrafficDiagnosis) (consultant-assisted low restaurant traffic diagnosis); other potential consumers include GastroPreisRadar and future site-selection products. No integration is implemented yet.

## Functional design baseline / 功能设计基线

Keep the core industry-neutral; industry selection is optional. Industry profiles and use-case templates are separate, versioned concepts. Begin with a food-service profile and three templates: surroundings, venue discovery, and location comparison. Validate generality with food-service, retail and education scenarios without building all three industry products. Business causation and scoring remain consumer responsibilities.

- [完整功能设计](docs/design/FUNCTIONAL_DESIGN.md) — numbered capabilities, shared rules, templates and acceptance scenarios
- [ADR-0002](docs/architecture/adr/ADR-0002-generic-core-industry-profiles.md) — confirmed direction and review clarifications
- [分步骤实施计划](docs/superpowers/plans/2026-11-04-core-implementation.md) — 13 first-release steps, 7 follow-up work items and 3 conditional population items
- [需求追踪表](docs/plans/REQUIREMENTS_TRACEABILITY.md) — F/G/T/V/A coverage and deferred scope
- [实施规划交接](docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md) — retained planning requirements

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
- [Data and API contract](docs/contracts/V1_CONTRACT.md) — implementation-target models, Python ports and completion semantics; not implemented
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

## Delivery plan / 实施顺序

Start with P01–P04: installable offline core, location confirmation, contracts, geometry and bounded provider access. P05–P08 add Photon, Overpass and ORS adapters. P09–P11 deliver food-service templates, evidence/export and neutral comparison. P12–P13 verify packaging, consumer contracts and permitted real-source activation.

Population remains optional: administrative references only when useful and inexpensive; grid aggregation is low priority; transit population is lowest priority and excluded from the first release. No JVM/R5py solely for population. Current live endpoint terms, actual budgets and quality still require verification.

Implementation progress: P01 provides installable offline manual location confirmation in [PR #3](https://github.com/augustunbear/GeoIntelligenceCore/pull/3). P02 adds immutable configuration/result shapes, five JSON schemas and capability preflight in a stacked PR. Both are unmerged and unreleased; provider calls, analysis execution and production integration remain pending.

## P02 configuration preflight (stacked PR)

`resolve_config` applies profile and template defaults, then explicit allowed parameters, and rejects overrides above policy ceilings. `ProviderRegistry` declares configured capability ports; preflight reports selected disabled or unconfigured topics without invoking providers. `Rights.allows` requires an explicit permission and matching purpose. The five checked-in JSON schemas are generated from Pydantic models. These are contract and offline preflight features, not a working analysis pipeline.
