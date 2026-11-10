# Offline E04 transport facts

The transport slice is implemented by
`geo_intelligence_core.inputs.transport.import_transport` and `TransportFact`.
It accepts caller-supplied facts only. There are no downloads, paid providers,
background refreshes, GTFS interpretation or live-data guarantees. Company
profiles and employee enrichment remain deferred, as does real-source validation.

## Contract

Call `import_transport(records, evidence=[...], purpose='research', as_of=aware_datetime,
context=RequestContext(...))`. Input is a list of dictionaries. Every record has:

- `id`, `kind`, `value`, `unit`, `location` (longitude/latitude Point).
- Explicit timezone-aware `valid_from`, `valid_until`, `measured_at`.
- Nonempty unique `evidence_ids`, all resolving to supplied Evidence.

Supported kinds are `parking_capacity`, `parking_free_spaces`, `parking_fee`,
`accessibility`, `cycling_restriction`, and `construction`. Counts require a
nonnegative strict integer and `unit='spaces'`. Other kinds require a nonblank
caller-written statement and `unit='statement'`. Fee statements preserve their
currency, charging period and conditions as supplied; the importer does not
parse or normalize tariffs. Unknown properties and kinds are rejected.

Accessibility, cycling restrictions and construction additionally require
`segment_ref` and `direction` (`forward`, `backward`, `both`). Direction is relative
to the caller's referenced segment orientation, which the caller must document.
Location alone never establishes a restricted segment. Periods must be positive;
validity is half-open `[valid_from, valid_until)`. Observations and evidence cannot
be dated after `as_of`. All facts must be valid at that requested instant. A
historical `as_of` imports historical facts only, not current availability.

## Fail-closed and bounded

The fixed bounds are 1,000 facts, 100 evidence entries and 1 MiB of JSON-encoded
records plus evidence. Preflight rejects text fields above 65,536 characters,
more than 50,000 visited values or nesting deeper than 16 before serialization.
IDs must be unique and every supplied source must be used
including rejecting unused evidence for an empty batch. Each source must explicitly grant `use` for exactly the
requested purpose. Unknown or denied rights do not grant use. Rights are supplied
by the caller, not independently verified by this library. Retention, caching,
display, export and redistribution require their separate permissions.

Imports are atomic: malformed inputs return `invalid_input` with no facts or
source content. Restricted rights and expired/future validity return `unavailable`
with no facts. An empty list returns `no_results`, never a zero parking count.
Malformed request context returns `invalid_input` with a safe fallback request ID
`transport-invalid-input`. Diagnostics do not echo arbitrary input. Success returns immutable typed facts
with the original evidence and request context. No omitted measurement is filled
with zero, no parking capacity becomes free spaces, and a source label never
becomes a live-data assertion. The importer neither assesses nor infers child
safety, route safety, frequency or accessibility for an ordinary route.

## Synthetic example

A record with `kind='parking_capacity', value=80, unit='spaces'` represents 80
capacity spaces, not 80 currently available spaces. Free spaces require a separate
`parking_free_spaces` observation and its own explicit validity. The unit tests
use synthetic coordinates and evidence, enforce an offline network guard, and
cover atomicity, purpose/rights, scope, validity, numeric types and bounds.

No provider has been activated and no real transport coverage has been validated.
