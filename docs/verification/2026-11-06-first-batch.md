# FF-04 first bounded public-sample attempt — 2026-11-06

Measured source: main `46f64c8bae01e717ddab7dfb33c83286cd4ff5b4`.
**Execution blocked; both provider quality decisions remain unverified.**
No consumer activation, merge, target migration or deployment is performed by this increment.

## Prepared before provider I/O

- Two Photon public-landmark cases cover forward/reverse operations. A primary OSM API extract supplied object identity/coordinates/address precision; a city-operated public page cross-checked the landmark identity. Inputs and labels were frozen and hashed before either runner.
- One Overpass bounded rectangle has two primary-OSM reference restaurant records; official venue/operator pages cross-check names/address. Contributor personal metadata is stripped from retained reference material. OSM attribution/ODbL accompanies the restricted bundle.
- Inputs/real reference data stay outside git, per AGENTS.md; the source repository contains only redacted reports, hashes and this record. The private reproducibility bundle is delivered to the project owner separately.
- Local caps: 5 HTTP attempts/run, 50/protocol/UTC-day, concurrency 1, zero estimated EUR cost. Shared ledger path stays fixed between runs. No free key is needed for these two instances.

These three cases are **smoke samples**, not the six German address strata or an independently surveyed business inventory. OSM primary API versus Overpass checks upstream replication/adapter consistency; both share the underlying OSM dataset. Even a later pass of this batch alone cannot establish field readiness, representative accuracy, demand/attendance or a consumer activation approval. Small-sample latency bounds are experimental, not an SLA.

## Actual outcome

| Provider | Cases | HTTP attempts/reservations | Runner status | Operational interpretation |
| --- | ---: | ---: | --- | --- |
| Photon | 2 | 0 | failed; cases unconfigured | Environment blocked before HTTP |
| Overpass | 1 | 0 | failed; case unconfigured | Environment blocked before HTTP |

The inherited HTTP proxy could read public operator/reference webpages. The gateway's public-host DNS resolution instead raised `gaierror`; `unsafe_endpoint` was returned before budget reservation or provider HTTP. No raw provider response was received. Existing failed reports are preserved unchanged: they are not relabeled as passed. The [redacted execution summary](reports/2026-11-06-first-batch.json) separately records the environment-blocked interpretation and exact runtime/runner fingerprints.

No DNS override, fixed-IP substitution, alternate endpoint, proxy rewrite or weakened SSRF policy was used. Neither source has a successful quality/performance/budget acceptance result. A subsequent zero-budget diagnostic replay is retained in the private bundle as `network-preflight.json`; it records DNS error class/errno and gateway issue codes without addresses, credentials or runtime infrastructure identifiers. An empty, uninitialized local quota ledger is not cross-worker daily enforcement evidence; zero reservations are consistent with rejection before HTTP.

## Next reproducible action

Use the unchanged clean source commit and frozen inputs on one approved host with normal public DNS and HTTPS access to the selected endpoints. Use one stable durable same-host quota path and a private report directory; do not reset/copy ledgers to obtain extra allowance. Re-review current terms and the labeled inputs before opting in. Run the existing `test_photon_live.py` and `test_overpass_live.py` separately as documented in [runner instructions](free-trial-measurements.md). Preserve all failed runs and do not tune expectations to returned outputs.

Prepare additional urban/suburban/rural/umlaut/missing-number/ambiguous German strata before any broader quality acceptance. ORS remains a separate batch requiring its runtime secret, readable current account terms/quota and independent route/matrix/catchment labels. The user already has a key; this increment did not read GitHub variables/secrets or treat a key as quality approval.

## Public permission/reference sources checked

- https://github.com/komoot/photon/blob/master/README.md — reasonable demo use, throttling/availability caveats; no invented numeric provider quota.
- https://overpass.private.coffee/ — public free commercial use, no registration, fair-use/attribution and privacy obligations.
- https://www.openstreetmap.org/copyright — OSM data attribution and ODbL; software licence is separate.
- Public city and venue/operator identity references are retained in the private input manifest; no articles/photos are copied into this repository.

## Verification of this handoff

All three frozen request/expectation models validate and all four input hashes match. The clean measured main identity was verified. Focused measurement/identity/activation regressions: **74 passed**; full offline suite: **288 passed, 3 opt-in live skips**. Separate opt-in executions above each failed as recorded; neither result is hidden in the offline counts. Independent whole-branch evidence review found no Critical/Important/Minor issues. A zero-budget replay retains the DNS diagnostic; no reviewer or offline test can infer unobserved provider quality from these records.
