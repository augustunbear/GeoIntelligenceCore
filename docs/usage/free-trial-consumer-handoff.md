# FF-05 free-source consumer handoff

RestaurantTrafficDiagnosis development was checked at
`1bd11719ec24204359a6fc180890317adf2c3dcb`: E07's case-scoped location confirmation,
offline preview and historical snapshots already exist. Do not rebuild them.

The remaining consumer increment uses `TrialSettings` / `build_trial_provider`,
the unchanged Budget port and the FF-04 sanitized measurement report. Pin the
exact source commit and wheel SHA in the consumer's `vendor/geo-source.json` and
`vendor/geo-wheel.sha256`; do not copy core sources or infer release status from
alpha version `0.1.0a1`. FF-01 PR #24 and FF-02 PR #25 remain explicit dependencies;
FF-03 and FF-04 are uploaded as stacked feature increments, without merging main.

| Responsibility | Delivery / acceptance boundary |
| --- | --- |
| Core | Same-protocol explicit instances, isolated runtime headers, bounded HTTP, safe source provenance, typed storage-failure result, label-driven measured runners. |
| Consumer | Explicit address submit, manual candidate confirmation, case/actor-scoped request IDs, durable SQL counters, source-wide concurrency, reviewed source configuration, rights, three-language notices, retained history. |
| Consumer database | Additive migration 0007 extends the existing database; no separate geo database/service is introduced. The target database still needs a controlled migration before deployment. |
| Live activation | Enable each source independently only with a matching passed report for the exact instance/endpoint/core commit, frozen sample/threshold hashes and explicit internal use/retention/display rights. ORS missing a key does not block other sources. |

The consumer increment supplies the existing PostgreSQL database with atomic
5-attempt logical-run and 50-attempt source/UTC-day counters and connection-owned
source advisory locks; SQLite fixtures use file-backed transactions/OS locks.
Credentials and instance aliases never form new quota domains. Stable request IDs
deduplicate repeated submits, returning saved operation results without spending
again. Failed/in-progress/indeterminate operations never fabricate an empty fact
or refund attempts. Population remains disabled. Historical evidence is not
rewritten when settings or instances change.

Real-source measurement is **blocked**: no approved representative sample and
threshold files/persistent runner quota location were supplied in this session.
No provider was contacted, no source is enabled by default, no production database
is changed and no deployment is performed. The consumer can adopt the code and
run isolated tests now; field quality and target-environment rollout remain
separate evidence gates. ORS keys must remain runtime secrets, not report/config
contents. A key in GitHub does not itself configure a running web process.

The library's synthetic tests are not consumer persistence proof. See the
consumer's FF-05 PR and status record for actual SQL/process/browser/CI evidence.
Keep Neon/cloud target validation distinct from disposable PostgreSQL CI results.

Pinned consumer runtime candidate (PR #38 head below): core commit `27ee290a7b51e245414d18ff681603c1c99decf6`
([FF-04 PR #27](https://github.com/augustunbear/GeoIntelligenceCore/pull/27));
wheel SHA-256 `e722028af51030cf3408a9ffe5b550fc2dc203bb21a22c55f8044b766e1cf314`,
package fingerprint `c638904f363336bbbe912168c0d61877b68d2698d5bbce749648c46a5dca652c`.
The wheel is vendored in the consumer PR, not published to a package registry.

Review corrections preserve approved Photon evidence alongside separate human
confirmation, immutable location source context and attribution; approved area
limits also constrain the radius menu and server validation. Empty results remain
explicit rather than inheriting a successful orchestration status. Migration
0007 preserves older candidates with empty evidence/context defaults.

## Verified consumer evidence (2026-11-06)

[RestaurantTrafficDiagnosis PR #38](https://github.com/augustunbear/RestaurantTrafficDiagnosis/pull/38)
head `53ffdcef24714acd338f0852a7a300944c4dac5b` contains the increment and follow-up rights,
export, provenance, PostgreSQL audit and idempotency corrections. Its exact-head
[CI run 42110668016](https://github.com/augustunbear/RestaurantTrafficDiagnosis/actions/runs/42110668016)
passed, including Chromium desktop/mobile and PostgreSQL 17 checks. See its
[status record at that commit](https://github.com/augustunbear/RestaurantTrafficDiagnosis/blob/53ffdcef24714acd338f0852a7a300944c4dac5b/docs/project/status.md).

Target schema compatibility and publication ordering remain an uncompleted consumer rollout gate. Keep the consumer PR open until controlled migration and release-order verification are complete, or automatic publication is confirmed disabled. Merge authorization alone is not evidence of schema compatibility. No target migration, deployment or live-source activation is claimed.

## FF-04 field measurement checkpoint (2026-11-06)

[The first public sample record](../verification/2026-11-06-first-batch.md) and its
[redacted reports](../verification/reports/2026-11-06-first-batch.json) belong to
core main `46f64c8bae01e717ddab7dfb33c83286cd4ff5b4` (package `0.1.0a1`,
code SHA-256 `f19d31c1ac93e712d468e1d21d8f1bad330ac859599657aa43d0dd7d863280a4`,
runner SHA-256 `fe9c02be832cdf250f67bc3b48255ea02be8ff9e4480e627d58b129fadadd2bc`).
These are actual runner invocations with **zero provider HTTP attempts**:
Photon search/reverse and Overpass places returned `unconfigured` because
public-host DNS failed before reservation. Their quality and budget gates failed;
there is no accepted provider data or representative German field result.
ORS was not run and its runtime key is unavailable here.

The consumer's fixed wheel derives from `27ee290a7b51e245414d18ff681603c1c99decf6`
with wheel SHA-256 `e722028af51030cf3408a9ffe5b550fc2dc203bb21a22c55f8044b766e1cf314`.
The new source commit and code fingerprint are **not** that pinned consumer
artifact. No FF-05 activation report matches its exact source commit, wheel,
instance, settings and frozen input hashes. Even a successful replay of the
current main report would require a deliberate consumer version update and
consumer regression/target-rollout checks; it cannot automatically authorize
that wheel. Do not alter RestaurantTrafficDiagnosis production configuration.

For each source, replay the frozen inputs on an approved host with normal public
DNS/HTTPS, one persistent same-host quota ledger and the exact clean core source
selected for the consumer. Keep the existing 5/run, 50/source/UTC-day, concurrency
1 and zero-cost caps. Review the independently labeled quality thresholds before
HTTP and retain `samples_sha256`, `thresholds_sha256`, `settings_sha256`, source
commit, code/runner fingerprints, instance/endpoint, timestamps and rights/quota
references. Extend the German address strata and independently surveyed POI
references before field acceptance. ORS needs its runtime secret, verified account
quota/terms, and separate route, directed matrix and catchment labels. A failed or
blocked source stays disabled while other sources can be evaluated independently.
