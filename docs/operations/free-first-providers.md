# Free-first provider policy — 2026-11-05

Decision: development and controlled trials expect only a few to a few dozen user queries per day. Prefer permitted free public services, with no recurring provider subscription. Paid hosting and self-hosting are later options justified by measured quality, availability, workload or cost. GeoIntelligenceCore remains an installable library; this decision does not create a separately deployed core service.

## Initial choices and manual setup

| Capability | First trial choice / configured base URL | Account and cost | Evidence / limitation |
| --- | --- | --- | --- |
| Address search and reverse | Photon demo, `https://photon.komoot.io` | No account or key; no subscription | [Official README](https://github.com/komoot/photon): reasonable project use is permitted; extensive use may be throttled or banned; no availability guarantee or fixed quota. |
| Surrounding POIs and OSM features | Private.coffee Overpass, `https://overpass.private.coffee` | No account or key; free, donations optional | [Operator terms](https://overpass.private.coffee/): commercial use explicitly allowed, no registration, fair use and attribution required. Adapter appends `/api/interpreter`; do not put this path into the base URL. |
| Routes, matrix and isochrones | ORS Standard, `https://api.heigit.org/openrouteservice` | Free Standard account and API key | [HeiGIT portal](https://api.heigit.org/): sign up for a free Standard key. Record current dashboard quotas and applicable terms; no paid plan is required for this trial choice. |

Photon and Overpass need only operator selection and bounded configuration, not a purchase, account or individual written permission when published terms already permit the workload. For ORS, the account owner registers through the portal, verifies email if requested, selects Standard, creates a key and saves it in the consumer's secret store. Do not paste keys into a PR, issue or chat. Account verification/terms acceptance and the choice of real test addresses are the remaining owner actions; configuration and offline tests can be automated. No Google Cloud, database or paid geocoding account is required by the library.

A provider's software licence does not grant all rights to its hosted data. Preserve OSM attribution and record purpose/cache/export permissions. See the [activation record](../verification/provider-activation.md) for ORS output-licence questions. Where caching/export rights are unresolved, leave those operations disabled. This is not a claim that live quality gates have passed.

## Bounded trial profile

Recommended starting limits, **our local caps, not provider entitlements**: 50 HTTP attempts per provider per day, at most 5 attempts per run, concurrency 1, and zero estimated monetary cost (`cost_per_call=0`, `cost_ceiling=0`, explicit currency and public free-service pricing reference). A user query can generate several HTTP attempts. Adjust these caps to the observed trial workload without exceeding provider policy. Count retries and redirects. Use explicit submit or debounced search rather than a request per keystroke. Provide a meaningful application User-Agent/contact where requested by the operator.

Per-run limits already exist in `HttpGateway`. Daily caps across restarts/workers and pacing require a caller-owned shared limiter; `InMemoryBudget` is not a daily persistent quota implementation. Do not mark them implemented merely by filling `period_limits`. Cache only where permission is established; the bundled memory cache has no TTL/persistence. On 429/unavailability, display a retry/manual-input option; no automatic paid fallback and no endpoint rotation to evade limits. Population analysis remains deferred/lowest priority.

## Switching instances without changing business logic

The existing ports separate consumer logic from provider protocol. Photon instance switching is regression-tested. ORS currently restricts host/path to HeiGIT and requires `credential_handle`; removing those fixed instance assumptions safely is a planned FF-03 change, not an already delivered capability. See the [incremental implementation plan](../superpowers/plans/2026-11-05-free-first-trial.md). The target for the **same supported protocol** is to change only provider composition/configuration:

1. Select a distinct instance ID, base URL (including any reverse-proxy prefix), matching HTTPS origin allowlist and supported capability flags.
2. Supply credentials as runtime headers only if required. Build a separate gateway per authenticated provider so headers cannot leak to another provider; inject a shared budget where the application needs a total across gateways.
3. Update quota/price/rights/source-version references and explicit limits. Paid access requires an explicit price and cost-budget change; never silently replace zero with a paid allowance.
4. Construct the same adapter using its configurable `provider_id`; retain the same resolver/place/routing port in consumer code. Distinct provider IDs/cache keys prevent reuse of another instance's cached results; retain the effective instance identity in run provenance. Candidate OSM identity alone does not identify the serving instance.
5. Run offline contracts and a small approved live sample before enabling the new instance. Instance capabilities and data coverage can differ even with the same protocol.

For example, a compatible Photon endpoint can change from `https://photon.komoot.io` to `https://geo.example.org/photon`; the adapter still appends `/api` or `/reverse`. Overpass appends `/api/interpreter`; ORS appends `/v2/...`. The gateway preserves base path prefixes. Synthetic regression tests cover Photon public/keyed/self-hosted configurations using the same result contract; these are not actual vendor certifications.

Switching to a different API protocol (e.g. a non-Photon commercial geocoder) requires a new adapter behind the existing port, not just a new URL. The core and consumer business logic should remain unchanged. Self-hosted endpoints currently must satisfy the gateway's HTTPS/public-DNS policy; localhost/private-IP services require a separately reviewed transport/policy extension. No private-network bypass is included in this decision.

## Verification boundary

Zero-cost/no-key records are valid activation inputs. Missing required terms/budget/sample references still block a live run; keyed providers still require their key. ORS defaults to required authentication; an approved no-key self-hosted instance explicitly sets `authentication_required=false`. Hosted ORS Standard must retain required authentication. Version may be explicitly recorded as unknown where the operator does not publish one, with the reproducibility limitation retained. Current live tests deliberately fail on a complete activation record until measured runners are implemented; passing the offline configuration tests is not a provider-quality result. No public instance is silently enabled at import time.
