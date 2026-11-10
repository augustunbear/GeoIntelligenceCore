# MarketLens selective port verification — 2026-11-09

Base: GeoIntelligenceCore main `77e888dc338bf592dfdb1ce3725fd5b7f76aebbd`.
Upstream reviewed: MarketLens `e1f86ba7dc16b69155e624eb23a37606e8b06f28`.
Verified code commit: `a4eb80125a76308c83557f53cc47b4ac4026da6a`.
PR: https://github.com/augustunbear/GeoIntelligenceCore/pull/42
CI: https://github.com/augustunbear/GeoIntelligenceCore/actions/runs/42707243536

## Observed results

| Check | Result |
|---|---|
| Local full `python -m pytest -q` | 342 passed, 4 skipped; 73.15 s |
| CI full offline/contracts/consumer/packaging suite | 342 passed, 4 skipped; 34.07 s |
| Dedicated CI actual Playwright/Chromium suite | 6 passed; 0.87 s |
| Source distribution and wheel | Built locally and in CI |
| Wheel contents | Optional adapters and original MarketLens MIT text present |
| Default import/disabled adapter checks | No browser launch, model request or required browser dependency |

The four default-suite skips are three real-provider opt-ins and one Chromium
opt-in. The separate browser job runs that Chromium test plus lifecycle tests
with `GEO_BROWSER_TESTS=1`; it is not skipped there. Its actual Chromium check
uses synthetic HTML, confirms source scripts do not change the name, checks
blocked-resource count, and validates missing/truncated fields and evidence hash.

Local Chromium launch was attempted but the managed sandbox denied its Unix
process-singleton socket (`EPERM`). That environment failure remains recorded;
actual browser behavior was subsequently verified on the GitHub runner.

## Independent review and regression repairs

All four findings were reproduced before repair:
1. Slow HTTP stream close exceeded the operation deadline: cleanup now uses the
   same remaining deadline; a 20 ms timeout no longer waits for a 300 ms close.
2. Malformed Gemini candidate/part envelopes raised AttributeError: shape checks
   now return sanitized `unavailable / invalid_explanation`.
3. Cancellation during browser context allocation could leave an unreachable
   context: close the session when allocation ownership becomes uncertain.
   Other active work may fail; the consumer must start a new session.
4. An empty repeated source observation could suppress a usable duplicate
   candidate: prefer usable matching fields before deterministic tie-breaking.
   No observation fields are merged or declared authoritative.

Each has a passing regression. Resource-request abort counting was also added
so the real-browser test would fail if request interception were removed.

## Scope and remaining operational checks

No real Gemini generation or paid request, provider activation, production
deployment, database migration, consumer dependency update or merge occurred.
The new adapter's exact Gemini account/model/schema behavior and costs still
need explicit live acceptance before use. Browser acquisition is intentionally
outside this adapter: it processes purpose-approved HTML snapshots only.
Overpass POST is opt-in and needs its own representative live measurements;
existing GET acceptance reports are not promoted to POST acceptance.

Software adaptation selects upstream MIT and ships its full original notice.
Third-party data rights remain independent. New optional/helper APIs are additive
to the unreleased `0.1.0a1` candidate; historical release manifests stay historical.
