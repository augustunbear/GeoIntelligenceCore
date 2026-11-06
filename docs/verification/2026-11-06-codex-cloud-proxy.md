# FF-04 Codex cloud proxy execution — 2026-11-06

This is a real, bounded Runner execution on Codex cloud, **not a source
acceptance**. The original frozen public smoke labels and thresholds from the
[previous replay](2026-11-06-public-smoke-replay.md) were not changed. The
individual sanitized Runner reports are
[Photon](reports/2026-11-06-photon-codex-proxy.json) and
[Overpass](reports/2026-11-06-overpass-codex-proxy.json). Real inputs remain
outside git at `/workspace/ff04-work`; the report hashes bind their bytes.

## Transport and source identity

The existing gateway's direct mode requires local DNS and an IP-pinned HTTPS
route, which this proxy-only cloud environment lacks. The FF-04 fix adds an
**explicit** trusted-proxy mode: the ordinary direct mode is unchanged; a
proxy-mode request retains the approved HTTPS hostname and verifies TLS with
the managed CA. The Runner checks the selected host in the restricted Codex
network-policy snapshot and performs a credential-free private-IP CONNECT
denial probe before and after the run. It refuses a custom transport or resolver
alongside this mode. The private-IP probe is one additional check, not proof by
itself of every DNS-rebinding behavior; the managed sidecar's enforced policy
remains the trusted destination boundary. Current environment status reported
`observations_current=true`, `network_policy.state=enforced` and all three
selected provider hosts allowed before execution.

Clean Runner identity at both measurements: source commit
`74c94d842db4cb81df27da17630afda2992d7442`, package `0.1.0a1`, runtime
`code_sha256` `c81f6535d4a115e8e606a035f29b43b1f389f783f68849101cf6c0faea539ae6`,
Runner SHA-256 `a46885937bfd59bbfbdc255961eb0c46b6f3af3781961488b1529e39cfd24491`.
The network-policy SHA-256 in both reports is
`736f277a38cf433be721df66e6a45382ad187a4052141add28f25d95d4f94744`.
Neither proxy address nor credentials are retained in the reports. Photon demo
and Private.coffee Overpass do not publish a reproducible serving-instance
version here; both reports explicitly say `instance_version=unknown`.

## Frozen-batch results

| Source | Runner time (UTC) | Actual reserved HTTP attempts | Case statuses | Gates | `settings_sha256` |
| --- | --- | ---: | --- | --- | --- |
| Photon `photon.komoot.io` | 13:35:01 | 2 | search `ok`, reverse `ok`; both failed frozen quality labels | quality failed; latency, memory, budget passed | `d3c214b3eb795d1a120de1d7ff290dc9789ae41f56de4841b7182a8fe0bdac33` |
| Overpass `overpass.private.coffee` | 13:35:31 | 1 | places `unavailable` | quality failed; latency, memory, budget passed | `8a5c57e9daa70f459fa4276cff2486ec3b1b02615235763b8e0243a1dbc9265d` |
| ORS `api.heigit.org` | — | 0 | not invoked: current account terms/quota, output rights and independent route/matrix/catchment labels are unverified | blocked | — |

Photon's earlier independent OSM identity label for Brandenburger Tor was way
`104393803`. A **separate, quota-counted diagnostic after the failed Runner
batch** observed the current response identify way `518071791`; this may be an
OSM object change and does not retroactively validate either frozen case. The
quality thresholds and original failed report remain unchanged. New references
and a newly frozen batch are needed before any further quality decision.

Overpass returned `unavailable` in the Runner. A separate quota-counted
diagnostic also returned `unavailable` with safe issue code `network_failure`;
no POI coverage or accuracy was observed. The earlier independent reference
lookup timed out. Do not interpret local-rejection or unavailable timings as
service performance acceptance.

The same persistent SQLite ledger at `/workspace/ff04-work/quota.sqlite` counted
all Runner and separate diagnostic attempts. Its post-run rows were
`(photon, 2026-11-06, 5)` and `(overpass, 2026-11-06, 3)`, including the
previous batch's attempts; SHA-256 at this checkpoint was
`ba67eaf7637212e26a528f5cf55c0f944dad14b2855e921c43e43069034e7785`.
The local caps stayed at 5 attempts/run, 50/source/UTC-day, concurrency 1 and
zero EUR cost. Failed reservations were never refunded or hidden.

The public use references remain
[Photon demo policy](https://github.com/komoot/photon/blob/master/README.md#demo-server),
[Private.coffee terms](https://overpass.private.coffee/) and
[OSM copyright/ODbL](https://www.openstreetmap.org/copyright). They do not
grant unresolved cache/export permissions. No real customer address or key was
sent or stored. This one-landmark and one-venue smoke batch cannot establish
the six German address strata or independently surveyed POI completeness.

## FF-05 handoff

Neither source passed its frozen quality gate. ORS was not measured. Keep all
three disabled. RestaurantTrafficDiagnosis still pins source
`27ee290a7b51e245414d18ff681603c1c99decf6` and wheel SHA-256
`e722028af51030cf3408a9ffe5b550fc2dc203bb21a22c55f8044b766e1cf314`;
the measured code fingerprint above does not match that fixed consumer package.
A future independent passing report still requires an explicit consumer pin
update and consumer regression/rollout checks before activation. No production
consumer configuration changed in this execution.
