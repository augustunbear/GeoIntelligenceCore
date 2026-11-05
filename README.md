# GeoIntelligenceCore

Reusable, provider-neutral geospatial intelligence foundation for multiple products. **Status: 0.1.0a1 source candidate under test, unreleased. Offline synthetic analysis and consumer packaging checks exist; live providers are not activated and no consumer repository is integrated.**

## Install and offline consumer example

Requires Python 3.12. Build with `python -m build`, then install the wheel from `dist/` into a clean venv. Optional extras are `geo-intelligence-core[geometry]` and `geo-intelligence-core[providers]`. No key, database, JVM or network access is needed to import the base package or run `python examples/python/offline_analysis.py`. The example confirms synthetic locations, runs the three packaged templates with a mock places port, and checks a purpose-bound snapshot and export. See [consumer integration](docs/usage/consumer-integration.md) and [release candidate checks](docs/releases/0.1.0a1.md).

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
- [Data and API contract](docs/contracts/V1_CONTRACT.md) — target models, Python ports and completion semantics
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

Implementation progress and merge status are tracked in [project status](docs/project/status.md). This source candidate does not constitute a released wheel, live source validation, or production integration.

## P02 configuration preflight (stacked PR)

`resolve_config` applies profile and template defaults, then explicit allowed parameters, and rejects overrides above policy ceilings. `ProviderRegistry` declares configured capability ports; preflight reports selected disabled or unconfigured topics without invoking providers. `Rights.allows` requires an explicit permission and matching purpose. The five checked-in JSON schemas are generated from Pydantic models. These are contract and offline preflight features, not a working analysis pipeline.

## P03 local geometry (stacked feature branch)

Install the optional `geometry` extra for offline ellipsoidal distance, explicit straight-line radial regions and local polygon overlays. Calls require independent area/vertex limits. See [geometry usage](docs/usage/geometry.md) for supported extent and boundary semantics. No road reachability or administrative data acquisition is implied.

## P04 bounded provider access (integration branch)

Install the optional `providers` extra for the HTTP gateway, atomic call/cost budget, and rights-gated cache. The gateway requires explicit endpoints and hard limits, rejects unsafe DNS and redirects, and returns typed failure statuses. See [provider activation](docs/operations/provider-activation.md). These controls do not activate a live provider or establish permission to cache its data.

## P05/P06 provider adapters (integration branch)

The configurable Photon resolver returns forward/reverse location candidates for explicit confirmation. The Overpass adapter returns bounded, mapped nearby places and unverified company sites. Both use the controlled provider gateway. See [location usage](docs/usage/location.md); no live provider has been activated.

## P07 routing (integration branch)

The optional ORS adapter provides walking, cycling and driving routes and directed duration matrices through bounded HTTP POST. See [routing usage](docs/usage/routing.md). Live activation is pending endpoint permissions, quota and rights verification.

### Selected-topic analysis (P09 preview)

`geo_intelligence_core.analyze(request, registry, policy, budget)` is an async composition entry point. Select an explicit Region or explicit radius with a confirmed location and category IDs (or the exact packaged `food-service@1` profile), register only the enabled provider ports, and set a positive `max_calls_per_run`. The packaged `surroundings@1`, `venue-discovery@1`, and `location-comparison@1` templates are exercised with synthetic data in the offline example. Static places may contain raw opening hours, but a descriptive time never establishes which venues were open or visited at that time. A disabled optional population request has null data and makes the overall result partial.

### Factual location comparison (P11)

For `location-comparison@1`, supply at least two confirmed locations, the same selected place topics, and one explicit Region per location or an explicit radius. The result includes each location's topic status and comparison rows; a difference is null unless source coverage, reference period, category mapping, scope, method, time, unit, and value are comparable. `compare(analyses, metric_ids)` also accepts analyses with explicitly supplied metrics and conditions. Distinct source keys give a factual union count for comparable place sets, not a visitor or demand estimate. Optional disabled population data stays null without blocking selected place metrics.

## Low-volume trial providers

Use the [free-first provider policy](docs/operations/free-first-providers.md): Photon and Private.coffee Overpass require no account/key; ORS Standard uses a free key. Compatible public, paid and self-hosted instances use configurable endpoints and credentials behind the same adapters. Live quality remains unverified; no paid subscription is required to install or trial the library.
