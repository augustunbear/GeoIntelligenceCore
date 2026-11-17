# GeoIntelligenceCore

Reusable, provider-neutral geospatial intelligence foundation for multiple products. **Status: 0.1.0a1 source candidate under test, unreleased. Offline synthetic analysis and consumer packaging checks exist; live providers are not activated here; consumer integration status is owned by each consumer repository.**

## Install and offline consumer example

Requires Python 3.12. Build with `python -m build`, then install the wheel from `dist/` into a clean venv. Optional extras are `geo-intelligence-core[geometry]`, `[providers]`, `[browser]` and `[temporal]`. No key, database, JVM or network access is needed to import the base package or run `python examples/python/offline_analysis.py`. The example confirms synthetic locations, runs the three packaged templates with a mock places port, and checks a purpose-bound snapshot and export. See [consumer integration](docs/usage/consumer-integration.md) and [release candidate checks](docs/releases/0.1.0a1.md).

## Mission / 定位

Turn an independently verified location into traceable spatial facts: geocoding, catchments, nearby places and infrastructure, area-level statistics, source attribution, and quality indicators. GeoIntelligenceCore must **not** decide restaurant business causes or invent customer counts. Domain applications interpret the evidence.

First potential consumer: [RestaurantTrafficDiagnosis](https://github.com/augustunbear/RestaurantTrafficDiagnosis) (consultant-assisted low restaurant traffic diagnosis); other potential consumers include GastroPreisRadar and future site-selection products. Check that consumer’s current fact branch for E07 integration status; this library’s tests alone do not establish it.

## Functional design baseline / 功能设计基线

Keep the core industry-neutral; industry selection is optional. Industry profiles and use-case templates are separate, versioned concepts. Begin with a food-service profile and three templates: surroundings, venue discovery, and location comparison. Validate generality with food-service, retail and education scenarios without building all three industry products. Business causation and scoring remain consumer responsibilities.

- [完整功能设计](docs/design/FUNCTIONAL_DESIGN.md) — numbered capabilities, shared rules, templates and acceptance scenarios
- [ADR-0002](docs/architecture/adr/ADR-0002-generic-core-industry-profiles.md) — confirmed direction and review clarifications
- [分步骤实施计划](docs/superpowers/plans/2026-11-04-core-implementation.md) — 13 first-release steps, 7 follow-up work items and 3 conditional population items
- [需求追踪表](docs/plans/REQUIREMENTS_TRACEABILITY.md) — F/G/T/V/A coverage and deferred scope
- [实施规划交接](docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md) — retained planning requirements

- [免费优先试用增量计划](docs/superpowers/plans/2026-11-05-free-first-trial.md) — 当前执行入口 FF-01–FF-05；不重做 P01–P13，不单独部署核心

## E03 offline inputs

Strict OpenStreetMap marker-link parsing and rights-checked local GeoJSON Feature import are available under `geo_intelligence_core.inputs`; region import requires the optional `geometry` extra. See [offline input rules](docs/usage/inputs.md). These are offline input checks only, not real boundary licensing, provider activation, or automatic location confirmation.

## E01 offline observations (partial slice)

`Observation` and `normalize_observation` validate supplied counts with explicit
spatial scope, UTC interval, IANA timezone, person/visit semantics and evidence
rights. Missing counts remain unknown, never zero. See [observation usage](docs/usage/observations.md).
No collection, observation comparison, provider activation or consumer integration is included. Optional opening-hours evaluation is a separate partial continuation; E01 remains incomplete.


## Open-source selection baseline

- [逐项开源选型](docs/research/OPEN_SOURCE_SELECTION.md) — all functional requirements mapped to selected tools, alternatives and source evidence
- [31 项候选核验快照](docs/research/OPEN_SOURCE_VERIFICATION_2026-11-04.md) — observed releases, maintenance and license evidence; not a tested dependency lock
- [最佳接入方案](docs/architecture/INTEGRATION_BLUEPRINT.md) — optional dependencies, data flows, adapter boundaries and A01–A11 acceptance gates
- [ADR-0003](docs/architecture/adr/ADR-0003-open-source-selection.md) — research selection baseline, with explicit production activation conditions

## Repository documentation

- [Selective MarketLens adaptations](docs/usage/marketlens-adaptations.md) — opt-in Overpass form POST, comparison/quality helpers, optional offline Playwright extraction and separately invoked Gemini explanations; no live activation.
- [Third-party notices](THIRD_PARTY_NOTICES.md) — selected MIT license and upstream provenance.

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

Select an instance with `TrialSettings.public(...)` and construct it with
`build_trial_provider(..., budget=...)` from `geo_intelligence_core.providers.trial`.
See the [offline dry-run example](examples/python/free_trial.py). Defaults are 5
attempts per gateway, concurrency 1 and zero cost; shared daily budgets remain
caller-owned. FF-03 implements explicit ORS custom-instance switching and
synthetic instance-isolation checks; FF-04 measured runners are implemented.
Live quality/activation remains blocked until approved measurements pass.




## Optional E01 opening-hours continuation

`evaluate_opening_hours(hours_raw, at=aware_datetime, timezone='Europe/Berlin')`
uses the pinned optional `[temporal]` parser. See [usage and limitations](docs/usage/opening-hours.md).
Holiday, solar, open-ended and quoted schedules remain unknown. This additive
offline API does not activate providers, filter places or infer attendance.



## E04 caller-supplied company records

`geo_intelligence_core.inputs.company.import_company` validates explicitly supplied company-site assertions with purpose-bound rights and scoped workforce facts. It does not infer operating sites or activate live sources. See the [company contract and limits](docs/operations/enrichment-sources.md).

## E04 caller-supplied transport facts

`geo_intelligence_core.inputs.transport.import_transport` imports a bounded batch
of explicit offline observations with purpose-bound evidence and expiry checks.
Parking capacity and free-space counts stay separate; restrictions require a
segment, direction and validity period. See the [transport contract and limits](docs/operations/enrichment-sources.md).
This does not activate live sources. Company import is separately available as a caller-supplied offline slice.

## Browser automation architecture decision

[ADR-0004](docs/architecture/adr/ADR-0004-browser-automation-outside-core.md) places Playwright, website discovery and menu/page extraction outside GeoIntelligenceCore, in consumer applications or independent collectors. The existing optional `[browser]` extra and extractor are still present in this source candidate pending a separate compatibility-reviewed migration; they are **not** the intended long-term core boundary. No browser is needed for ordinary geospatial analysis. Website-derived facts require explicit rights, provenance and verification status.

## 本地 Playground

安装 Python 3.12 后，在仓库根目录执行：

```bash
python -m pip install -e '.[geometry,providers,temporal]'
python -m geo_intelligence_core.playground
```

浏览器打开 <http://127.0.0.1:8765>。按分类选择功能，修改自带的合成示例 JSON，点击“运行测试”；结果显示状态、耗时、来源和结构化数据，可复制请求与响应。地址确认、OSM 链接、距离与区域、POI、路网、数据质量、行业配置和分析/导出都有入口。`apply_correction` 使用固定合成案件与证据测试；真实案件更正仍由消费者授权和人工审核。

默认 Provider 测试使用同一适配器的固定离线响应，不访问服务。想测试真实 Photon / Overpass / ORS 时，在**本机终端**设置 `GEO_PLAYGROUND_LIVE=1`；ORS 还需设置 `ORS_API_KEY` 环境变量，然后重启 Playground，在对应功能上勾选“本次调用真实服务”。不要把密钥填入网页。公开端点、超时与单次请求上限固定；路线端点最多相距 20 km、矩阵最多 5×5、等时线最多三档 30 分钟；本机 SQLite 配额文件默认位于 `~/.geo-playground-quota.sqlite3`，按来源每天最多 50 次尝试，失败也计入。实时结果仅是调用观察，不代表数据质量或商用权已获批准。公共端点不可用时仍可执行离线示例。

新增功能时在 `playground.py` 的显式注册表增加名称、分类、参数模型/示例和受限执行适配器。CI 的公开函数覆盖测试会发现未登记的新公开函数。Playground 只监听 `127.0.0.1`；请勿将其暴露到公网或填入私人案件数据。出现“依赖不可用”时安装对应的 optional extra；出现 ORS 未配置时检查本机环境变量；出现额度耗尽请次日再试，不要删除配额文件规避限制。
