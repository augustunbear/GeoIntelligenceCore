# Selective MarketLens adaptations

This increment adapts small capabilities from MarketLens commit
`e1f86ba7dc16b69155e624eb23a37606e8b06f28` into the existing Python package.
It does not install a Node service, copy MarketLens's database, activate a
provider, change consumer pins, or merge PR #41's field observations.

## Overpass: opt-in form POST

```python
from geo_intelligence_core.providers.trial import build_trial_provider

# settings and shared_budget retain the existing explicit terms, endpoint,
# bounds and persistent per-source/day controls. Construction performs no I/O.
provider = build_trial_provider(settings, budget=shared_budget,
                                overpass_request_method='POST')
result = await provider.search(place_query, request_context)
```

Default remains GET for compatibility. POST uses an URL-encoded `data` body,
not JSON or query-string parameters. `provider_http_method` is recorded in
the result's effective conditions. It adds opt-in retries for 502/504 and
transport errors, with exponential delays (0.25 s, 0.5 s), at most three
attempts and the existing run quota/whole-operation deadline. 429/503 respect
`Retry-After`; every actual attempt consumes a reservation. No endpoint rotation
or automatic search-radius reduction. A failed query is never an empty dataset.

Changing GET to POST is a new effective configuration requiring its own live
measurement; old GET acceptance reports do not approve POST. The existing
measurement runner keeps its default until explicitly extended/reconfigured.

## Comparison and quality

```python
from geo_intelligence_core import find_duplicate_candidates, summarize_place_quality

summary = summarize_place_quality(place_set.places)
candidates = find_duplicate_candidates(place_set.places)  # geometry extra
```

Matching does not edit source names/addresses, merge records, or bypass data
rights. It handles Unicode accents/case (including German ß), but does not
apply Indonesian address substitutions or infer German abbreviation aliases.
The provisional 0.75 threshold combines name-token similarity, ellipsoidal
distance, shared categories and structured-address equality. Matches over
250 m and missing comparable names are excluded. It is an explainable
heuristic, not a calibrated probability. At most 1,000 records are accepted;
larger workloads need spatial indexing in a separately scoped change.

For repeated source identities, candidate search chooses the observation with
usable name/address/category/contact fields, then a stable serialized tie-break.
This does not establish which conflicting observation is current or true, and
never combines their fields. Keep source conflicts for consumer review.

Completeness describes received records. Its denominators include repeated
source identities; the repeat count is reported separately. Name, category,
any nonempty structured address, and validated coordinates define a complete
record; phone/website additionally contribute to six-field completeness.
Empty denominators yield `None`. Address presence is not address precision.
Coverage remains `unknown`, regardless of field completeness.

## Optional Playwright document extraction

Install `geo-intelligence-core[browser]` and then `python -m playwright install
chromium`. Browser installation is explicit and never occurs during core import.

```python
from geo_intelligence_core.providers.browser import BrowserExtractor, HtmlDocument

document = HtmlDocument(html=approved_html, evidence=source_evidence,
                        purpose='document-extraction')
async with BrowserExtractor(enabled=True, max_concurrency=1) as extractor:
    result = await extractor.extract(document, {'name': 'h1', 'address': '.address'},
                                     request_context)
```

`source_evidence.rights.use` must be allowed for exactly that purpose. The
consumer acquires the HTML lawfully and retains responsibility for source
rights. `source_ref` and retrieval time describe acquisition, not extraction.
Output retains the evidence and a document hash. It is unverified extracted
text, never automatic business/geographic truth.

One browser is reused within a session; each document gets a fresh context,
preventing cross-document cookies/state. Document scripts are disabled,
service workers blocked, downloads disabled and all requests aborted. Output
reports the number of aborted requests. Defaults: concurrency 1 (maximum 4),
1 MB HTML, 20 selectors, 2,000 characters per field, 10 s extraction deadline
including slot wait. Resource cleanup gets a separate maximum of 5 s per
resource. If cancellation interrupts context creation, the whole browser
session is closed because the context handle may be unreachable; other work
in that session may become unavailable. Open a new session to retry.

Missing fields are null/partial; ambiguous selectors or truncated values are
partial, not silently complete. Selector errors and unavailable browsers return
explicit failures. Exceptions never return source HTML. `browser_factory` can
inject an existing launch policy/executable; the extractor owns and closes the
returned browser. Keep the session open until all extraction tasks settle.

This is a complete offline document extractor, not a live Google Maps crawler.
It cannot render data that only appears after executing a site's JavaScript.
MarketLens's Google selectors, consent clicking, proxy rotation and email
crawling are not imported. Live web acquisition needs its own approved adapter.

## Optional Gemini factual explanations

```python
from geo_intelligence_core.interpretation import ApprovedFact, ExplanationRequest
from geo_intelligence_core.providers.gemini import GeminiExplainer

request = ExplanationRequest(
    facts=(ApprovedFact(id='record-count', text='The query returned 2 records.',
                        evidence_ids=('source-evidence-id',), kind='derived'),),
    evidence=(source_evidence,), purpose='factual-explanation', language='de',
    allow_external_processing=True,
)
explainer = GeminiExplainer(approved_ai_gateway, provider_id='gemini',
                            model=explicit_model_id, enabled=True)
explanation = await explainer.explain(request, request_context)
```

Construct the existing `HttpGateway` with the selected Gemini endpoint,
`explain` in both policy capabilities and provider flags, an `x-goog-api-key`
runtime header, response-size/deadline/call limits, and a shared budget with a
conservative cost-per-attempt ceiling covering bounded input and output.
This adapter does not claim that Gemini is free; account, region, processing
terms, quotas and pricing need separate approval. No real AI calls were made
to verify this increment. Model selection is explicit (no stale default model).

Every fact binds to provided evidence. That evidence must explicitly allow use
and redistribution for the same purpose, and the caller separately approves
external processing. This conservative dispatch gate does not replace legal
review of the actual provider/region. At most 100 facts (2,000 characters each)
are accepted. Payloads contain selected fact text/IDs/kinds and source retrieval
times/quality only: no raw tags, private source URLs or scope tokens. Do not put
credentials or unnecessary personal data in fact text/IDs.

Generation uses JSON Schema, a bounded token cap (default 2,048), strict local
validation, existing citation IDs, `STOP` finish state and input/prompt/model
fingerprints. Provider/malformed-output failures return no explanation and do
not change the original analysis. No additional 502/504/network retries are
enabled for billable generation; the gateway's existing 429/503 policy and
per-attempt budget still apply. The model can still misstate facts despite
valid citations: output is always `unverified`, `requires_review=True` and is
not converted into new `Evidence`. Consumers own rendering, approval and any
storage permitted by source and model-provider terms.

## Verification and compatibility

No saved V1 model/envelope changes, automatic activation, target database
migration or consumer upgrade. The source candidate remains unreleased
`0.1.0a1`; new optional/helper API is additive. Historical release SBOMs remain
historical, not a dependency manifest for this changed candidate.

Offline regression: `python -m pytest -q`.
Optional Chromium: `GEO_BROWSER_TESTS=1 python -m pytest -q
tests/unit/test_browser_documents.py`. Set `GEO_CHROMIUM_PATH` only when using a
system executable instead of Playwright's installed Chromium.

Locked browser CI dependencies target Linux x86_64/Python 3.12 separately from
base dependencies. The browser CI job installs Chromium and exercises synthetic
HTML, scripts, blocked requests and partial fields. Local Chromium launch was
attempted but the managed environment denied Chromium's process-singleton
socket (`EPERM`); lifecycle/limits/cancellation are tested offline. This does
not constitute a live provider or AI acceptance result.

Upstream software notices: [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
Official API references checked 2026-11-09:
- https://playwright.dev/python/docs/api/class-browsercontext
- https://playwright.dev/python/docs/api/class-page#page-set-content
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/api/generate-content
