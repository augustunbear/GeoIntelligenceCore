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
# Unreleased P05

- Added the configurable Photon API v1 forward/reverse candidate resolver with bounded query and language semantics, conservative precision, hard geographic filtering and explicit failure status.

