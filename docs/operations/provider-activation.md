# Provider activation (P04)

For the current low-volume trial, follow the [free-first provider policy](free-first-providers.md). Public terms can establish permitted use without an individual operator approval; account details and credentials apply only where an account is required.

The provider extra offers a controlled request channel, not an enabled provider. No endpoint, token, quota, or rights grant is bundled. Record the provider's current terms and a source reference before configuring a real host.

For each activation, record the approved HTTPS origin, DNS and redirect policy, applicable public/account quota and time period, expected calls per run and per period, per-call price with currency and evidence (including documented zero for free access), total cost ceiling, concurrency, deadline, response size, allowed query paths, usage purpose, and source retention/cache rights. `UsagePolicy` needs a finite positive call limit, deadline and response byte limit, explicit cost ceiling, currency and pricing reference. `HttpGateway` also needs a per-attempt estimated price. Missing fields return `unconfigured`. No estimate means no paid request. Runtime credentials may be passed as headers; do not put them in URLs, logs, fixtures or the cache.

The gateway accepts GET queries and bounded JSON POST requests, returning JSON objects. It disables environment proxies, follows no redirects by default, checks an explicit origin allowlist, rejects IP literal/private DNS results, pins the checked address for transport, preserves the original hostname for TLS verification, and closes streamed responses after a finite byte cap. Explicit redirect permission is limited to the same origin and at most three hops; each hop is checked and charged. HTTP 429/503 retries consume another reservation and stop at the run deadline or budget. A provider-specific adapter should validate its own path and response schema. Network access is never triggered by importing the core package.

`InMemoryBudget` atomically reserves calls and estimated cost within one Python process. Multiple workers or replicas **must** inject a shared atomic Budget implementing the port and period limits before claiming an application-wide total. `max_concurrency` only limits this gateway instance. Do not silently add the counters from several processes. Real provider quota and billing consistency need separate live verification.

## FF-02 shared-budget contract

The existing `Budget` port remains unchanged:

```python
async def reserve(provider_id: str, calls: int, estimated_cost: Decimal) -> bool: ...
async def record(provider_id: str, actual_cost: Decimal) -> None: ...
```

Construct a Budget bound to a stable logical `run_id`, with all workers using the
same authoritative storage. The recommended free-trial policy is **5 HTTP attempts
per logical run across selected sources**, **50 attempts per source per UTC day**,
and **zero cost**. These are application caps, not published provider entitlements.
No daily allowance is enforced by merely setting `UsagePolicy.period_limits`.

| State / operation | Required semantics |
| --- | --- |
| Source quota domain | Application-controlled mapping from provider/instance aliases to a stable source domain. Key rotation, a new client, a worker restart or an instance alias cannot open another allowance. Unknown mappings stop requests. |
| Run counter | Shared `(application, run_id)` usage across sources, independent of UTC date. Rebuilding a Budget with the same run ID preserves usage. Repeated clicks/retries must reuse the logical run or be deduplicated by the caller. |
| Daily counter | Shared `(application, source_domain, UTC_date)` usage based on an authoritative storage clock. A new UTC day opens that day's allowance, without resetting an existing run's cap. |
| Reservation | Check both counters and the zero-cost rule, then increment both in **one atomic transaction**. Concurrent clients competing for the final slot must produce exactly one grant. Never implement separate read/check/write operations. |
| Accounting | Reserve before each outbound HTTP attempt, including retries and permitted redirect hops. Failure, timeout, cancellation and `record(0)` do not refund consumed reservations. Reject any positive price; do not raise a ceiling or fall back to paid access. |
| Storage failure | Fail closed on timeout, outage or indeterminate transaction outcome. Do not retry with local counters, delete counters or treat errors as fresh quota. An indeterminate commit may conservatively consume an attempt without sending HTTP. |

Storage adapters signal an unavailable decision with
`geo_intelligence_core.providers.budget.BudgetUnavailable`. `HttpGateway` catches
this exception around **each** reservation and returns `status='unavailable'`,
`data=null`, issue `budget_unavailable`; it does not expose exception details or
send the pending attempt. Returning `False` means quota/cost rejection and keeps
the existing `rate_limited` / `budget_exhausted` result. Translate known backend
outages into the typed exception in the caller's adapter; programming errors are
not silently swallowed. A slow reservation is still bounded by the gateway's
overall deadline. No reservation interface or saved result schema is changed.

### Shared concurrency is a separate lifecycle

The caller wraps the **whole source operation**, including HTTP streaming,
retries and cancellation cleanup, in a shared source-domain lock/semaphore with
capacity 1. Use the same domain mapping as the daily quota. Bound the wait plus
operation with a finite deadline; return an explicit unavailable/retry result
when it expires. Acquire before invoking the provider and release in `finally`.
Cancellation while waiting must not release another caller's slot. `reserve`
must not acquire a concurrency slot it has no way to release.

For a real distributed lock, implement ownership-safe release, loss-of-ownership
handling and a lease/connection lifetime that covers the entire HTTP operation.
A lease must not expire and admit another worker while the old worker continues
I/O. Consumer tests must exercise failure, timeout and process/worker lifecycle;
an in-process asyncio lock proves none of those distributed guarantees. A source
lock outage stops invocation, and reservations already consumed remain charged.
At limit or on 429/unavailability, wait/retry within policy or offer manual input;
do not rotate endpoints or credentials to evade limits. The caller owns submit
debouncing and duplicate-click prevention.

### Evidence delivered here versus caller activation

Run `PYTHONPATH=src python examples/python/shared_budget.py` with the providers
extra. This example uses a **synthetic shared service**, two separate client
objects and mocked HTTP. It demonstrates the default 50-attempt source allowance
with one remaining slot, immutable alias mapping, run-bound budgets and separate
source slots. The contract tests use an injected clock and an interleaving point
inside the atomic storage transaction; they check retries, UTC rollover,
reconstructed clients, zero-cost rejection, outages and all slot exit paths.

The example's dictionaries and asyncio locks are deliberately **not durable or
cross-process storage**. They simulate client reconstruction while one service
object survives, not a datastore restart. This PR adds no database, Redis,
infrastructure or enabled source. Before FF-05 activation the consumer must
implement the same contract using its existing durable store, then verify two
actual workers, application/process restart, atomic final-slot contention,
authoritative UTC rollover, storage/lock failures and ownership-safe release.
Do not mark actual persistent daily enforcement complete from these tests.

`Cache` is disabled by default. A caller must explicitly supply rights permitting use, retention, and cache for the same purpose. Private records require a nonempty opaque scope token in a complete key containing provider, source identity/version, language, method, path, parameters and purpose. The scope token stays internal; the consuming service authenticates and authorizes its own users. Unknown rights or missing scope deny cache storage. A prior record is retrieved only by an explicit matching key; freshness and source version selection remain the caller's responsibility. This in-memory example does not implement persistence or expiration.

All tests use synthetic HTTPX transports. They do not verify provider terms, live throughput, data quality, or real account quotas. Those remain P13 gates.
