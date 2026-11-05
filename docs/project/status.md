# GeoIntelligenceCore project status

Updated 2026-11-05. P01–P12 have been merged into `main`, most recently P12 PR #20 at `2b656b3df0a190040d7b54c1c85afa0ebd8c226d`. The library has offline core, geometry, bounded provider adapters, configuration/templates, evidence/export, comparison and packaged consumer examples. No package publication or live provider activation is recorded here. Consumer integration status must be checked in the consumer repository; this repository does not establish whether E07 has since completed.

P12's local candidate wheel `geo_intelligence_core-0.1.0a1-py3-none-any.whl` has SHA-256 `3398d79eec5c68530c098f7ec9dc2338ea1cc743ac79b1e2f7c4baab0ffc6c3c`. P13 offline regression on synchronized source: **130 passed, 3 skipped**. The skipped tests concern Photon, ORS and Overpass live activation. The added passing budget replay is synthetic, single-process only.

P13's [provider activation record](../verification/provider-activation.md) and [first-release decision](../verification/first-release.md) state remaining gates. Each provider lacks an approved endpoint/account configuration, rights and quota evidence, predeclared consumer workload, labeled samples and live measurements. Current complete HeiGIT account terms/plan and key-specific quota are not readable in this review. These live gates remain **blocked**, and this version is suitable only for an explicitly labeled offline/preview evaluation. It is not production ready.

Population calculations A06/A08 are outside the first scope; temporal A07 waits for E01. Later E and POP work remains separately scoped. RestaurantTrafficDiagnosis owns consultant UI, case isolation and domain decisions; this library only provides geospatial facts.

## Free-first trial policy (2026-11-05)

Current low-volume trials prefer Photon demo, Private.coffee Overpass and free ORS Standard; see [provider policy](../operations/free-first-providers.md). Public services need no subscription or mandatory individual operator grant where published permission applies. Activation validation now accepts zero cost and no-key providers. Same-protocol Photon instance switching has synthetic regression coverage. These changes do not enable providers or implement measured live runners; daily shared quotas, live quality and consumer activation remain separate gates.

## Current implementation entrypoint (2026-11-05)

Baseline main `b7fb468b1122260251b5ef051a1a5fc9219e1878` includes PR #22. The [incremental trial plan](../superpowers/plans/2026-11-05-free-first-trial.md) orders FF-01 configuration, FF-02 budget integration contract, FF-03 switching regressions, FF-04 per-provider measured runners and FF-05 consumer handoff. These are planned, not implemented by the documentation update. P01–P12 are not restarted; P13 remains preflight-only. No standalone core deployment is required. Published public permission can suffice for account-free providers; ORS account/key evidence applies only to ORS. FF-05 checks existing E07 work before changing the consumer.
