# First release decision — pending P12/P13

Updated 2026-11-05. P12 merged as main `2b656b3df0a190040d7b54c1c85afa0ebd8c226d`, PR #20. The locally observed candidate wheel is `geo_intelligence_core-0.1.0a1-py3-none-any.whl`, SHA-256 `3398d79eec5c68530c098f7ec9dc2338ea1cc743ac79b1e2f7c4baab0ffc6c3c` at `/tmp/pytest-of-agent/pytest-7/dist0/`. It is ephemeral and not a published artifact. This is an offline/preflight decision; no release or live activation has been approved or observed.

P13 regression on the synchronized P12 source: `PYTHONPATH=src /workspace/scratch/73c39fd27714/p01-venv/bin/python -m pytest -q` → **130 passed, 3 skipped** in 82.05 s. The three skips are Photon, ORS and Overpass live placeholders. The one added passing test is a synthetic single-process budget reservation replay; no geographic or service latency was measured. Local source has been synchronized from P12's working snapshot; the remote base commit is recorded above.

| Gate | Status | Evidence / next action |
| --- | --- | --- |
| A01 offline manual location and core contract | pass (offline) | P12 PR #20 reports clean Python 3.12 wheel/sdist installs and synthetic consumer contract. Candidate hash above. |
| A02 Photon German address quality | blocked | Approved instance, rights and six labeled strata, predeclared precision/ambiguity thresholds, measured results. |
| A03 local geometry | pass (offline) | P12 clean geometry-extra install and offline contracts in PR #20. |
| A04 Overpass places and category coverage | blocked | Approved origin/rights and representative bounded regions, independent POI audit. |
| A05 ORS routing, matrix and isochrone | blocked | Current complete HeiGIT account terms/quotas, key, directional/no-route live checks and output licence decision. |
| A09 configurations, rights and evidence | pass (offline contracts) | P12 synthetic consumer and purpose-bound export tests in PR #20; real-source retention/export rights remain provider gates. |
| A10 comparisons | pass (offline contracts) | P12 synthetic comparison consumer contract in PR #20. |
| A11 budget and performance | blocked (live) | Frozen workload/thresholds and calls, latency, memory, cost; shared atomic budget if multiple workers. Synthetic single-process replay is no substitute. |
| A06/A08 | not_applicable | No population calculation in the first scope. |
| A07 | not_applicable | Deferred until E01 temporal capability. |

`pass` requires a linked raw evidence path and reviewer, `fail` records unmet criteria, and `blocked` means no valid measurement. Mock/CI success does not resolve a live gate. If P12 passes while providers remain blocked or fail, label the artifact **offline/preview only**, enumerate disabled capabilities and do not call it production ready. Release/version tagging and deployment require a separate decision.
