# Current FF-04 execution checkpoint — 2026-11-06

Main baseline `46f64c8bae01e717ddab7dfb33c83286cd4ff5b4` includes FF-01–FF-05 core PRs #24–#28; combined offline verification was 288 passed/3 live skips. Historical sections below retain their original branch-time context.

The [first public-sample attempt](../verification/2026-11-06-first-batch.md) prepared/froze 3 cases and ran both existing source runners. Both failed before provider HTTP because this execution environment could not resolve the approved public hosts: **Photon 0 HTTP attempts, Overpass 0**. No provider payload/quality was observed. Raw runner failures remain unchanged; operational status is **environment blocked**, never source acceptance. Private labels/reference extracts remain outside git; redacted reports and hashes are linked above. ORS was not tested; sources remain disabled by this increment.

Verification: frozen models/input SHA and clean identity checks passed; focused offline 74 passed, full offline 288 passed/3 live skips; separate opt-in source tests failed as recorded. Independent evidence review found no blocking or minor findings. A zero-budget DNS/issue-code replay is retained privately.

Only next core task: rerun the frozen batch on an approved host with normal public DNS/HTTPS and one persistent quota ledger; then extend representative German strata before field acceptance. Do not replace security checks or repeat implementation of the existing runners. Consumer migration/merge/deployment status must be read from its own repository.

Resume: `Check current main and the 2026-11-06 FF-04 attempt record. Recover the owner-delivered private sample bundle, verify frozen hashes and clean source/runtime identity, ensure normal public DNS plus durable same-host quota storage, then rerun each existing public-source test within the 5/run and 50/day zero-cost caps. Preserve failures; no automatic activation, endpoint rotation or target deployment.`

# GeoIntelligenceCore project status

Updated 2026-11-05. P01–P12 have been merged into `main`, most recently P12 PR #20 at `2b656b3df0a190040d7b54c1c85afa0ebd8c226d`. The library has offline core, geometry, bounded provider adapters, configuration/templates, evidence/export, comparison and packaged consumer examples. No package publication or live provider activation is recorded here. Consumer integration status must be checked in the consumer repository; this repository does not establish whether E07 has since completed.

P12's local candidate wheel `geo_intelligence_core-0.1.0a1-py3-none-any.whl` has SHA-256 `3398d79eec5c68530c098f7ec9dc2338ea1cc743ac79b1e2f7c4baab0ffc6c3c`. P13 offline regression on synchronized source: **130 passed, 3 skipped**. The skipped tests concern Photon, ORS and Overpass live activation. The added passing budget replay is synthetic, single-process only.

P13's [provider activation record](../verification/provider-activation.md) and [first-release decision](../verification/first-release.md) state remaining gates. Each provider lacks an approved endpoint/account configuration, rights and quota evidence, predeclared consumer workload, labeled samples and live measurements. Current complete HeiGIT account terms/plan and key-specific quota are not readable in this review. These live gates remain **blocked**, and this version is suitable only for an explicitly labeled offline/preview evaluation. It is not production ready.

Population calculations A06/A08 are outside the first scope; temporal A07 waits for E01. Later E and POP work remains separately scoped. RestaurantTrafficDiagnosis owns consultant UI, case isolation and domain decisions; this library only provides geospatial facts.

## FF-02 shared-budget contract branch (2026-11-05)

Based on main `ab60d2e83502959230448da81635fce790406ed5`. FF-01 PR #24 is still
open with successful CI at the start of this task; FF-02 reuses the already-merged
Budget/HttpGateway interfaces and does not duplicate FF-01. A separate branch
adds a synthetic shared service with independent clients, run-bound budgets,
stable source quota domains, atomic 5/run + 50/source/UTC-day + zero-cost checks,
and separate shared concurrency slots. Tests distinguish client reconstruction
from actual storage restart and check slot release after success, error, timeout
and cancellation. The contract exposed a gateway gap: `BudgetUnavailable` now
returns explicit unavailable/null results before the pending attempt, without
leaking backend exception details. No public Budget signature/schema changes.

FF-02 branch verification: **22 new contract cases**, **35 focused checks passed**
(contract + HTTP policy + budget replay), and the full offline suite **170 passed,
3 opt-in live skips**, including isolated wheel/extras/sdist installations.
Independent whole-change review found no Critical/Important/Minor findings.
These are branch results, not a merged, released or activated status.

Actual durable storage, distributed locks and two real workers remain consumer
FF-05 acceptance work. No database/infrastructure, live requests, source activation,
consumer modifications or package publication are included.

## Free-first trial policy (2026-11-05)

Current low-volume trials prefer Photon demo, Private.coffee Overpass and free ORS Standard; see [provider policy](../operations/free-first-providers.md). Public services need no subscription or mandatory individual operator grant where published permission applies. Activation validation now accepts zero cost and no-key providers. Same-protocol Photon instance switching has synthetic regression coverage. These changes do not enable providers or implement measured live runners; daily shared quotas, live quality and consumer activation remain separate gates.

## Current implementation entrypoint (2026-11-05)

Baseline main `b7fb468b1122260251b5ef051a1a5fc9219e1878` includes PR #22. The [incremental trial plan](../superpowers/plans/2026-11-05-free-first-trial.md) orders FF-01 configuration, FF-02 budget integration contract, FF-03 switching regressions, FF-04 per-provider measured runners and FF-05 consumer handoff. These are planned, not implemented by the documentation update. P01–P12 are not restarted; P13 remains preflight-only. No standalone core deployment is required. Published public permission can suffice for account-free providers; ORS account/key evidence applies only to ORS. FF-05 checks existing E07 work before changing the consumer.

## FF-01 configuration branch (2026-11-05)

Based on main `ab60d2e83502959230448da81635fce790406ed5` (PR #23), the FF-01
branch adds `TrialSettings.public(...)` and `build_trial_provider(..., budget=...,
headers=...)`, reusing PhotonResolver, OverpassPlaceProvider and OrsRoutingProvider
with one gateway per instance. Construction and the example are offline.
Defaults cap each gateway at 5 attempts, concurrency 1 and zero cost; missing
ORS Authorization leaves only ORS unconfigured. Settings preserve policy/terms
and attribution references without credentials. Shared daily enforcement remains
FF-02; custom ORS switching is implemented by FF-03 and live runners by FF-04. No live requests,
provider activation, package publication or consumer changes are part of FF-01.

FF-01 verification: full offline suite **176 passed, 3 live skips**, including
clean wheel/extras/sdist installation. Focused trial/live-config/consumer suite
**45 passed**. Independent review found one structured validation-error credential
leak; its failing regression now passes for direct construction, model validation
and copying. Full suite reran after the fix. This is branch verification, not a
merged/released/live status.

## FF-03–FF-05 source branches (2026-11-05)

Explicit ORS instances and safe serving-instance provenance are implemented;
Photon/Overpass/ORS switching is verified with synthetic adapters. FF-04 replaces
three unconditional placeholder failures with measured real-adapter runners and
frozen labels/thresholds, actual-attempt accounting, persistent same-host test
quotas and sanitized reports. [Runner instructions](../verification/free-trial-measurements.md).
No approved live samples/thresholds or persistent measurement quota path were
supplied, so source quality/activation remains blocked and no live requests ran.
The [FF-05 handoff](../usage/free-trial-consumer-handoff.md) records the already
merged E07 baseline and the remaining consumer-owned storage/authorization flow.
P01–P13 are not rebuilt. No merge, release, target migration or deployment.

Combined offline verification after independent review: **221 passed, 3 live skips**.
Review corrections cover strict negative-result semantics, nullable credentials, independent Photon precision/cardinality labels, code/policy-bound reports, custom authentication/inbound settings and anonymous-key isolation.

## PR #27 matrix quality correction (2026-11-05)

Complete request cross-product labels are now required before I/O for positive and all-null matrix controls. Result cells must match that set exactly without duplicates and retain the expected per-cell status. RED regressions reproduced partial-label acceptance and unchecked extra/duplicate/status cells; focused suite 41 passed, full Python 3.12 suite 243 passed, 3 live skips. Runtime package sources are unchanged. No live calls, activation or release. PR remains stacked on #26; its target is codex/ff03-instance-switch, not main. Latest commit/CI/merge state is recorded by GitHub.

Follow-up independent review found duplicate Photon IDs could inflate candidate cardinality. Search/reverse measurements now reject duplicate IDs; both new tests were observed failing before the fix. Final full suite: 245 passed, 3 live skips. Runtime package sources remain unchanged.

Provider-scope review follow-up: Photon requires positive search and reverse cases, ORS positive route/matrix/catchments, and Overpass positive places before any HTTP. A partial capability batch cannot approve a whole provider. Synthetic complete batches exercise real adapters; incomplete Photon/ORS batches were observed passing before the fix and now block without requests. Full suite: 248 passed, 3 live skips.

Checkout verification follow-up: generated __pycache__/*.pyc files no longer make ordinary Python imports fail the clean-checkout gate. Untracked Python source and modified tracked runner files still fail verification. An isolated real Git checkout/compile regression reproduced the blocker before the fix. Full suite: 249 passed, 3 live skips.

The same source-identity regression also verifies that Git ignore rules cannot hide untracked Python source: all untracked paths are inspected, with only generated cache bytecode filtered. Final focused measurement suite: 47 passed; full suite immediately before this hardening: 249 passed, 3 live skips.

Final quality/configuration follow-up: Photon labels must be distinct, cover the minimum cardinality and include any first-ranked ID before I/O. Reports now retain complete effective settings and their canonical SHA-256 for consumer binding; settings changes cannot reuse old approval. Six Photon regressions failed before the fix. Full suite: 255 passed, 3 live skips. Runtime package source remains unchanged.

Direction/documentation review follow-up: ORS always needs a positive outbound catchment case and also an inbound case whenever catchment_inbound is enabled; either missing direction blocks before HTTP. Both missing-direction regressions failed before the fix. Obsolete provider-activation execution text has been replaced: complete approved configuration can perform live HTTP and pass measured gates, not deliberately fail as a placeholder. Full suite: 257 passed, 3 live skips.

### PR #27 blocked-report quota reconciliation
- Timeout and shared-control failure reports now preserve consumed `calls`, matching the durable ledger even when partial case diagnostics are unavailable.
- Both regression variants failed with a missing `calls` field before the fix; full offline suite: 259 passed, 3 opt-in live skips.
- This follow-up changes only runner/tests/docs; the packaged runtime and consumer wheel are unchanged. No live measurements, provider activation or deployment.
- Next: verify CI and independent review, then merge #27 into its existing `codex/ff03-instance-switch` target. Parent PRs remain separate.

### PR #27 cancellation-safe quota settlement
- Cancelling a SQLite reservation now waits for its bounded worker transaction to settle and updates the consumed count before releasing the source slot or writing a blocked report.
- A deterministic thread/event regression reproduced the stale zero count before the fix and reconciles the completed reservation against the ledger afterward.
- Full offline suite: 260 passed, 3 live skips. Runtime package remains unchanged. Next: exact-head CI and independent review, then merge to the existing target if clear.

## FF integration review (2026-11-06)

FF-01 PR #24 merged main. FF-04 PR #27 merged its FF-03 parent, not main.
Photon now attaches current-instance context before local query rejection; six
regressions first failed with the previous instance and pass after correction.
ProviderConfig authentication additions are documented with explicit unreleased
V1 compatibility/migration rules; README historical pending language corrected.
The consumer remains pinned to its reviewed wheel; this core source correction
does not silently replace that artifact or approve old measurement fingerprints.

Focused independent correction review caught the model-validation failure paths
as well; search/reverse invalid-request regressions were observed failing before
context attribution was moved ahead of request validation.

Integration verification: the focused Photon correction suite passed 31 cases;
the corrected FF-03/04 tree passed 266 tests, 3 live skips. Merging FF-02 preserves
its separate shared-budget examples/contracts and both completed plan entries;
only the plan table required manual conflict resolution. The combined suite is
verified before upload/merge. Consumer #38 remains technically blocked by the
uncompleted target schema compatibility and publication-order verification.

Combined FF-01–FF-04 tree after conflict resolution: **288 passed, 3 live skips**.
