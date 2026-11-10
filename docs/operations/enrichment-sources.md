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

## Acceptance still absent

All automated examples are synthetic. No real company source, licensed fields,
source-rights acceptance, operating-site accuracy, coverage denominator, workforce
accuracy or field acceptance has been verified. No transport enrichment,
parking/availability facts, temporal integration, downloads, scheduling, consumer
integration, release or deployment is included. E04 remains partial and real-source
enablement remains blocked pending explicit source/user/purpose/rights acceptance.
