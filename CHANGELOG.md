# Changelog

## 0.1.0a1 — unreleased

- Add installable Python 3.12 core and immutable Pydantic v1 target models for manual location confirmation.
- Confirm one explicitly selected candidate or manual WGS84 point offline, with provenance, result status, and incrementing location version.
- Add synthetic offline tests, package build, hashed Python 3.12 dependency lock, and CI.

This pre-release does not include search, provider adapters, geometry operations, analysis, deployment, or live source verification. No published schema migration is required yet; future breaking schema changes require a new schema version and migration notes.
