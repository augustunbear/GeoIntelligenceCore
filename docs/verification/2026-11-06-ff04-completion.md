# FF-04 bounded live follow-up — 2026-11-06

Real Codex cloud requests used the existing Runner, the managed restricted proxy and one persistent same-host quota ledger. Every report preserves its actual source commit, code/Runner fingerprint, instance/settings digest, frozen input hashes, time, quota/rights references and gates. Hosted serving-instance versions remain `unknown`. No simulated result is treated as live quality evidence.

## Photon: public-location investigation, quality gate still failed

Independent public references were selected for Berlin dense city ([Mapcarta](https://mapcarta.com/25743032)), Pasing suburb ([Mapcarta](https://mapcarta.com/W25299100)), Rattelsdorf rural ([Mapcarta](https://mapcarta.com/W28068307)), Düsseldorf umlaut ([Mapcarta](https://mapcarta.com/W498263715)), Potsdam same-name gate ([Mapcarta](https://mapcarta.com/39807042)) and Munich square without a house number ([Mapcarta](https://mapcarta.com/W1033347395)). These independently published pages reuse OSM data; they are not field surveys. The names and coordinates were frozen before each batch. The 100 m error, required precision, candidate bounds, 8 s p95 and 100 MB traced-memory ceilings were not relaxed.

The earlier [Berlin landmark](reports/2026-11-06-photon-current-public-smoke.json) search and reverse passed. In the new [Pasing/Rattelsdorf batch](reports/2026-11-06-photon-strata-a-initial-fail.json), Rattelsdorf search and reverse passed but Pasing failed. A separately quota-counted diagnostic observed Photon returning the same OSM way `25299100` twice for Pasing search. The current FF-04 rule says duplicate returned candidate IDs fail quality. A proposed adapter deduplication passed in a later exploratory commit, but independent review found it contradicted that rule; it was reverted. Those exploratory passing reports are **not acceptance evidence**. The [Düsseldorf/Potsdam initial batch](reports/2026-11-06-photon-strata-b-initial-fail.json) passed Düsseldorf but failed Potsdam because the predeclared `locality` precision was incorrect. [Independent Nominatim documentation](https://nominatim.org/release-docs/develop/api/Lookup/) includes the specific [way `50637691` lookup](https://nominatim.openstreetmap.org/lookup?osm_ids=W50637691&format=json) on Brandenburger Straße, supporting `street`; the original failed report was retained. The [Munich-square batch](reports/2026-11-06-photon-strata-c-pass.json) passed both search and reverse.

The [A](samples/2026-11-06-photon-strata-a-samples.json), [B](samples/2026-11-06-photon-strata-b-samples.json) and [C](samples/2026-11-06-photon-strata-c-samples.json) samples and same-stem threshold files match their preserved reports. The Potsdam query already specifies the city and exact near point, so it does not prove ambiguous-address ranking. The square is a named place, not a missing-house-number address. Thus these are six **public-location smoke subjects**, not six completed address strata. Photon is not FF-05 eligible under the frozen quality contract. Keep manual entry/confirmation available. [Photon demo policy](https://github.com/komoot/photon#demo-server) and [OSM ODbL/attribution](https://www.openstreetmap.org/copyright) still govern any later controlled trial.

## ORS Basic: three positive operations passed, scope limited

The owner supplied a redacted HeiGIT Basic dashboard screenshot showing Directions V2 `2000/2000` remaining and `40/min`, and explicitly approved bounded Basic testing. Our stricter local 5/run, 50/source/UTC-day, concurrency-one and zero-EUR caps applied. Frozen [samples](samples/2026-11-06-ors-basic-samples.json) and [thresholds](samples/2026-11-06-ors-basic-thresholds.json) used public [Berlin Gate](https://mapcarta.com/25743032) and [Potsdamer Platz station](https://sbahn.berlin/en/plan-a-journey/rail-stations/potsdamer-platz/) coordinates, with predeclared walking distance/time and 300 s reachability-area plausibility windows. These bounds are broad independent checks derived from geodesic distance and walking speed, not surveyed route truth.

The first [real Runner attempt](reports/2026-11-06-ors-basic-initial-fail.json) passed route and matrix but returned `unknown` for the catchment. One separately counted public-coordinate diagnostic found HTTP 200, a valid 48-vertex polygon of about 405,943 m² and an integer-valued range represented as `300.0`. The adapter rejected float seconds. A red/green regression fixed it to accept only finite, integral numeric seconds; fractional values still fail. The same frozen thresholds then passed real route, directed matrix and outbound catchment in the [final Runner report](reports/2026-11-06-ors-basic-pass.json), source commit `0002002a82cf48d670bc8182412f8073d4e454f5`, with 3 HTTP attempts and all four gates passed. Its `settings_sha256` is `d4660458ba19e26b3f0f731f5e999c3d70d39be9072e3a67ddd4b942fedeb774`.

[HeiGIT account terms](https://account.heigit.org/info/tos) and [Basic plans](https://account.heigit.org/info/plans) are the operator references. A [HeiGIT staff response](https://ask.openrouteservice.org/t/free-plan-in-an-app-with-a-paid-tier-license-cc-by-sa-4-0-personal-data-and-attribution-questions/8079) permits Standard commercial use and identifies CC BY-SA 4.0 results. Attribution is required; caching/customer export needs separate review. The current consumer has no route-destination workflow. No no-route negative control, broader route set or target-runtime validation has passed, so this is a positive-operation smoke result, not permission to expose a route feature.

## Overpass and FF-05 handoff

### Dresel Europe instance: real smoke pass, FF-05 remains blocked

On 2026-11-06 at 16:58:49 UTC the existing Runner passed the unchanged public
sample and frozen thresholds against `https://ovp.dresel.systems/api/interpreter`.
The [final report](reports/2026-11-06-overpass-dresel-pass.json) binds clean source
`24a138194044790c38638fc130a85d3cfac71e0a`, package fingerprint
`6bc3868a82853e3485ce06988c2f7e6a997dbf176785a1bd61bdf5809d8fd815`
and Runner fingerprint
`9f6925365723630d9d5992dbcf4d6d8a0afca0dfccdcb06f2042c792035faff2`.
The instance ID is `overpass-europe-dresel`; its hosted version is unknown.
The endpoint setting is the origin; the existing adapter appends `/api/interpreter`.
Quality, latency, memory and budget passed: one attempt, 1.979 s batch p95 against
20 s, and 7,983,898 traced Python bytes against 100,000,000. The single labeled
OSM restaurant met precision and recall 1.0. This is not a representative POI
inventory or independent field survey; no negative control was measured.

The [initial report](reports/2026-11-06-overpass-dresel-initial.json), measured on
main `2ce0309`, also passed its measured gates but inherited Private.coffee's
terms URL inside `effective_settings`. It is retained as diagnostic evidence,
not an activation artifact. The activation now supplies explicit supported
`TrialSettings` with consistent instance terms; no runtime code, sample labels,
quality or performance threshold was changed. The final settings digest is
`a8e09040e6859b920a2415fc184930bcfa3d9f5090e6966a4ea7c6ea5d8eb307`.
The [verification record](reports/2026-11-06-overpass-dresel-verification.json)
records recomputed settings/input/report hashes and quota reconciliation.

Before HTTP, current cloud status reported an enforced restricted policy allowing
`ovp.dresel.systems`. The Runner used the declared proxy and CA and verified
private-target denial before and after measurement. The original private quota
database was absent in this environment. The owner's explicit 12-attempt history
was carried forward into `/workspace/ff04-work/quota.sqlite`; historical run rows
were not reconstructed. Both runs used this same monotonic ledger: 12 + 1 + 1 =
**14/50 Overpass attempts on 2026-11-06 UTC**. Each run retained the five-attempt
cap, concurrency one and zero-EUR ceiling. No other source was called; their
historical counters were not restored in this continuation database.

The report retains OSM ODbL/attribution rights and public-instance terms/quota
references. Those references and the unknown hosted version do not establish
consumer caching, redistribution or customer-export permission. FF-05 must
verify its exact deployed source/wheel, instance, complete effective settings
and digest, frozen inputs, report time and all gates; approve internal use,
retention and display rights; and verify consumer durable counters, source lock,
authorization, notices and controlled rollout. Keep Overpass disabled until
those checks and representative coverage are approved. No consumer production
configuration was changed and no FF-06 was created.

Local verification: 105 focused configuration/measurement regressions passed;
the full Python 3.12 suite passed 297 tests with three opt-in live skips. The
two source-specific opt-in executions are separate real runs, each passing
its single case. Commands required the environment's socket permission for
async thread wakeups; restricted-command attempts stalled in the synthetic
ledger test and were stopped, without consuming provider requests.

### Earlier Private.coffee checkpoint

The public Berlin restaurant [sample](samples/2026-11-06-overpass-public-samples.json)
and [thresholds](samples/2026-11-06-overpass-public-thresholds.json) used by
the earlier Runner attempts are now retained in the repository. Their byte
SHA-256 values match the frozen input hashes in the original sanitized report:
`b6e8b4972e5565947823184de779f7204821ab10f46a7740fd56c2041a7de454`
and `1fa9757d4024431b5c0e739a9a68540d05d9e1fd25fa0d75c012b6bbc826c707`.
These files contain a public OSM restaurant ID and bounded Berlin rectangle;
they contain no contributor metadata or private reference extract. The original
reference extract remains separate. Reusing these labels on a different
Overpass instance is a new measurement, not an inherited quality pass.
The [Europe-instance activation record](samples/2026-11-06-overpass-europe-activation.json)
references the same frozen files and keeps the five-attempt run cap, shared
50-attempt UTC-day cap, one-request concurrency and zero-EUR ceiling. It is a
test configuration, not an FF-05 consumer activation. The Runner still requires
an enforced allowlist entry for `ovp.dresel.systems` and a persistent same-host
ledger carrying earlier protocol attempts.

The Private.coffee landing page was reachable while `/api/interpreter` and minimal GET/POST queries timed out in the [root-cause record](2026-11-06-ff04-root-cause-followup.md). Later counted probes returned 403 for `/api/status` and another interpreter timeout. At that earlier checkpoint no POI quality pass existed. The distinct Dresel smoke result above does not establish Private.coffee availability. Do not rotate endpoints to evade a limit or interpret an unavailable response as an empty place list.

The one private quota ledger counted, at this checkpoint on 2026-11-06 UTC, Photon 33, Overpass 10 and ORS 16 attempts; all remained below 50/source/day. RestaurantTrafficDiagnosis still pins a different core wheel. **No source may be enabled through FF-05 from this handoff**: Photon fails its duplicate-ID quality rule, Overpass lacks a reachable API, and ORS has only narrow smoke coverage with no consumer route workflow. Source-specific failed and passing reports remain available for the next controlled decision. No consumer production configuration was changed.
