# FF-04 current-environment preflight — 2026-11-06

This is an execution record, **not a live provider measurement report**. No
Photon, Overpass or ORS quality gate passed and no FF-05 source is approved by
this record.

## Checked baseline

- GitHub `main` and the clean local checkout both pointed to
  `0e062f793da5d2428a0f00852bb8917ea0d95a92` (PR #30 merged). Its latest
  main CI run `42209539599` concluded `success`. The local Python 3.12 suite
  produced **288 passed, 3 opt-in live skips**.
- The existing Runner verified that checkout and its editable package install:
  package `0.1.0a1`, `code_sha256`
  `f19d31c1ac93e712d468e1d21d8f1bad330ac859599657aa43d0dd7d863280a4`,
  `runner_sha256`
  `fe9c02be832cdf250f67bc3b48255ea02be8ff9e4480e627d58b129fadadd2bc`.
- RestaurantTrafficDiagnosis `development` still pins core commit
  `27ee290a7b51e245414d18ff681603c1c99decf6`, package fingerprint
  `c638904f363336bbbe912168c0d61877b68d2698d5bbce749648c46a5dca652c`
  and wheel SHA-256
  `e722028af51030cf3408a9ffe5b550fc2dc203bb21a22c55f8044b766e1cf314`.
  A current-main report would not match that pinned source and package. Consumer
  PR #38 is merged into `development`; this does not activate a source.

## Access and input checks

The managed environment reports an enforced restricted HTTP policy. Its
effective allowlist does not contain `photon.komoot.io`,
`overpass.private.coffee` or `api.heigit.org`. After turn-scoped network
permission was granted, a TLS HEAD preflight through the inherited proxy to
each approved hostname returned **403 CONNECT denied**. These were access
checks, not Runner operations or provider responses. No DNS/IP substitution,
proxy rewrite, endpoint rotation or SSRF-policy change was attempted.

The runtime binding `ORS_API_KEY` is reported ready and was checked only for
presence; its value was not read or logged. That removes the earlier
"key unavailable" assumption for this environment, but does not establish
current account quota, output rights or endpoint access.

Current public terms were rechecked without sending test requests:
[Photon's official demo policy](https://github.com/komoot/photon/blob/master/README.md#demo-server)
allows reasonable project use without a published numeric entitlement;
[Private.coffee's terms](https://overpass.private.coffee/) allow commercial use
without registration and require fair use, a meaningful User-Agent and OSM
attribution. The current [HeiGIT plans](https://account.heigit.org/info/plans)
and [account terms](https://account.heigit.org/info/tos) returned no readable
text to this review, so this record establishes no key-specific ORS allowance
or output licence. The [OSM copyright notice](https://www.openstreetmap.org/copyright)
remains the data rights reference; retention and redistribution need separate
approval.

The earlier frozen private sample bundle was not present in the current
workspace. The repository retains only its hashes and redacted failed reports;
they cannot reconstruct independent labels or reference extracts. No new
quality thresholds were inferred from provider output or weakened. The existing
5 attempts/run, 50 attempts/source/UTC-day, concurrency 1 and zero-cost
constraints remain mandatory when a durable same-host ledger and approved
inputs are available.

## Per-source outcome

| Source | This preflight's provider HTTP attempts | Quality/FF-05 decision |
| --- | ---: | --- |
| Photon forward and reverse | 0 | Unverified; remain disabled |
| Private.coffee Overpass places | 0 | Unverified; remain disabled |
| HeiGIT ORS route, matrix, catchments | 0 | Unverified; remain disabled |

No FF-04 `settings_sha256` acceptance report was generated in this preflight:
the existing Runner cannot reach its selected services and the frozen input
bundle is absent. The previous [first-batch failed reports](reports/2026-11-06-first-batch.json)
remain unchanged. For any later source-specific pass, FF-05 must compare the
report's exact core commit, package fingerprint, instance, effective settings and
canonical `settings_sha256`, sample/threshold hashes, quality gates, time and
rights references against its deployed wheel and approved configuration before
enabling that source. A pass for another source grants nothing to this one.
