# E04 COMPANY offline import: partial implementation

The additive `geo_intelligence_core.inputs.company.import_company(records, evidence, purpose=...)`
validates explicitly caller-supplied Python dictionaries only. It does not fetch
URLs, files, registries or providers. No source is activated, and import does not
retain, cache, display, export or redistribute data. Consumers must separately
check those rights. A valid result is a preserved source assertion, not verified
company activity or workforce.

## Caller contract

- Pass an `Evidence` instance with explicit `use=allowed` and a nonblank exact
  matching `permitted_purpose`. Unknown/denied use or mismatched purpose returns
  `disabled`, with null data. No inferred rights or default purpose.
- Pass a list of at most 1,000 dictionaries. Every row requires nonblank `id`,
  `source_id`, `source_ref`, and an explicit `site_role`. Source ID and source
  reference must match the batch Evidence. IDs must be unique within the batch.
- Roles are `unknown`, `registered_address`, `headquarters`, `branch` or
  `operating_site`. They are caller assertions, not inferred classifications.
  A registered address never becomes an operating site automatically.
- Each row needs a valid WGS84 `point` (longitude/latitude), or an `address`
  with at least one nonblank ordinary address field. A legal registered address
  may lack a point. This import does not geocode or confirm spatial accuracy.
- Optional `legal_entity_ref` and `industry` are nonblank source text. No
  industry profile, category mapping or industry-specific business meaning is
  imposed. No entity resolution or cross-batch deduplication is performed.
- Optional `workforce` is null when unknown. A supplied fact requires explicit
  `scope` of `site` or `legal_entity` and either nonnegative integer `count` or
  both ordered nonnegative integer `lower`/`upper`. Booleans, numeric strings,
  fractional numbers, mixed count/range, and incomplete ranges are rejected.
  Legal-entity scope also requires `legal_entity_ref`. A headquarters' entity
  workforce never propagates to branches; even identical range endpoints stay
  a range with null count. Values are not aggregated.
- Import attaches the supplied Evidence ID to each output; input `evidence_ids`
  and unknown fields are rejected. Input fields and separate rights are
  preserved, not silently trimmed or upgraded. The Evidence reference/valid
  periods and quality describe the whole batch; use separate batches when
  records have different provenance, periods or rights.

The output is `Result[tuple[ImportedCompanySite, ...]]`. Existing `CompanySite`
remains unchanged. Valid nonempty batches return `ok`, authorized empty batches
return `no_results` with an empty tuple. Any malformed record, duplicate ID or
source mismatch rejects the entire batch with `invalid_input` and null data.
The output context records `company-import-v1` and the requested purpose.
The additive JSON schema is `schemas/v1/company-import-result.json`.
It describes structural shapes; cross-field rules such as exact-count versus
range, legal-entity workforce references, nonblank addresses and batch rights
must also be checked by the runtime importer.

## Acceptance still absent

All automated examples are synthetic. No real company source, licensed fields,
source-rights acceptance, operating-site accuracy, coverage denominator, workforce
accuracy or field acceptance has been verified. The separate offline transport slice accepts caller-supplied parking and restriction facts. No live transport data, temporal integration, downloads, scheduling, consumer integration, release or deployment is included. E04 remains partial and real-source
enablement remains blocked pending explicit source/user/purpose/rights acceptance.

# Offline E04 transport facts

The transport slice is implemented by
`geo_intelligence_core.inputs.transport.import_transport` and `TransportFact`.
It accepts caller-supplied facts only. There are no downloads, paid providers,
background refreshes, GTFS interpretation or live-data guarantees. Company records are supported by a separate offline caller-supplied importer, but real-source validation remains deferred.

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
