# E02 offline snapshot-history slice

Implements the existing [E02 specification](2026-11-04-core-implementation.md#e02历史变化与监测条件表达) as a synthetic offline contract slice. This is not activation or complete E02 acceptance: two legal real snapshots and their consumer/rights/budget acceptance are absent.

## Scope and decisions

Use the existing immutable Snapshot, purpose/rights model, typed PlaceSet/Place and Metric/MetricConditions. Compare factual source records only; emit a method/condition change instead of record deltas when queries, location versions, source methods, coverage or metric conditions differ. Unknown, redacted, unsupported or incomplete inputs must never become empty successful histories. No verified-real-world change, scheduler, notification, network or persistence. Caller retains case-level authorization because snapshots deliberately scrub scope tokens.

An arbitrary JSON diff was rejected because it cannot establish typed facts. A new persistence system was rejected as outside E02. No existing public model or provider code changes are required.

## Execution

- [x] Write offline tests in `tests/unit/test_history.py` for same-query missing/added/updated records, key order stability, condition changes, null/redaction/status handling, typed metrics, rights/purpose/integrity and declarative WatchSpec validation. Observe RED before implementation.
- [x] Implement `compare_snapshots(before: Snapshot, after: Snapshot) -> Result[list[Change]]` in `history.py`, with additive immutable types in `models/change.py`. Only explicit typed fields are compared; method changes suppress factual deltas.
- [x] Add schema round-trip and three-industry regressions, usage and honest status/changelog. Keep shared provider/API files untouched to avoid PRs #41–#44.
- [x] Run focused and full Python 3.12 tests, independent review, fix reproduced findings with RED/GREEN, restore tracked bytecode and commit locally. Do not push, open a PR, merge or deploy.

Review focus: unauthorized evidence, redacted/missing data versus zero; duplicated source identities; query/coverage/method drift; source-record absence never closure; unsupported topic types never silently ignored.
