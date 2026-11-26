# Offline snapshot-history comparison (synthetic E02 slice)

This unmerged source candidate provides a small, domain-neutral history contract.
It does **not** complete E02 acceptance: two legal real snapshots and their
consumer/source-rights/budget acceptance are not available. No source is activated,
no data collected, and no scheduler, watch runner, persistence or notification is
created. Existing public V1 models and package-root exports are unchanged.

## Use

```python
from geo_intelligence_core.evidence import snapshot
from geo_intelligence_core.history import compare_snapshots
from geo_intelligence_core.models.change import WatchSpec

# before_analysis and after_analysis are authorized caller-owned Analysis objects.
before = snapshot(before_analysis, 'planning').data
after = snapshot(after_analysis, 'planning').data
result = compare_snapshots(before, after)
watch = WatchSpec(topics=('places',), changes=('source_record_missing',))
```

Check each snapshot operation's status before consuming its data. The comparison
also checks purpose, schema version, canonical hash, retained evidence, use and
retention rights, topic context/status, data completeness and query conditions.
Hashes detect accidental changes; they are not signatures or access control.
Callers must authorize both inputs in the same case. Retained snapshots scrub
scope tokens, so this function cannot prove that two snapshots belong to the same
case. No I/O or provider calls occur.

The return type is `Result[tuple[Change, ...]]`. The tuple preserves the existing
immutable-model convention and serializes to a JSON array without list/tuple
serializer warnings. An `ok` empty tuple means no supported fact changed under
identical known conditions. An unsafe comparison returns `data=None`, with an
explicit issue/status, never a successful empty history.

## Supported facts

- PlaceSet topics, including a complete empty PlaceSet with `no_results`. Source
  identities must be unique; counts and per-record evidence must be present and
  consistent. `PlaceSet.coverage` must be an explicit `complete:<coverage-ref>`
  attestation, where the reference is 1–128 ASCII letters, digits, dots,
  underscores, slashes or hyphens and starts with a letter or digit. The
  caller/source must establish that the *retained query result for that scope*
  is complete before making this attestation. It does not assert exhaustive
  real-world coverage. The existing provider default `unknown`, or any other
  string, returns `partial` without a change payload. Record identities are
  not matched by name or address.
- Typed `Analysis.metrics` with complete `MetricConditions`, explicit units,
  nature, non-null values and retained evidence. A metrics-only analysis can use
  exactly one selected, identically named topic as its null-data evidence
  container. Multiple null topics or a mixture of null and PlaceSet topics are
  incomplete. Zero is a value; null never becomes zero.
- The same contracts work for food-service, retail and education profiles.

A `source_record` change is `source_record_added`, `source_record_missing`,
`source_record_updated` or `metric_changed`. Before/after payloads remain typed
Place or Metric objects. A missing record means only that it is absent from the
second retained source result. It never means closed, moved, or no longer present
in the real world. Changed raw opening-hours text is a source-record update, not
an interpreted operating-status change. Every change remains `unverified`.

`method` / `conditions_changed` carries typed HistoryConditions and suppresses all
record deltas for that comparison. Conditions include location versions,
caller query parameters (`effective_conditions`) and retained serving provenance
(`topic_provenance`, keyed by topic and then by field). When both snapshots lack
serving provenance, comparison uses the remaining conditions. If provenance is
present on only one side, it counts as a conditions change. Other conditions include
profile/template/method versions, selected topics, source
identity/query reference/method/reference and valid periods, coverage, methods
resolved to each shared record or metric, metric
conditions, units and nature. Request IDs, retrieval timestamps, evidence IDs,
dictionary key order, record order and category order do not themselves create
fact changes. Entity-reference components are percent-encoded before joining with
`/` and `:` so source keys containing separators remain distinct.

Change evidence IDs reference the two input snapshots, including both sides of an
updated record. Keep those snapshots alongside the result; evidence IDs are not a
new global namespace, and rights are not expanded by comparison. This function is
not an export/redistribution authorization. It does not integrate with the existing
snapshot or export pipeline for histories.

## Explicit limits and failure semantics

- Purpose/integrity/schema/retained-evidence/rights/identity inconsistencies return
  `invalid_input` with no change payload. Failure responses do not echo untrusted
  snapshot conditions.
- Redactions, incomplete topic statuses, unknown coverage/conditions, missing
  metrics or data return `partial` with no change payload. Redacted records cannot
  appear as removals.
- Arbitrary dictionaries, routes/matrices, typed-topic metric dictionaries,
  `Analysis.corrections`, `originals`, and derived `comparison` payloads return
  `unsupported`. Manual verification/relocation references need a later typed
  history extension; they are never silently dropped or promoted to a verified
  real-world change by this slice.
- WatchSpec validates topics and change conditions only. It has no clock, interval,
  endpoint, callback or execution method. Consumers own any later scheduling and
  notifications under their own authorization.

Additive schemas are `schemas/v1/change.json`, `history-result.json` and
`watch-spec.json`. No extra dependency or migration is required. Real-source E02
acceptance, manual confirmation history, broader typed topics and consumer
integration remain pending.
