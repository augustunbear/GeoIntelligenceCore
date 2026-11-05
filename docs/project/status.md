# GeoIntelligenceCore project status

Updated 2026-11-05. P01–P12 have been merged into `main`, most recently P12 PR #20 at `2b656b3df0a190040d7b54c1c85afa0ebd8c226d`. The library has offline core, geometry, bounded provider adapters, configuration/templates, evidence/export, comparison and packaged consumer examples. No package publication or live provider activation is recorded here. Consumer integration status must be checked in the consumer repository; this repository does not establish whether E07 has since completed.

P12's local candidate wheel `geo_intelligence_core-0.1.0a1-py3-none-any.whl` has SHA-256 `3398d79eec5c68530c098f7ec9dc2338ea1cc743ac79b1e2f7c4baab0ffc6c3c`. P13 offline regression on synchronized source: **130 passed, 3 skipped**. The skipped tests concern Photon, ORS and Overpass live activation. The added passing budget replay is synthetic, single-process only.

P13's [provider activation record](../verification/provider-activation.md) and [first-release decision](../verification/first-release.md) state remaining gates. Each provider lacks an approved endpoint/account configuration, rights and quota evidence, predeclared consumer workload, labeled samples and live measurements. Current complete HeiGIT account terms/plan and key-specific quota are not readable in this review. These live gates remain **blocked**, and this version is suitable only for an explicitly labeled offline/preview evaluation. It is not production ready.

Population calculations A06/A08 are outside the first scope; temporal A07 waits for E01. Later E and POP work remains separately scoped. RestaurantTrafficDiagnosis owns consultant UI, case isolation and domain decisions; this library only provides geospatial facts.

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
FF-02, custom ORS switching FF-03, live measurements FF-04. No live requests,
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
