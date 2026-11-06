# FF-04 root-cause follow-up — 2026-11-06

This follow-up uses Codex cloud's enforced restricted proxy and the existing
same-host quota ledger. It does not replace the failed frozen reports in the
[earlier cloud run](2026-11-06-codex-cloud-proxy.md). No source is activated.

## Photon label drift and new frozen public smoke batch

The earlier label `photon:osm:W:104393803` was a real historical Berlin Gate
identity, visible in [Nominatim's old lookup example](https://git.openstreetmap.org/nominatim.git/blob/6f2e767c77a7efbc326fdb69287d72f062cec5b0%3A/docs/api/Lookup.md).
An [independently published current map page](https://mapcarta.com/25743032)
identifies the same Berlin landmark as OSM way `518071791`, at approximately
13.3777° E, 52.51628° N, with address Pariser Platz 1. The earlier Photon
diagnostic also observed that way. This is evidence of a changed reference
identity, not a retroactive pass for the old batch.

Before the new Runner call, public [samples](samples/2026-11-06-photon-current-public-samples.json)
and [thresholds](samples/2026-11-06-photon-current-public-thresholds.json) were
frozen with SHA-256 `3ec980c4762ccb62c961783a767964937956f01cc5a4463fafc2904575e3ad33`
and `b560f6b2d47654ce7a552cf6550919f6ddeacc2d5d2aef3e5d985bed8ef66383`.
The identity label and independently rounded reference coordinate changed;
the 100 m maximum error, required house precision, candidate bounds, 8 s p95
and 100 MB traced Python memory ceiling did not relax. Mapcarta republishes
OSM data independently of Photon; it is not an independent field survey.

The [sanitized real Runner report](reports/2026-11-06-photon-current-public-smoke.json)
binds clean source commit `4de0a1255a9cd0f976de91b21d25d8b750d0237b`,
runtime/Runner hashes and `settings_sha256`. At 13:54:20 UTC, search and reverse
both returned `ok` and passed frozen quality; latency, memory and budget gates
also passed. Two HTTP attempts were reserved. This **one-landmark smoke batch**
does not meet FF-04's six German address strata or independent field-quality
coverage. FF-05 must not enable Photon from this batch alone.

## Overpass response path

The gateway previously set every HTTPX timeout phase to 5 seconds even when
the approved operation deadline was 40 seconds. The prior 5.98 s
`network_failure` is consistent with this read timeout. A red/green unit test
exposed `read=5` and now verifies `read=40`, while connection/write/pool retain
5 s and the whole operation remains bounded by the approved deadline.

With that fix, the [real unchanged Overpass Runner batch](reports/2026-11-06-overpass-read-timeout-followup.json)
reserved one attempt but exceeded the 40 s total deadline. The report says
`blocked`, with no claimed quality result. Four separately counted diagnostics
are summarized in a [sanitized non-Runner record](reports/2026-11-06-overpass-diagnostic-summary.json):
`/api/status` GET read timeout after 8 s; landing-page HEAD 200
after 1.72 s; minimal `/api/interpreter` GET read timeout after 10 s; the same
minimal query by the operator-preferred form POST also timed out after 10 s.
The landing page is reachable, but the API backend did not serve even a trivial
query from this cloud path. GET versus POST does not explain this observation.
No POI coverage was measured. This does not prove whether the operator backend
or an intermediary causes the stall; do not switch endpoints to evade it.
Overpass remains disabled pending recovery and a new independently labeled run.

The unchanged persistent ledger at `/workspace/ff04-work/quota.sqlite` then
showed 7 Photon and 8 Overpass attempts for 2026-11-06 UTC, including earlier
runs and every diagnostic; checkpoint SHA-256 was
`a038bf192dd168a8a54fe5e6dd2cd4689e43d81608e90665414a7aba66ed4f5f`.
The per-run five, per-source daily 50, concurrency one and zero-EUR caps stayed
in force. ORS received zero requests; its account-specific quota/rights and
independent route, matrix and catchment labels remain unverified.

## FF-05 handoff

Photon's public smoke pass supports only the stated landmark cases. Overpass
and ORS have no passing quality report. Keep all three disabled in the consumer.
RestaurantTrafficDiagnosis remains pinned to `27ee290a7b51e245414d18ff681603c1c99decf6`,
which differs from this measured source commit. Any future independently passing
source requires exact package/settings verification and an explicit consumer
pin review before enabling it. No consumer production configuration changed.
