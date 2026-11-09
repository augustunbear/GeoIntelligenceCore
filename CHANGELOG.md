# Changelog

## Unreleased — Photon street-only precision

- Map a named Photon highway feature with explicit `type=street` to
  street-level address precision when it has no separate street property.
  Preserve missing house numbers and avoid upgrading other feature types.
  This is an offline adapter fix, not measured address quality or activation.

## Unreleased — Photon duplicate identity guard

- Reject a Photon response that repeats the same OSM candidate identity with
  `unavailable` / `invalid_response`, preserving the frozen duplicate-ID quality
  failure rather than silently choosing one feature. Cover search, reverse,
  conflicting indexed records, same-name distinct towns and missing-number
  address mapping with offline regressions. This is a fail-closed adapter change,
  not a live quality pass or source activation.

## Unreleased — FF-04 bounded acceptance follow-up

- Investigate six public German location subjects. Preserve the Photon suburb
  duplicate-ID quality failure; revert candidate deduplication after independent
  review found it contradicted the existing acceptance rule.
- Accept integral float seconds in real ORS isochrone responses, rejecting
  fractional thresholds. The unchanged Basic route, matrix and outbound
  catchment smoke sample then passed; Overpass API remained unavailable.

## Unreleased — FF-04 measured follow-up

- Let provider response reads use the approved operation deadline while
  retaining a five-second connect/write/pool bound. The whole gateway call
  remains deadline-bound.
- Record a new independently referenced, passing Photon landmark smoke run
  without treating it as representative source acceptance. Record the unchanged
  Overpass batch's 40-second deadline failure and counted API diagnostics.

## Unreleased — FF-04 Codex cloud transport

- Add explicit trusted-proxy transport to the existing bounded gateway and
  trial factory for proxy-only managed environments. Default direct DNS/IP
  validation remains unchanged; the managed proxy must enforce destination
  safety, and the FF-04 Runner checks the selected host against Codex's
  restricted network policy before use.
- Read proxy and CA paths only at runtime. No source is activated by the
  transport change; real quality and FF-05 version/rights gates remain separate.

## Unreleased — FF-01

- Add explicit free-only `TrialSettings` presets and `build_trial_provider` over
  the existing Photon, Overpass and ORS adapters; construction is offline.
- Keep runtime authentication outside settings, isolate per-instance gateways,
  and enforce a local run cap in addition to the injected shared Budget.
- Add an always-dry-run example and synthetic factory contracts. Daily persistent
  budgets, custom ORS switching and live quality remain pending.

## P12 consumer packaging candidate — unreleased

- Export the public consumer facade and exercise manual confirmation, all three synthetic templates, disabled population, comparison, snapshot and JSON export through it.
- Add a saved v1 result-envelope fixture, clean Python 3.12 wheel and sdist installs for the core and optional extras, offline no-key execution, archive marker checks, MapLibre GeoJSON integration guidance, and observed dependency inventory/audit.
- No tag, PyPI release, live provider activation, downstream product integration, or schema version change is claimed.

## 0.1.0a1 — unreleased

- FF-02: add synthetic caller-owned shared-budget/slot contracts and an offline
  executable example. Add `BudgetUnavailable` and a fail-closed gateway result
  for unavailable shared reservations; existing Budget signatures and schemas
  stay unchanged. Actual durable cross-worker enforcement remains consumer work.

- Add installable Python 3.12 core and immutable Pydantic v1 target models for manual location confirmation.
- Confirm one explicitly selected candidate or manual WGS84 point offline, with provenance, result status, and incrementing location version.
- Add synthetic offline tests, package build, hashed Python 3.12 dependency lock, and CI.

This pre-release does not include search, provider adapters, geometry operations, analysis, deployment, or live source verification. No published schema migration is required yet; future breaking schema changes require a new schema version and migration notes.

## P02 stacked change — unreleased

- Add immutable versioned configuration, spatial, place, and analysis target models, five generated JSON schemas, and typed provider ports.
- Resolve explicit/profile/template precedence with allowed overrides and policy ceilings; preflight selected and required capabilities without I/O.
- Enforce purpose-specific rights checks and reject nested non-finite public model values.
- No provider adapter, analysis execution, live-data validation, release, or schema migration is claimed.

## P03 stacked change — unreleased

- Add optional Shapely/pyproj geodesic distance and bounded local circle/region overlay with explicit boundary semantics.
- Return explicit invalid/unsupported/unavailable statuses for malformed, out-of-scope and unavailable geometry operations; add synthetic offline tests and a hashed geometry dependency lock.
- No road reachability, live boundaries, provider access, release or schema migration is claimed.

## P03/P04 integration — unreleased

- Combine P03 geometry with P04 bounded HTTP, budget and cache on the P04 branch; retain both optional extras and hashed lock sets.
- Run both suites in CI. No live provider adapter, release or schema migration is claimed.

## P05/P06 integration — unreleased

- Add the optional Photon forward/reverse candidate resolver to the P06 Overpass and company-place branch. Preserve hard geographic filtering and explicit provider status; candidates require manual confirmation.
- No live provider activation, release or deployment is claimed.

## P07 integration — unreleased

- Add optional ORS walking, cycling and driving routes and directed duration matrices through bounded JSON POST. Preserve explicit distance units and per-cell no-route status.
- Live ORS activation remains pending current terms, quota and rights verification; no release or schema version bump is claimed.
## P08 stacked change — unreleased

- Add ORS time isochrones with explicit outbound/inbound capability and direction mapping, entrance selection, sorted second thresholds and bounded polygon validation.
- Preserve MultiPolygon holes and report non-nested areas as partial without repairing or substituting a circle; add synthetic offline cases.
- Add optional `CatchmentRequest.time_kind` with strict offset-aware time validation. Timed and arrival requests remain unsupported by this graph adapter. No live ORS activation or release is claimed.

## P09 analysis composition — unreleased

- Add packaged food-service profile and T-01/T-02/T-03 template definitions with explicit version references and no default catchment radius or population requirement.
- Compose selected place topics under a shared call budget after required-capability preflight. Preserve individual failure status and nullable data; static place retrieval does not establish historical occupancy or attendance.
- Extend OSM food-service mapping with restaurant, cafe, bar and fast_food category labels while preserving the existing broad category and source identity. Synthetic retail and education scenarios exercise the same core request path.
- T-03 comparison execution remains reserved for P11; no live provider quality or population capability is claimed.

## P10 evidence correction and export — unreleased

- Preserve scoped factual corrections with original records and explicit source identity checks; snapshot only purpose-authorized retained content with redaction notes and a canonical hash.
- Recheck each contributing source's export rights for deterministic JSON, CSV and GeoJSON; ship DE, ZH-CN and EN summaries, with CSV formula safeguards.
- Additive `Analysis.corrections`, `Analysis.originals` and `Snapshot.purpose` fields update the generated analysis schema. No storage authorization, public redistribution, report layout or live provider enablement is claimed.

## P11 factual location comparison — unreleased

- Add T-03 per-location analysis and explicit metric comparability: mapping, category selection, source coverage, reference period, scope type/threshold/version, boundary, method, time, unit, and measurement nature must match before a difference is reported.
- Preserve missing or incomplete cells as null with reasons. Count distinct source keys across overlapping place result sets; no population union, rank, score, or investment recommendation is produced.
- Keep comparison and derived metric outputs subject to evidence rights during retention and export. Unknown or denied rights redact values and dependent differences.

### Free-first trial configuration

- Prefer permitted public Photon/Overpass and free ORS Standard before paid or self-hosted services. Document same-protocol instance migration and remaining live-validation boundaries.
- Accept explicit zero cost and credential-free public services in the offline-tested P13 activation gate; retain required evidence and positive operational limits.
- Add synthetic Photon instance/prefix/auth switching regression coverage.

## FF-03–FF-05 source increments — unreleased

- Configurable ORS-protocol HTTPS instances with explicit authentication;
  known hosted ORS still requires Authorization. Preserve safe serving-instance
  provenance and cache isolation without relaxing DNS/SSRF checks.
- Add label-driven Photon/Overpass/ORS measured runners and sanitized, per-source
  quality/latency/memory/budget reports. Live quality remains blocked pending inputs.
- Record consumer adoption boundaries; existing SQL storage and case policy remain
  caller-owned. No deployment, live activation or release is implied.
