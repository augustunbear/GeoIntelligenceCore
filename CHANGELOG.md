# Changelog

## 0.1.0a1 — unreleased

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
