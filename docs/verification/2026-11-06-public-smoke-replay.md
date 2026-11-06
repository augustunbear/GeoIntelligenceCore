# FF-04 public smoke replay — 2026-11-06

This record preserves two **failed** invocations of the existing live Runner. It
does not establish provider quality or authorize FF-05 activation. The frozen
input files are kept outside git; their hashes are in the individual sanitized
[Photon](reports/2026-11-06-photon-public-smoke.json) and
[Overpass](reports/2026-11-06-overpass-public-smoke.json) reports.

## Source and gates

GitHub main `d8cb37c4f261fc83f723dfec8c2943a7b6b10321` was the clean
measurement checkout. `package_identity()` verified package `0.1.0a1`, runtime
fingerprint `f19d31c1ac93e712d468e1d21d8f1bad330ac859599657aa43d0dd7d863280a4`
and Runner fingerprint `fe9c02be832cdf250f67bc3b48255ea02be8ff9e4480e627d58b129fadadd2bc`.
The focused offline gate passed 73 tests; the full offline suite passed 288 with
3 opt-in live skips. PR #31 head CI run `42212246403` concluded success. These
offline results do not substitute for the failed opt-in results below.

Before Runner I/O, the public Photon smoke batch froze two operations against
Berlin's Brandenburger Tor. The independent coordinate reference is
[Wikipedia's monument coordinates](https://en.wikipedia.org/wiki/Brandenburg_Gate),
cross-checked against the
[Berlin city monument description](https://www.berlin.de/en/attractions-and-sights/3560266-3104052-brandenburg-gate.en.html).
The expected OSM way identity `104393803` and historic address came from the
[Nominatim lookup documentation](https://nominatim.org/release-docs/3.6/api/Lookup/),
which shares OSM lineage with Photon; it is an identity check, not independent
survey evidence. The predeclared quality bound was 100 m and house precision,
with p95 at most 8 s and traced Python peak memory at most 100 MB.

The Overpass smoke batch froze a small rectangle around Zur letzten Instanz,
Berlin, and expected OSM node `411728139`. The venue's
[operator contact page](https://zurletzteninstanz.com/kontakt/) confirms its
address and restaurant use; the
[Berlin monument register](https://denkmaldatenbank.berlin.de/daobj.php?obj_dok_nr=09011253)
confirms the site, while the [OSM object link in a public source](https://oldpubs.com/pubs/zur-letzten-instanz-berlin/)
supplies the mapped identity. This single venue is not an independent complete
inventory for the rectangle. Precision and recall were predeclared as 1.0 for
that one identity, p95 at most 20 s and traced peak memory at most 100 MB.
Neither batch covers the required representative German strata or an independent
POI inventory; a later HTTP success on these inputs alone would remain smoke
evidence, not field acceptance. Both sets of thresholds were frozen before
their Runner invocation and were not adjusted after the failures.

## Actual execution

| Source | Runner cases | Runner HTTP reservations | Result | `settings_sha256` |
| --- | ---: | ---: | --- | --- |
| Photon demo | search + reverse | 0 | failed; both `unconfigured` | `d3c214b3eb795d1a120de1d7ff290dc9789ae41f56de4841b7182a8fe0bdac33` |
| Private.coffee Overpass | places | 0 | failed; `unconfigured` | `8a5c57e9daa70f459fa4276cff2486ec3b1b02615235763b8e0243a1dbc9265d` |
| HeiGIT ORS | route, matrix, catchments | 0 | not invoked; current account quota/rights and independent labels unavailable | none |

The managed HTTP policy now lists all three selected hosts. A TLS HEAD via the
inherited proxy reached Photon. Nevertheless, Python `getaddrinfo()` for all
three service names failed with `gaierror`. The gateway requires local public-IP
resolution before reservation, uses `trust_env=False`, and pins a direct IP for
HTTPS. This proxy-only runtime cannot satisfy that transport path. The live
Runner therefore rejected both public sources before provider HTTP; no provider
payload, accuracy or service latency was observed. We did not change DNS,
transport, endpoints, proxy policy or SSRF checks to force a pass.

One separately budgeted Overpass reference lookup through the inherited proxy
returned `ReadTimeout` without a response. It consumed **one** Overpass
source/UTC-day reservation in the persistent same-host ledger; the Overpass
Runner itself consumed zero. The ledger was not reset. The local caps were 5
attempts/run, 50/source/UTC-day, concurrency 1 and zero EUR cost. Small-sample
p95 and memory in the failed reports describe local rejection only.
The restricted ledger remains at `/workspace/ff04-work/quota.sqlite` in this
execution workspace. A read-only post-run query showed
`daily=(overpass,2026-11-06,1)` and
`runs=(public-reference-20261106,1)`; its SHA-256 at that checkpoint was
`c6c44579b20b6ca8be713bdaf17860178e60a922d87d1b533d33e81107fbdc5c`.
This separately accounts for the reference attempt without adding it to either
Runner report's zero-call field.

The runtime `ORS_API_KEY` binding was present but never read or logged. The
[current account terms](https://account.heigit.org/info/tos),
[plan](https://account.heigit.org/info/plans) and key-specific quota remain
unverified, so a key alone does not authorize an ORS call. The public-service
references are [Photon's demo policy](https://github.com/komoot/photon/blob/master/README.md#demo-server),
[Private.coffee's terms](https://overpass.private.coffee/) and
[OSM attribution and ODbL](https://www.openstreetmap.org/copyright).
Retention/export rights remain unresolved; no raw provider payload is in git.
Invoking the existing ORS live test with this activation file produced one
explicit skip, `approved provider record unreadable; provider quality
unverified`, before any provider I/O. No ORS measurement report was created.

## FF-05 boundary

RestaurantTrafficDiagnosis still pins source commit
`27ee290a7b51e245414d18ff681603c1c99decf6`, package fingerprint
`c638904f363336bbbe912168c0d61877b68d2698d5bbce749648c46a5dca652c`
and wheel SHA-256
`e722028af51030cf3408a9ffe5b550fc2dc203bb21a22c55f8044b766e1cf314`.
This main checkout has a different runtime fingerprint. Both measured source
gates failed, and neither report can enable that fixed wheel. No consumer
production configuration was changed.
