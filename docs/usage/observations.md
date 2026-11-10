# Offline count observations (E01 partial slice)

`Observation` and `normalize_observation` are available from
`geo_intelligence_core`. These validate caller-supplied synthetic or independently
obtained observations locally. No provider is configured or called. The
observation slice does not implement collection, attendance estimation, time
filtering in `analyze`, or observation comparison. A separate optional
[`evaluate_opening_hours` API](opening-hours.md) now evaluates conservative
non-holiday schedules offline; it does not change observation normalization.
E01 is not complete and temporal A07/live source acceptance is not claimed.

## Input contract

- Supply an opaque `id` and exactly one WGS84 `Point` or existing `Region`.
  Region geometry/boundary metadata is preserved, not geometrically validated
  by this function. The caller must establish the validity of a supplied region.
- Supply offset-aware `start` and `end` instants (datetime or ISO-8601 text),
  with end strictly after start. They normalize to UTC before ordering, including
  across DST. Naive local times are rejected; no offset or fold is guessed.
  The host must provide the IANA timezone database used by Python `zoneinfo`.
  Supply a valid IANA `timezone` separately for local display. It does not
  reinterpret the input instants or assert their original wall offsets match
  that zone. UTC input instants with `Europe/Berlin` are therefore valid.
- Supply source descriptions for `direction`, `method`, and `dedupe`. They
  must be nonblank. Use an explicit description such as `unknown` when a
  direction or deduplication method is unknown. Descriptions are preserved,
  not checked against the actual collection procedure.
- `count_object` is explicitly `person` or `visit`. `count` is a strict
  nonnegative integer or null. Booleans, floats and numeric strings are invalid.
  Null or omitted count requires a nonblank `missing_reason`; a measured count,
  including zero, forbids a missing reason.
- Supply at least one full `Evidence` with unique IDs, retaining method version,
  source identity, timestamps, quality and `Rights`. No use, retain, cache,
  display, export or redistribution permission is inferred or upgraded.

Direct invalid model construction raises Pydantic `ValidationError`. Calling
`normalize_observation` with a mapping or model returns `invalid_input` and null
data for invalid input, without echoing payload or validation internals. Valid
measured counts return `ok`; missing counts return `unknown` with the observation,
missing reason and evidence retained. Result context records
`observation-normalization-v1` and uses the observation ID as the request ID.
All validation is local. It does not assert source quality or rights approval.
The returned in-memory object is not authorization to persist or share data;
callers must enforce source rights and case-level access themselves. This slice
has no snapshot or export integration.

## Synthetic example

```python
from geo_intelligence_core import Observation, normalize_observation

# evidence is a caller-supplied Evidence object with its original rights.
observation = Observation(
    id="synthetic-counter-1",
    point={"longitude": 11, "latitude": 49},
    start="2026-10-25T02:30:00+02:00",
    end="2026-10-25T02:30:00+01:00",
    timezone="Europe/Berlin",
    direction="northbound",
    count_object="visit",
    count=0,
    method="synthetic-manual-v1",
    dedupe="unknown",
    evidence=[evidence],
)
result = normalize_observation(observation)
assert result.status == "ok" and result.data.count == 0
```

The repeated local hour spans one elapsed hour, not zero. A count of visits is
never converted to a count of distinct people. Different intervals retain their
original counts and instants: this function computes no rates, differences,
rankings or comparability flags. Equal counts or successful normalization do
not establish that durations, spatial scopes, methods or sources are comparable.
Annual population is not an observation of lunchtime flow.

`schemas/v1/observation.json` is additive and unreleased; existing schemas are
unchanged. It describes structural types. Cross-field rules, IANA zone existence,
aware instants and interval order also require runtime validation. Existing
consumer contracts do not gain an observation topic automatically.
