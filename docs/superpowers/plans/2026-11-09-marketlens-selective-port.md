# MarketLens Selective Port Implementation Plan

> For agentic workers: execute using superpowers:executing-plans, then obtain one independent whole-branch review.

**Goal:** Adapt robust collection and quality helpers with optional browser extraction and factual AI explanations into the existing Python package.
**Architecture:** Extend the bounded gateway; add separate immutable helper results and optional adapters. Preserve V1 schemas and consumer-owned acquisition, persistence and authorization.
**Tech Stack:** Python 3.12, existing Pydantic/httpx/Shapely/pyproj, optional pinned Playwright.
**Spec:** `docs/superpowers/specs/2026-11-09-marketlens-selective-port-design.md`

## Global Constraints
- No provider activation, endpoint rotation, paid calls, merge or deployment.
- Preserve V1 result serialization and original place/evidence records.
- Ship MIT upstream attribution for adapted material.
- Browser and AI optional; unknown permissions never grant external disclosure.

## Review Focus
- Retry deadlines and budgets must cover every actual HTTP attempt, including cancellation.
- Empty/incomplete datasets must not imply real-world absence or full coverage.
- Fuzzy matching must not merge same-address distinct businesses or treat scores as probabilities.
- Browser documents must not cause network/JavaScript execution, leaked contexts or cookies.
- AI citations/schema validation do not prove semantic truth; all output stays unverified.

### Task 1: Gateway and Overpass
Files: `providers/http.py`, `providers/overpass.py`, `tests/unit/test_marketlens_http.py`.
Interfaces: `HttpGateway.request(..., *, form=False, retry_transient=False)`; `OverpassPlaceProvider(..., request_method='GET')`.
- [x] Add and run RED tests: exact URL-encoded POST body, unchanged JSON POST, two failures then success, budget exhaustion, Retry-After/deadline and unsafe request rejection.
- [x] Implement optional parameters without changing old callers; run new and existing provider tests.

### Task 2: Place matching and quality
Files: `place_quality.py`, `tests/unit/test_place_quality.py`.
Interfaces: `normalize_comparison_text`, `find_duplicate_candidates`, `summarize_place_quality`.
- [x] Add and run RED tests for German/Chinese normalization, nearby cross-source candidates, same-source exclusion, source-ID repeats and empty completeness.
- [x] Implement frozen outputs, bounded candidate work and existing distance calculation; run quality and place suites.

### Task 3: Optional browser extraction
Files: `providers/browser.py`, `tests/unit/test_browser_documents.py`, optional browser test/lock.
Interfaces: `HtmlDocument`, `BrowserExtraction`, `BrowserExtractor` async context manager with `extract(document, selectors, context)`.
- [x] Add and run RED tests for disabled/rights checks, explicit selectors, partial/missing fields, input/output limits, fresh contexts and cancellation cleanup.
- [ ] Implement lazy Playwright import and offline HTML extraction with blocked requests and disabled JavaScript. Verify real Chromium against synthetic HTML.

### Task 4: Optional cited AI explanation
Files: `interpretation.py`, `providers/gemini.py`, `tests/unit/test_interpretation.py`.
Interfaces: `ApprovedFact`, `ExplanationRequest`, `Explanation`, `GeminiExplainer.explain(request, context)`.
- [x] Add and run RED tests for disabled/unknown rights, minimized payload, external citation injection, invalid JSON/schema, provider failure and valid cited output.
- [x] Implement strict bounded models, evidence validation and explicit gateway/model settings; run AI and HTTP suites.

### Task 5: Delivery
- [x] Add MIT notice, usage examples, migration/limitations and branch status.
- [ ] Run full offline suite, optional real-browser tests and distribution checks; independent review and repair findings with regressions.
- [ ] Create feature branch/commit against the actual upstream parent and open PR. Record exact verification and unperformed live checks.

## Execution record

Local complete suite: 342 passed, 4 skipped. Source/wheel builds passed. Four independent review findings were each reproduced before correction and the suite passed after fixes. Browser lifecycle/limits/cancellation pass offline; real local Chromium launch is blocked by socket EPERM. The new browser CI job carries that remaining execution check. Default GET and all source activation states remain unchanged.

Decision: if context creation is interrupted before a handle is returned, close the browser session; recovery requires a new session and other active operations may become unavailable. This favors resource isolation over preserving a damaged pool.
Decision: repeated identities select a complete observation before stable tie-breaking for candidate search, without merging fields or deciding source truth.
