# Location resolution (P05)

`PhotonResolver` implements forward search and reverse lookup using the optional
HTTPX provider extra and a caller-configured `HttpGateway`. Importing it performs
no network access. No endpoint, account, rights grant, or quota is shipped.
Supply an approved HTTPS origin in `ProviderConfig` and `UsagePolicy`, an atomic
`Budget`, a finite deadline, response byte ceiling, call/cost limits and a
documented per-call cost. See [provider activation](../operations/provider-activation.md).

Declare `PhotonCapabilities` for the installed Photon API v1 deployment after
checking its supported filters and languages. The adapter maps `/api` `q`,
`lang`, `limit`, optional `countrycode`, `bbox` and `lon`/`lat` bias; `/reverse`
uses `lon`, `lat`, `lang`, `limit`. `near` changes ranking only. The resolver
rechecks single-country and bounding-box constraints on every returned point.
Multiple countries or an unavailable hard server filter return `unsupported`
before network access. Because the gateway accepts scalar parameter values,
repeated `countrycode` parameters are not sent. An invalid range, whitespace
query, overlong query, or a limit above the configured bound returns
`invalid_input`. Set a minimum query length for autocomplete; callers debounce
and cancel stale tasks. Cancellation propagates to HTTPX without another retry.

Photon returns GeoJSON features with OSM type/ID. Each candidate keeps the OSM
source identity, address fields, and a conservative precision (`house` only
when street and house number exist, `street`, `locality`, or `unknown`). A house
address is not an entrance survey. `Address.native_names[effective_language]`
contains the returned `name`. Only an explicit `extra.name` is additionally
recorded under `und` as an original OSM name; a translated `name` alone cannot
prove the original. Photon language selection depends on server index and its
fallback chain. An unsupported requested language uses the declared fallback
and records `language_fallback` plus `context.effective_conditions.language`.
Translation availability for an individual feature is not verifiable from the
basic response. Do not label an entire result set as translated.

For a named OSM `highway` feature that Photon explicitly classifies as
`type=street`, the name supplies `Address.street` when the separate `street`
property is absent. This yields street precision without inventing a house
number. Neither `type=street` alone nor `osm_key=highway` alone changes the
precision; the provider's street layer and OSM key must agree.

Successful empty results return `no_results` and an empty candidate list.
Network failures and malformed responses return `unavailable` with null data.
If Photon repeats an OSM type/ID in one response, the entire response is
`unavailable` with `invalid_response`, even if the repeated records are byte-for-byte
identical or a local bounding filter would remove them. One OSM identity cannot
represent two separately confirmable candidates. The resolver never silently
deduplicates a response to make a quality gate pass. A distinct OSM type with
the same numeric ID remains a distinct candidate.
Candidates never confirm a `Location`; the caller must explicitly select one
and call `confirm_location`, or provide a manual point. No automatic first match
or silent substitution of old data occurs.

## German address review sample protocol

For an approved instance, prepare separate human-labeled samples for a large
city, a suburb and a rural place; include identical town names in distinct
regions, umlauts/transliteration, a known house number, an address lacking a
house number, and a coordinate for reverse lookup. Record expected candidate
identity, allowable geographic extent, address components, language requested
and actually returned, and whether a surveyed entrance exists. Compare all
candidates rather than top-one accuracy alone. Record provider version, index
vintage, terms/rights, quota, time, and sample provenance. Obtain permission
before sending potentially personal addresses. Keep real address samples and
tokens out of git; P13 owns opt-in live validation and activation decisions.
