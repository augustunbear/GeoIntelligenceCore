# Third-party notices

## MarketLens selective Python adaptation

Source: https://github.com/GipsyDanger-dev/MarketLens

Reviewed upstream commit: `e1f86ba7dc16b69155e624eb23a37606e8b06f28`.
Original MarketLens code is dual-licensed Apache-2.0 OR MIT. This adaptation
selects MIT. The complete original copyright and MIT text is included in
`src/geo_intelligence_core/data/licenses/MarketLens-MIT.txt`, shipped in the wheel.

Adapted/reference areas:
- `apps/web/src/providers/openstreetmap/{provider,query}.ts`: form POST and bounded retries.
- `apps/web/src/research/{normalization,deduplication,data-quality}.ts`: comparison-only normalization, explainable duplicate candidates, descriptive completeness.
- `apps/web/src/providers/google-maps-scraper/browser-pool.ts`: bounded browser lifetime and allocation; new Python implementation uses fresh per-document contexts and supplied HTML, without Google selectors/navigation.
- `apps/web/src/ai/{types,gemini-provider}.ts` and `research/research-ai-service.ts`: optional structured interpretation, explicit invocation and failure isolation.

These are selective adaptations, not a full fork. Geographic calculations use
the existing Python geometry implementation. Address rules are language-neutral;
upstream Indonesian abbreviations are not applied. Source records are not merged
by heuristic scores. Browser documents cannot execute JavaScript or load remote
resources. AI explanations require approved input facts and remain unverified.

No gosom scraper source, Google Maps selectors or navigation implementation is
copied. MarketLens's independent upstream `gosom/google-maps-scraper` MIT notice
must be included if that scraper material is adopted in a future change.

## Dependencies and data

Dependencies retain their own licenses; this notice does not relicense them or
the rest of GeoIntelligenceCore. Software licensing does not grant rights to
third-party data, browser acquisition or external AI processing. Those require
separate source/purpose-specific permission checks.
