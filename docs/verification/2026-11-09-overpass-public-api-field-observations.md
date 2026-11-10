# Overpass public API field observations — 2026-11-09

> Evidence type: user-supplied field report from Google Cloud Shell (Germany) and GipsyDanger-dev/MarketLens. Transcribed as reported; **not independently reproduced by GeoIntelligenceCore's FF-04 runner**. This is supplemental evidence, not a new acceptance pass or production activation.

## Observed results

- Public endpoint `https://overpass-api.de/api/interpreter` returned HTTP 200 and real Nuremberg OSM restaurant JSON without an API key.
- One reported successful request took **49.544043 seconds**. This is a single observation, not an average, SLO or benchmark.
- MarketLens queries around 1 km succeeded multiple times, but sometimes first returned HTTP 502 and succeeded after retries.
- In this environment, `overpass.private.coffee` and `overpass.kumi.systems` did not respond within 25 seconds; `overpass.nchc.org.tw` failed DNS resolution. These are time- and environment-specific results, not permanent provider judgments.
- Larger radii (especially >2 km), strategy comparisons and sustained production reliability were **not validated**.

## Reproducible minimal connectivity probe

```overpassql
[out:json][timeout:20];
node["amenity"="restaurant"](49.45,11.05,49.46,11.07);
out center 5;
```

```bash
cat > /tmp/overpass-query.txt <<'EOF'
[out:json][timeout:20];
node["amenity"="restaurant"](49.45,11.05,49.46,11.07);
out center 5;
EOF
curl --connect-timeout 10 --max-time 60 \
  -H "User-Agent: GeoIntelligenceCore-Test/1.0" \
  --data-urlencode data@/tmp/overpass-query.txt \
  "https://overpass-api.de/api/interpreter" \
  -o /tmp/overpass-response.json \
  -w "HTTP %{http_code} | Time %{time_total}s\n"
```

Reported successful output: `HTTP 200 | Time 49.544043s`. This probe uses **node only**, a small bounding box, `amenity=restaurant` and a five-element output cap. It is a connectivity test, **not** complete POI coverage: real POIs may be ways or relations. `out 5` does not guarantee low server-side work.

## Failure modes and limits

- HTTP 502 appeared intermittently; retry sometimes succeeded. Consider 502/503/504 transient, with bounded exponential backoff and jitter, respecting public-instance policies.
- Avoid dividing a total budget equally by endpoint count and attempt count: e.g. 60 s / (2 endpoints × 2 attempts) = 15 s per request, which can defeat slow-but-successful calls. Model HTTP request deadline, Overpass QL `timeout`, overall job deadline, and backoff separately.
- A MarketLens query of `nwr["amenity"="restaurant"](around:1000,49.45,11.07); out center 30;` was more complex than the successful node+bbox probe, but **no controlled comparison** established that `nwr` or `around` caused the timeout.
- MarketLens Zod configuration rejected `OVERPASS_TIMEOUT_SECONDS=120` because the configured maximum was 60. This was startup configuration validation, not an Overpass failure. Document and validate bounds; do not inflate timeouts without understanding workload.
- HTTP 200 alone is insufficient: validate JSON and service-side error content, including malformed/partial responses.

## Design recommendations (proposals, not implemented claims)

1. Preserve a **domain-neutral** POI query core; food-service, retail and education category mappings belong in profiles/templates.
2. Keep interchangeable providers (public/self-hosted Overpass, licensed commercial POI) with declared capabilities, limits, errors, provenance, attribution and rights.
3. Query planner inputs: center, radius, categories, result cap and provider policy. Evaluate bbox/around, node/way/relation, bounded tiling, deduplication and partial-failure markers; do not mistake output caps for work caps.
4. Distinguish HTTP 400/406 (inspect, no blind retry), 429 (respect rate limits), 502/503/504 (bounded retry), network/TLS/DNS errors, HTTP timeouts and invalid JSON. Avoid retry storms and unbounded concurrency.
5. Cache by provider, normalized query, spatial extent, category and query version; retain retrieval timestamp, freshness, completeness, cached/partial status, license and attribution. **Free API access does not imply unrestricted ODbL storage or redistribution rights.**
6. Instrument HTTP status, elapsed time, result count, query scale, retry count, actual provider and safe error diagnostics.

## Suggested next controlled FF-04 measurements

With the same independently checked German coordinates and public-service rate limits: node+bbox, nwr+bbox, nwr+around; radii 500 m / 1 km / 2 km; simulated 502/429/timeouts; cache replay; provider switching and partial-result handling. Accumulate repeated low-frequency samples before claiming success rate or latency percentiles. Keep independently sourced POI quality/coverage checks separate from connectivity.

## Relationship to existing project gates

Read current `main`, `AGENTS.md`, `docs/project/status.md`, FF-04 runner/thresholds and provider contracts before implementation. Compare recommendations against existing retry, timeout, caching, budgets and rights mechanisms; only fill proven gaps. This user-supplied MarketLens observation does **not** supersede GeoIntelligenceCore's 2026-11-06 Dresel smoke pass or its frozen inputs/thresholds, and does **not** unlock FF-05 or RestaurantTrafficDiagnosis production data sources. No runtime code, provider configuration, quota or production activation is changed by this note.
