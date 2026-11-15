# Shared LLM capability: evidence audit and minimum-change plan (2026-11-14)

Status: **PARTIAL CODE AUDIT / IMPLEMENTATION BLOCKED**. This document records inspected source and a proposed gate, not a completed four-repository audit. No shared module has been implemented, tested, or deployed.

## Four-repository evidence

1. ZhuLinsen/daily_stock_analysis (upstream default branch): inspected README.md, AGENTS.md, LICENSE, src/llm/__init__.py, src/llm/litellm_backend.py. The MIT license permits reuse with notice preservation. LiteLLMGenerationBackend is a thin callable adapter with generation capabilities, response_validator, audit_context, model/provider/usage results. Search located src/agent/litellm_route_resolution.py, but its implementation and fallback orchestration have **not** been fully audited. Do not assume the adapter alone provides retries, routing, budget enforcement or structured-output guarantees.
2. augustunbear/GeoIntelligenceCore (main): inspected README.md, AGENTS.md, pyproject.toml, docs/usage/marketlens-adaptations.md. Python >=3.12; offline-first optional providers. An opt-in GeminiExplainer already exists with approved-fact/evidence gate, JSON Schema validation, fingerprints, review-required result and a supplied HttpGateway. **Do not replace this evidence contract or introduce mandatory LLM dependencies.**
3. augustunbear/RestaurantTrafficDiagnosis (development): inspected README.md and AGENTS.md. FastAPI monolith, AI optional, consultant review and source-specific external-AI authorization mandatory. Existing AI runtime modules, config, tests and request paths remain **uninspected**; avoid duplicate gateway design until traced.
4. augustunbear/GastroPreisRadar (development): inspected README.md, AGENTS.md and docs/project/status.md. Rules-first parsing with restricted AI fallback, deterministic validation, provenance and tenant isolation. Existing AI adapter, tests and job retry semantics remain **uninspected**.

## Minimum-change target (proposal, not approval to code)

- First map each existing call site, model/provider configuration, credentials, timeout/retry, output schema, tests and licensing gates; record exact files, line ranges, commit SHAs and behavior differences. Review latest PR/CI and branch HEAD before implementation.
- Prefer a small **optional installable Python package** only if two or more consumers demonstrably need the same adapter. Start with an interface, provider/model ID, timeout, typed errors, usage and request correlation. Evaluate LiteLLM as optional adapter, not required dependency.
- Keep authorization, tenant/case separation, business prompts, source provenance, result review and deterministic validation in consumers. No automatic billable retry without bounded budget and idempotency assessment; never downgrade source-rights restrictions during fallback.
- Preserve existing GeminiExplainer contract in GeoIntelligenceCore; adapt via dependency injection rather than rewriting it.
- No new web console, service, database, model leaderboard, autonomous routing or broad upstream code copy. Preserve MIT attribution if copying substantial code; prefer reimplementation of narrow interfaces where simpler.

## Ordered acceptance gates

A. **Complete code-level audit:** inspect actual source, configs, lockfiles, tests and CI for all four repos; compare route/fallback semantics, data permissions, async behavior and model configuration; write a file-level reuse/keep/change matrix. Update this document with verifiable findings and commit IDs.
B. **Architecture decision:** prove whether shared package beats 2-3 small existing adapters; define stable contract and dependency boundaries, costs and rollback. Obtain review per repository rules.
C. **Implementation only after A+B:** build isolated optional package and deterministic tests for success, schema errors, 429/5xx, timeout, exhausted budget, denied external processing, fallback and secret redaction.
D. **One pilot consumer:** integrate RestaurantTrafficDiagnosis behind default-off flag, test manual path unchanged, permissions and trilingual UI; no cloud activation.
E. Integrate GastroPreisRadar only after price/tenant/collection-job regression; GeoIntelligenceCore last and opt-in only. Keep existing providers and geographic calculations unaffected.

## Explicitly not verified

No local clone, complete file inventory, four-way code diff, test run, CI check, dependency/license transitive audit or live provider calls were performed in this pass. Upstream default-branch search and selected file fetches are insufficient to claim the full audit is complete. Do not mark this plan 'audit passed' or begin shared-module implementation until gate A is closed.
