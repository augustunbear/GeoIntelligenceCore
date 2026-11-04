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

## P07 stacked change — unreleased

- Add optional ORS route and directed duration matrix adapter through the bounded HTTP gateway, with explicit units and per-cell no-route status.
- Add bounded JSON POST support, synthetic provider fixtures, and offline tests; reject unsupported time conditions and unapproved legacy endpoints.
- Live ORS activation remains pending current terms, quota and rights verification; no release or schema version bump is claimed.
