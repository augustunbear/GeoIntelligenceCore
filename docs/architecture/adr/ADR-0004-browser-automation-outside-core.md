# ADR-0004: Browser automation outside GeoIntelligenceCore

Date: 2026-11-17
Status: Accepted; migration implemented in PR #52

## Context
GeoIntelligenceCore is a reusable, provider-neutral geospatial Python package. The 2026-11-09 selective MarketLens adaptation introduced an optional Playwright HTML extractor under `geo_intelligence_core.providers.browser` and a `[browser]` extra. Although opt-in and offline, browser document extraction is not a geospatial capability. Keeping it here increases coupling to Chromium, web-page structure and website-specific acquisition rules.

## Decision
1. GeoIntelligenceCore MUST NOT own Playwright, browser execution, website discovery, menu scraping, consent interactions, or website-specific selectors. No new browser automation should be added to the core.
2. Website acquisition and extraction belong to a separate optional collector or to the consuming application. AI interpretation of scraped pages belongs outside the geospatial core as well; core analysis must never require it.
3. The core MAY accept caller-supplied, rights-checked structured geospatial facts through stable, provider-neutral contracts. Imported facts retain source, retrieval time, permitted purpose, attribution, confidence and unknown/partial status. An extracted website assertion is not automatically a verified location or POI fact.
4. Core geospatial acquisition remains through documented provider adapters (e.g. Photon, Overpass/OSM and ORS), permitted offline imports and approved alternatives. Browser automation is not a substitute for an authorized Google Maps/Places API or permission to bulk extract map data.
5. Do not silently remove the existing optional `providers.browser` implementation or `[browser]` extra: inventory references, choose a migration/deprecation path, preserve compatibility according to release policy, and remove code/dependencies only in a separately tested implementation PR. Existing documentation describing the historical implementation remains factual until then.
6. Existing optional Gemini factual explanation code is also not required for the geospatial core; evaluate its ownership separately, without treating this ADR as authorization for an unreviewed breaking removal.

## Boundaries
```text
Consumer / optional external collector (Playwright, website discovery, menu extraction, AI)
               | approved, structured, provenance-rich facts
               v
GeoIntelligenceCore (location, POIs, geometry, catchments, comparison, quality)
               |
      replaceable authorized geospatial providers / permitted offline inputs
```

## Consequences and acceptance
- No Playwright runtime, browser download or browser-specific API is a prerequisite for core install or geospatial analysis.
- External collectors must not bypass evidence-rights checks or automatically turn page text into verified geospatial truth.
- A follow-up implementation PR should inventory and migrate the existing optional browser API and tests, update extras, examples and notices, and run wheel/contract/consumer compatibility checks before any removal.
- The migration was implemented separately in PR #52 after GeoWebCollector PRs #1 and #2 passed CI. No package release, live provider activation or consumer integration is asserted.
