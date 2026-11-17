> This source tree includes the offline changes reviewed in PRs #41–#48. The per-PR test counts below are historical isolated results, not live-source acceptance. The source tree is not a release or deployment.

# E01 offline observation slice — 2026-11-10

First tested against GitHub main `77e888dc338bf592dfdb1ce3725fd5b7f76aebbd`
(local reconstructed source baseline `3aec618`). The E01 slice adds
`Observation`, `normalize_observation`, an additive schema and synthetic tests.
The local operation preserves source rights/evidence, zero versus missing count,
person versus visit, explicit direction/method/deduplication descriptions, and
UTC instants with a separate IANA zone. Missing counts return `unknown` and
retain their reason; invalid inputs return `invalid_input` and null data.

This is only E01's offline observation contract/normalization slice. It neither
collects data nor establishes rights, real quality, duration comparability or
attendance. A separate optional opening-hours continuation now provides
`evaluate_opening_hours` with the pinned 2.1.5 parser, explicit instant/timezone,
parser provenance, overnight/DST tests and unknown on holiday selectors, solar,
open-ended and quoted schedules. See [parser usage](../usage/opening-hours.md).
Temporal analysis integration and live sources remain unimplemented/unconfigured.
E01 and A07 are not completed. No
provider activation, consumer changes, release, merge or deployment is implied.
See [observation usage and limits](../usage/observations.md). Existing FF-04/FF-05
checkpoints below retain their historical scope and are not changed by this work.

Final Python 3.12 verification: **40 observation unit tests passed**, **79
observation + existing contract tests passed**, and the **full suite passed 348
tests with 3 opt-in live skips** (including wheel/extras/sdist installation).
Independent review found one numeric timestamp-string coercion bypass; seconds
and milliseconds string regressions reproduced it before the ISO-text validation
fix. A second independent review found nested unvalidated model instances could
bypass field checks and extreme offset dates could raise uncaught UTC overflow;
both were reproduced and fixed, with nested evidence-date coverage as well.
A further RED-to-GREEN regression prevents raw-input serializer warnings from
unvalidated model instances. Restricted non-default rights/provenance and
schema roundtrip checks pass. No known actionable review finding remains in
this slice; real collection, rights approval and field validation are absent.


# Selective MarketLens adaptation — 2026-11-09 feature branch

Built against main `77e888d` and MarketLens `e1f86ba`: optional form POST and
bounded transient retries, comparison/quality helpers, optional offline
Playwright HTML extraction, and separately invoked cited Gemini explanations.
See [usage and limitations](../usage/marketlens-adaptations.md) and
[implementation plan](../superpowers/plans/2026-11-09-marketlens-selective-port.md).

Local verification: **342 passed, 4 skipped** (three live providers and one
opt-in real Chromium check); source/wheel builds passed. Independent review
found four issues, fixed with RED-to-GREEN regressions: HTTP cleanup deadline,
malformed AI envelopes, browser context-allocation cancellation and incomplete
repeated-identity representative selection. Real Chromium launch was attempted
but blocked by process-singleton socket `EPERM`; a separate Chromium CI job is
included and passed: **6 real Chromium tests**, plus the full **342 passed / 4 skipped**
CI suite at code commit `a4eb801`. See [verification](../verification/2026-11-09-marketlens-selective-port.md).
No live AI request, provider activation, consumer pin/update, merge,
release or deployment is implied. GET remains the compatible Overpass default.
PR #41's field observations remain separate, not duplicated here.

# E03 offline input subset

The E03 branch adds strict offline OSM marker-link coordinate parsing and local GeoJSON administrative Feature import with matching provenance, explicit use rights, WGS84 CRS, scale metadata, valid bounded geometry, and a boundary-precision warning. It has synthetic tests only. No real boundary source, license, short-link resolution, provider call, consumer change, release, or production activation is claimed. E03 real-source/rights acceptance remains pending. See [input rules](../usage/inputs.md).

Opening-hours continuation verification on Python 3.12: **41 parser tests passed**,
**42 focused tests passed with the system timezone path disabled** (including
built-wheel metadata), and **392 full-suite tests passed with 3 opt-in live skips**.
The full run includes six isolated wheel/extras installs and sdist installation.
Both optional wheel hashes were verified offline, and sdist/wheel builds passed.
Independent review found and reproduced Easter-selector and unused-parser
provenance gaps; both were fixed with RED-to-GREEN regressions. The temporal
extra now pins tzdata as an IANA fallback, tested without a system timezone DB.
This is local offline verification, not remote CI, a Windows-native run, release
or live-source acceptance.


# E02 synthetic history draft — 2026-11-10

The [offline history contract](../usage/history.md) was first tested on the
reconstructed tree of main `77e888dc338bf592dfdb1ce3725fd5b7f76aebbd`.
It compares retained typed source records/metrics and method conditions, with
explicit rights, integrity, completeness and redaction checks. It cannot report
real-world closure, run a watch or notify anyone. It is not a release or deployment.

This is **partial synthetic E02 work**, not real E02 acceptance. Two legal real
snapshots, manual-confirmation history and broader typed topics remain absent;
consumer/source activation stays under the existing FF-05 gates. See the
[verification record](../verification/2026-11-10-e02-offline-history.md).

---


# E04 offline COMPANY subset

The partial E04 slice validates bounded caller-supplied company records against
explicit purpose/use rights and source provenance. Additive models preserve roles
and scoped unknown/exact/range workforce without operating-site or branch inferences.
Synthetic tests do not establish real-source rights, coverage or field acceptance.
The separate caller-supplied transport import is also available offline; live transport data, providers, consumer changes and activation remain absent.
See [contract and limitations](../operations/enrichment-sources.md).


## E04 offline transport slice — 2026-11-10

Bounded atomic caller-supplied transport facts import is implemented with synthetic
offline tests. [Contract and limits](../operations/enrichment-sources.md). Company
record import is a separate offline slice; live transport data and real-source validation remain deferred. This
does not change FF-04/FF-05 source activation or consumer settings.


# Current FF-04 execution checkpoint — 2026-11-06

The [Dresel Overpass report](../verification/reports/2026-11-06-overpass-dresel-pass.json)
now passes the unchanged public smoke gates on clean source `24a1381`, after
main `2ce0309` restored the original public inputs. One real attempt returned
`ok`; batch p95 was 1.979 s and traced peak memory 7,983,898 bytes. Explicit
activation settings corrected an inherited Private.coffee terms reference;
the initial report is preserved as diagnostic evidence. No runtime code or
frozen threshold changed. The same continuation ledger carries the owner's
12 historical Overpass attempts plus two new attempts, totaling **14/50** for
2026-11-06 UTC. Original historical run rows were unavailable, not reconstructed.

FF-04 has a narrow Dresel POI smoke pass; FF-05 activation remains blocked by
representative coverage and exact consumer package/settings/rights/storage and
rollout validation. [Completion and evidence](../verification/2026-11-06-ff04-completion.md#dresel-europe-instance-real-smoke-pass-ff-05-remains-blocked).
No consumer production configuration changed; no FF-06 was created.

## Historical checkpoints

After PR #35 merged, the existing Runner was repeated on clean `main`
`d46f0e0dcbf71ab8902763edbdbca05109f90714` with the same frozen inputs,
thresholds and persistent ledger. [Photon's Pasing/Rattelsdorf report](../verification/reports/2026-11-06-photon-main-recheck.json)
again failed quality for both Pasing cases while both Rattelsdorf cases passed;
latency, memory and budget passed. Four HTTP attempts were counted.
[Overpass's report](../verification/reports/2026-11-06-overpass-main-recheck.json)
again ended blocked at the approved 40 s deadline, with one counted attempt and
no POI quality conclusion. At this checkpoint the ledger recorded Photon 37,
Overpass 11 and ORS 16 attempts on 2026-11-06 UTC. These observations do not
change FF-05 eligibility or the consumer pin.

The [latest bounded measurements](../verification/2026-11-06-ff04-completion.md)
found a real Photon duplicate-ID quality failure in a public suburb case;
independent review rejected adapter deduplication as contrary to the frozen
quality rule, so it was reverted. The six public locations are smoke subjects,
not completed ambiguous/missing-number address strata. On clean source
`0002002a82cf48d670bc8182412f8073d4e454f5`, ORS Basic passed positive
route, directed matrix and outbound catchment smoke cases after an integral
float-second response fix. Its route-negative/field coverage and consumer
workflow remain absent. Overpass API still times out. All three remain closed
to FF-05 activation; no consumer production configuration changed.

The [root-cause follow-up](../verification/2026-11-06-ff04-root-cause-followup.md)
fixed a 5 s HTTP read timeout that contradicted the approved 40 s operation
deadline. A newly frozen, independently referenced **single-landmark Photon
smoke batch** passed search/reverse quality and resource gates in two real
requests. It does not establish the required representative German strata.
The unchanged Overpass query then exceeded 40 s, while its landing page worked
and even tiny GET/POST API queries timed out in counted probes. Its POI quality
remains unmeasured. ORS remains unmeasured. No FF-05 source activation or
consumer production change follows from this checkpoint.

The [Codex cloud proxy execution](../verification/2026-11-06-codex-cloud-proxy.md)
removed the previous local-DNS blocker with an explicit trusted
sidecar transport and a narrowly opt-in live-test socket allowance. On clean
source `74c94d842db4cb81df27da17630afda2992d7442`, the existing Runner
reserved 2 real Photon attempts (search/reverse both `ok` but frozen quality
failed) and 1 real Overpass attempt (`unavailable`, quality failed). Individual
sanitized reports retain policy, source, Runner, settings and input fingerprints.
ORS stayed unmeasured pending account-specific rights/quota and labeled inputs.
All sources remain disabled; no FF-05 activation or consumer config change.

The [new public smoke replay](../verification/2026-11-06-public-smoke-replay.md)
used clean main `d8cb37c4f261fc83f723dfec8c2943a7b6b10321` and the existing
Runner. Photon search/reverse and Overpass places each failed before provider
HTTP because this proxy-only runtime cannot resolve provider DNS locally; the
Runner recorded **0 attempts per source** and separate failed, sanitized
reports with settings digests. One separately budgeted Overpass reference lookup
timed out and consumed one daily reservation. The small public labels do not
establish representative coverage. ORS was not invoked: a ready key binding
does not establish current account quota, usage rights or independent labels.
All three sources remain disabled for FF-05; no consumer config changed.

The [current-environment preflight](../verification/2026-11-06-current-environment-preflight.md)
checked GitHub main `0e062f793da5d2428a0f00852bb8917ea0d95a92`, its
successful CI and the existing Runner's clean source identity. Python 3.12
offline tests: **288 passed, 3 opt-in live skips**. An enforced outbound policy
denied CONNECT to all three selected service hosts even after turn-scoped
network permission. The earlier frozen private inputs are absent from this
workspace. `ORS_API_KEY` is now present as a ready runtime binding, but no ORS
call or account-quota/rights check occurred. This preflight made **0 provider
HTTP attempts for each source** and generated no new FF-05 acceptance report.
Photon, Overpass and ORS remain independently unverified and disabled. The
consumer remains pinned to `27ee290a7b51e245414d18ff681603c1c99decf6`;
its PR #38 is merged, but current-main measurements would require an explicit
pin/update review before activation. Historical checkpoint text below is retained.

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


## Standalone Playground PR #53 (2026-11-17)

The local-only registry now has 31 explicit entries, including synthetic corrections, company/transport input, config preflight and historical comparison, plus fixed-response Photon/Overpass/ORS adapters, with an opt-in live switch, service-side ORS environment key, same-host persistent UTC-day quota and fixed public endpoints. Synthetic examples remain distinct from live observations. Public root functions have a CI coverage assertion; `apply_correction` uses an isolated synthetic scope/evidence fixture; consumer case authorization and reviewed evidence remain required for real records. The browser extractor remains on this branch pending the independent migration PR #52 and compatibility check. The Playground does not activate providers for a consumer or change V1 schemas.

Local verification: 617 passed, 4 opt-in skips on the full offline suite before the last fixed-sample additions; targeted Playground suite 6 passed after those additions. Final exact-head CI is required. Chromium cannot launch in this workspace due a host socket restriction; GeoWebCollector CI owns its real Chromium check. Public endpoint and ORS live calls are unverified in this workspace. Latest PR CI and merge status are authoritative on GitHub.
