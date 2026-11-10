# Selective MarketLens adaptation

User direction: retain the Python core and selectively implement useful MarketLens capabilities, also referencing its Playwright and AI implementation. Baseline: GeoIntelligenceCore `77e888dc338bf592dfdb1ce3725fd5b7f76aebbd`; MarketLens `e1f86ba7dc16b69155e624eb23a37606e8b06f28`.

## Approach
Selected in the conversation: adapt individual capabilities to existing Python contracts. Replacing the core with the full Next.js app or deploying a second service adds avoidable runtime/storage boundaries. No whole-repository vendoring or Node runtime.

## Deliverables
1. Explicit form-encoded POST support in the existing bounded gateway; opt-in Overpass POST preserves GET compatibility. Bounded idempotent transient retries retain full per-attempt quota checks, Retry-After and one operation deadline. No automatic endpoint rotation.
2. Unicode-aware comparison normalization, explainable cross-source duplicate candidates using existing ellipsoidal distance, and field completeness statistics. Preserve originals, no automatic fuzzy merge, no calibrated-probability claim, empty completeness is unknown, not zero coverage.
3. Optional Playwright HTML-document extraction: caller supplies a lawfully acquired HTML snapshot and purpose-bound evidence, plus selectors. One browser per async session, fresh isolated context per document, bounded concurrency/input/output/deadline, no document JavaScript or external network, release resources on all exits. This deliberately reuses pool/lifecycle techniques, not Google-specific scraping, proxy rotation or CAPTCHA handling. Live acquisition remains the consumer's responsibility.
4. Optional, separately invoked Gemini factual explanation adapter using the existing HTTP gateway, explicit model, approved facts/evidence, minimized payload, structured cited statements and prompt/method fingerprints. Unknown citations or malformed output fail closed; model prose remains unverified interpretation requiring human review, never new factual evidence. Provider failure does not mutate or invalidate the original geographic result.
5. MIT provenance/license notice shipped with the package, usage examples, tests, current limitations and verification record.

## Compatibility and defaults
No changes to saved V1 envelopes, default provider activation or consumer deployment. Browser and AI disabled by default and imported only explicitly. No mandatory browser, LLM key, database or service. Pure helpers do not force geometry installation; fuzzy matching explicitly needs the existing geometry extra. AI disclosure requires the caller to select facts whose purpose-bound rights permit use and redistribution to the external provider. No scope token, raw tags or credentials in AI payloads. Credentials remain gateway headers.

## Acceptance
Offline transport tests verify exact POST encoding, retry exhaustion/deadline/quotas, and unchanged JSON POST. German/Chinese text, co-located distinct businesses, duplicate source identities, incomplete and empty datasets are covered. Browser tests exercise real Chromium on synthetic supplied HTML plus deterministic lifecycle/cancellation tests. AI tests use synthetic gateway responses, no real account or billable requests. Run full offline suite and distribution/install checks; obtain an independent whole-branch review. Opening a PR is authorized; merge/deployment is not part of this request.
