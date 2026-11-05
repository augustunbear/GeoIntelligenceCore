# Python consumer integration (preview)

Use Python 3.12 and pin the repository commit containing the tested `0.1.0a1` wheel. Install the core with `python -m pip install ./dist/geo_intelligence_core-0.1.0a1-py3-none-any.whl`; add `[geometry]` for local region operations and `[providers]` only for configured HTTP adapters. Neither extra needs a key at import time. Hashed Python 3.12 inputs are in `requirements/`; revalidate on each target platform before trusting a lock resolved elsewhere.

Run `python examples/python/offline_analysis.py` for a complete, synthetic, offline consumer. It imports only `geo_intelligence_core`, explicitly confirms two WGS84 locations, registers a mock places port and bounded budget, runs `surroundings@1`, `venue-discovery@1`, and `location-comparison@1`, then retains and exports a snapshot. The disabled optional population topic makes the first analysis `partial` and keeps its data `null`. An empty provider result is a successful *search with no retrieved records*, never proof of zero real places.

Public entry points include `confirm_location`, `analyze`, `compare`, `apply_correction`, `snapshot`, `export_result`, `load_profile`, and `load_template`. The package root exports their request/result models and `ProviderRegistry`. Specify category IDs and a Region or an explicit permitted radius. Supply the allowed capabilities and finite call budget; unconfigured or disabled topics keep their own status. Do not infer traffic, business performance, workforce, provider completeness, or a score.

Snapshots record exact version references and an explicit purpose. The consumer must check its own case authorization, scope private material, store only the permitted retained view, check `Result.status`, preserve `issues`, attribution and redactions, and use the same permitted purpose for export. `Rights.unknown` grants nothing. MapLibre guidance is in `examples/maplibre/README.md`; it does not supply a tile license, a map application, or a live source.

JSON schema `1.0` is a separate version from Python package `0.1.0a1`. Saved `tests/fixtures/consumer/result-v1.json` pins the first consumer envelope; `tests/contract/test_consumer.py` checks public imports and the roundtrip. Changes to public fields require schema/fixture and changelog review. For an incompatible published schema, issue a new schema version with migration notes. Existing alpha consumers should pin the exact git commit and test before updating; no backward compatibility across untagged alpha commits is promised.

## Shared free-trial budgets (FF-02)

Read the [shared-budget contract](../operations/provider-activation.md#ff-02-shared-budget-contract)
and run `PYTHONPATH=src python examples/python/shared_budget.py` for the synthetic
reference. The example is not an installable persistent limiter or a production
storage adapter. Use the consumer's existing storage; no new core database or
deployment is required.

Bind an implementation of the existing Budget port to the logical run ID and
inject it into every gateway for that run. The server/storage enforces the total
5-attempt run cap across sources, each source's 50-attempt UTC-day cap and zero
cost atomically. The application controls provider-to-quota-domain mappings;
all aliases/keys for the same source must share one allowance. Persist counters
across reconstructed clients and workers. Do not include credentials or a
user-controlled alias in the storage key, and do not reset usage on gateway
construction, retries, duplicate clicks or application restart.

Separately wrap the provider invocation in the caller's shared source-domain
concurrency slot (capacity 1), with a finite wait/operation deadline and ownership-
safe `finally` release. The example's `invoke_guarded` illustrates this around a
callback such as `lambda: provider.search(request, context)`; the same wrapper can
surround a route/matrix operation. Reuse the same quota domain and run-bound
budget for subsequent retries. A per-gateway semaphore alone is insufficient.

Quota/cost rejection returns `rate_limited` with `data=null`. Normalize storage
outages to `BudgetUnavailable`; the gateway returns `unavailable` with issue
`budget_unavailable` before sending another HTTP attempt. Do not display either
as zero places or a valid empty result. Preserve consumed attempts on every exit;
do not raise the zero-cost ceiling or select another endpoint automatically.

The library contract has synthetic coverage. FF-05 must verify the actual
consumer adapter with two real workers, durable application restart, UTC rollover,
lost/unavailable storage or lock, and success/error/timeout/cancellation cleanup.
Only then can the consumer claim application-wide daily enforcement. This does
not establish live provider quality or source activation.
