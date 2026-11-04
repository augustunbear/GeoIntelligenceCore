# Agent / contributor instructions

## Source of truth
- This repository is the SSOT for GeoIntelligenceCore. Check current branches, commits, open PRs, README, ADRs, status and relevant contracts before changing code.
- Do not silently import RestaurantTrafficDiagnosis domain assumptions or private credentials. Its repository is a consumer, not the owner of generic core contracts.
- Maintain an independent library, with semantic versions, changelog, explicit migration/deprecation policy, and consumer contract tests.

## Scope and implementation
- Provide domain-neutral location resolution, catchments, POI discovery, region statistics and reproducible provenance; never infer restaurant attendance, causation or arbitrary scoring.
- Prefer established open-source packages or permitted provider APIs over reimplementing GIS algorithms. Depend on pinned, audited versions; do not vendor upstream code absent compelling need.
- Keep core Python package installable without external API keys, database, cloud account or running services.
- Provider adapters optional and replaceable. Fail with explicit statuses: disabled/unconfigured/rate_limited/unavailable/unknown, never silently treat missing as zero.
- Preserve CRS, units, boundary semantics, timestamp, query method, dataset vintage, rights and attribution. Separate measured, derived, estimated and unverified results.
- No credential or commercial geodata in git fixtures. Use synthetic locations for tests.
- Third-party code licenses and third-party data licenses are separate. Do not assert that a provider permits commercial caching or redistribution without evidence.

## Quality gate
- TDD where behavior changes; deterministic fixtures, offline unit tests, contract schema validation, integration tests using opt-in provider credentials, rate-limit handling, geospatial edge cases and independent review.
- Avoid breaking public schemas; bump version when necessary. Consumer security and case-level authorization remain consumer responsibility unless this repo operates an authenticated service.
- Keep status accurate: documentation is not implementation, CI is not deployment, mock result is not live data.
- Use feature branches and PR reviews for subsequent work; do not merge to main or deploy without explicit authorization.
