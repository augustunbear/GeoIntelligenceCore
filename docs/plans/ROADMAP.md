# Milestones, implementation order and acceptance

**No software milestones below are implemented as of 2026-11-04.** This plan does not authorize production deployment or binding API spend.

## M0 — research/architecture baseline
- [x] Independent repository selected
- [x] Source candidate inventory, provider/data policy, architecture/contract proposal and contributor workflow documented
- [ ] Review current dependency releases, licenses and German pilot coverage with recorded evidence
- [ ] Confirm first consumer integration point and packaging distribution method

## M1 — installable core and address candidate resolution
- [ ] `pyproject.toml`, typed Python objects, error/status/provenance contracts, documentation and offline tests
- [ ] Photon provider adapter with bounded HTTP requests, resilient errors and English/German/Chinese locale fallback documented
- [ ] Manual coordinate/location confirmation; no implicit selection of ambiguous candidate
- [ ] Publish pre-release Git tag; consume by pinned git commit/tag or private package index
**Accept when:** package installs without API keys; tests run offline; Germany fixtures and failure modes pass; one consumer validates candidate/manual workflow.

## M2 — OSM POI and transport
- [ ] Category taxonomy and OSM tags mapping, bounded geographic search, upstream rate protection, provenance and duplicate handling
- [ ] Basic road and transit access evidence, not claims of actual passengers
**Accept when:** nearby restaurant/bus/parking/school queries can be audited, missing/partial is explicit, provider failure leaves manual path.

## M3 — pedestrian catchments
- [ ] Remote routing API adapter; 5/10/15 min geometries with travel mode and data vintage
- [ ] Straight-line baseline separated from road-based isochrones; cache policy
**Accept when:** spatial boundary around barriers verified using sample fixture, behavior at no routing coverage documented.

## M4 — German population
- [ ] Audited Zensus grid import process and offline fixtures
- [ ] Document centroid vs proportional area aggregation; suppressed data and uncertainty
**Accept when:** reproducible totals, reference year, missing-cell treatment and no false present-day precision.

## M5 — consumer integration and scale evaluation
- [ ] RestaurantTrafficDiagnosis area_research integrates package and stores generic evidence with case-level permissions; no root cause auto-approval
- [ ] Another consumer pilots same package release before extracting service layer
- [ ] Only then assess hosted geocoder, PostGIS, paid POI or dedicated routing and HTTP facade with ADR/cost envelope

## Test and security gates
Unit/contract tests; selected live provider opt-in smoke; license/redistribution review; API keys and PII handling; simulated timeouts and 429s; documented data attribution; semver changelog; reviewer signoff. Avoid CI depending on public geocoding endpoints.
