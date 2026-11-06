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

The Private.coffee landing page was reachable while `/api/interpreter` and minimal GET/POST queries timed out in the [root-cause record](2026-11-06-ff04-root-cause-followup.md). Later counted probes returned 403 for `/api/status` and another interpreter timeout. No POI quality pass exists; Overpass stays disabled. Do not rotate endpoints to evade a limit or interpret an unavailable response as an empty place list.

The one private quota ledger counted, at this checkpoint on 2026-11-06 UTC, Photon 33, Overpass 10 and ORS 16 attempts; all remained below 50/source/day. RestaurantTrafficDiagnosis still pins a different core wheel. **No source may be enabled through FF-05 from this handoff**: Photon fails its duplicate-ID quality rule, Overpass lacks a reachable API, and ORS has only narrow smoke coverage with no consumer route workflow. Source-specific failed and passing reports remain available for the next controlled decision. No consumer production configuration was changed.
