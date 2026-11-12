# V1 contract — implementation target, not implemented

Planning baseline: 2026-11-04, main `99bce3d90186acf8a431896341ab95fc66708ac7`.
This replaces the earlier illustrative signatures. [Implementation plan](../superpowers/plans/2026-11-04-core-implementation.md) assigns implementation and tests. JSON schema target `1.0` is independent of package pre-release `0.1.0a1`; neither is released.

## 1. Conventions and model ownership
Public Python package: `geo_intelligence_core`. Pydantic 2 models reject extra fields and non-finite numbers; typed quantities do not coerce strings or booleans into numbers. JSON objects contain plain data, never Shapely, DataFrame, HTTP responses or vendor objects.
GeoJSON coordinates are WGS84 [longitude, latitude]. Point fields are explicit `longitude`, `latitude`; each is bounded. Distances meters, durations seconds, timestamps offset-aware RFC3339 normalized to UTC; local time conditions include an IANA timezone.
Models are immutable; updates return new values. IDs are opaque strings; caller identities and case authorization are outside this library.

| File under src/geo_intelligence_core/models/ | Types / required semantics |
|---|---|
| common.py | Status, Issue(code, message_key, safe_params), `Result[T]` (schema_version, status, data, issues, evidence, context); recoveries are typed suggestions, never automatic source changes |
| evidence.py | Evidence(id, source_id, source_type, source_ref, retrieved_at, reference_period, valid_period, method_version, rights, quality); unknown dates explicit null with issue |
| location.py | Point; Address(country_code, postcode, locality, street, house_number, native_names); Candidate(id, point, address, source_ref, precision); Location(id, version, point, address, entrances, confirmation); Entrance(id, point, role, modes); Confirmation(method, at, evidence_ids) |
| requests.py | SearchRequest(text, language, country_codes, bbox, near, limit); ReverseRequest(point, language); ConfirmRequest(candidate or manual point/address, entrances, confirmation); RequestContext(request_id, location_versions, effective_conditions, profile_ref, template_ref, method_version, scope_token nullable) |
| spatial.py | Region(id, version, geometry, method, source_ref, boundary_rule); GeometryLimits(max_area_m2, max_vertices); CircleRequest(center, radius_m); SpatialOperation(union/intersection/difference); RouteRequest(origin, destination, mode, time); MatrixRequest(origins, destinations, mode, time); CatchmentRequest(location, entrance_id, direction, mode, durations_s, time); Route(distance_m, duration_s, geometry, mode, origin, destination); TravelMatrix(cells with origin_id/destination_id, duration_s nullable and per-cell status); Catchment(region, direction, mode, duration_s, time) |
| places.py | Place(source_key, native_names, point, geometry, point_role, address, categories, raw_tags, hours_raw, contacts, evidence_ids); PlaceQuery(region, category_ids, mapping_version, boundary_rule); PlaceSet(places, retrieved_count, unique_count, coverage, duplicate_candidates); CompanySite(place, site_role, legal_entity_ref, workforce) |
| configuration.py | Profile(id, version, category_ids, defaults, display_groups); Template(id, version, profile_ref, required_inputs, required_topics, optional_topics, defaults); TopicSelection(id, required); AnalyzeRequest(locations, topics: list[TopicSelection], regions, time, explicit_parameters, profile_ref, template_ref, scope_token nullable); EffectiveConfig(values, provenance_by_field, profile_ref, template_ref); TimeCondition(kind, instant/start/end, timezone, label) |
| analysis.py | Analysis(request_context, topic_results: mapping[str, Result], selected_topics); Comparison(rows with location_version, metric_id, value nullable, difference nullable, unit, evidence_ids and comparability_issues); Snapshot(schema_version, analysis, canonical_hash, retained_evidence_ids, redactions); Correction(target_ref, action, replacement: Place or Metric or null, attachments: list[Evidence], evidence_ids, reason, scope_token, at); Metric(value nullable, unit, nature, numerator, denominator, evidence_ids) |
| policy.py | UsagePolicy(allowed_endpoints, allowed_capabilities, max_calls_per_run, max_concurrency, max_area_m2, max_geometry_vertices, max_items, deadline_s, max_response_bytes, cost_ceiling, currency, pricing_ref, period_limits, cache_policy); ProviderConfig(id, endpoint, capability_flags, rights_ref, credential_handle, authentication_required=true, authentication_header="Authorization"); Budget reservation interface defined below |

`Rights` has separate permissions for use, retain, cache, display, export and redistribute, each allowed/denied/unknown, attribution text, license/source URL, checked_at and permitted purpose. Unknown is not permission. Evidence `Quality` separates precision, coverage, freshness, source reliability, uncertainty, verification; no single confidence score.
`Metric.nature` is measured/derived/estimated/unverified; numeric zero needs evidence and valid semantics. Suppressed, missing and unknown remain distinguishable through status/issue and nullable value.
`TimeCondition.kind`: depart_at / arrive_by / interval / descriptive. Unsupported temporal filtering is reported; descriptive labels cannot change data.
The `instant`, `start` and `end` inputs, when present, must be offset-aware
`datetime` values or ISO-8601 text with an explicit offset. Numeric values and
numeric timestamp strings are not interpreted as Unix seconds or milliseconds.
`source_key`: (source_id, entity_type, entity_id), including OSM node/way/relation.
`Region.boundary_rule`: point_covers (boundary included) / point_within (excluded) / geometry_intersects; geometry_intersects counts entities once and is not an area allocation algorithm.
`Location.version` increments on confirmation changes; snapshots reference exact versions.
 `scope_token` is opaque caller-supplied isolation context, not authentication. Propagate AnalyzeRequest.scope_token into RequestContext and the internal cache key; never send it to external providers. A direct provider caller supplies it in RequestContext. Missing scope forbids private caching/retention rather than choosing public scope; public cache accepts only explicitly public, permitted source records. Consumer verifies authorization.
`TopicSelection.required` defaults false; the effective required set is the union of caller-required topics and template required_topics. A caller cannot downgrade a template requirement. Reject duplicate topic IDs or missing required selections before execution. Analysis.selected_topics stores IDs; effective required flags remain in request_context.
`Correction.action` is confirm/correct/exclude/attach. correct requires a replacement of the same entity type and target identity; confirm/exclude require replacement=null, attach requires nonempty attachments. Only allow corrections to declared factual fields, never source identities, original provenance or rights. Preserve originals and append the scoped correction. Location changes use confirm_location and a new Location.version instead.
`GeometryLimits` is a separate offline value object: positive finite max_area_m2 and positive max_vertices. circle/combine require it explicitly; analyze derives max_area_m2 and max_vertices from trusted UsagePolicy.max_area_m2 and UsagePolicy.max_geometry_vertices respectively and cannot accept larger limits from caller overrides. Limits apply before expensive work where estimable and to final output; input vertex count is checked before polygon operations. No network policy is required for direct local geometry calls.

## 2. Status and completion rules
Status values: `ok, partial, no_results, not_collected, disabled, unconfigured, unsupported, unavailable, rate_limited, invalid_input, conflict, unknown`.

- ok: requested operation completed with usable data; not a claim of real-world exhaustive coverage.
- no_results: completed search found no matching records; PlaceSet may contain [] and unique_count=0, but no claim of zero real facilities.
- partial: at least one selected topic/cell succeeded and another selected part failed or is incomplete. Preserve all topic statuses.
- disabled/unconfigured/unsupported/unavailable/rate_limited: data=null for that failed topic; do not fabricate empty successful datasets.
- conflict: conflicting evidence retained; no ungrounded average.
- invalid_input: validation failure, no provider calls.
- unknown: data or interpretation cannot be established, not closed/zero.
- not_collected: no execution attempted.

Selected population disabled + POI ok => analysis partial. Population not selected + all selected topics ok => analysis ok. All selected topics disabled => disabled; all unavailable => unavailable; heterogeneous failures without any usable result => unavailable plus per-topic reasons, never partial success. Required input/capability preflight failure blocks execution and returns its status with topic diagnostics. Optional selected topic failure does not discard other results.
Candidate list never creates confirmed Location automatically.
No hidden fallback: recoveries are suggestions; an explicit subsequent request changes source/method and receives a new context.

## 3. Public function / port target
All Result returns include context, evidence and issues. Validation services convert Pydantic validation errors to invalid_input; direct model construction may raise ValidationError.

```python
# location.py (offline)
def confirm_location(request: ConfirmRequest, previous: Location | None = None) -> Result[Location]: ...

# ports.py (async external providers)
class LocationResolver(Protocol):
    async def search(self, request: SearchRequest, context: RequestContext) -> Result[list[Candidate]]: ...
    async def reverse(self, request: ReverseRequest, context: RequestContext) -> Result[list[Candidate]]: ...
class PlaceProvider(Protocol):
    async def search(self, request: PlaceQuery, context: RequestContext) -> Result[PlaceSet]: ...
class RoutingProvider(Protocol):
    async def route(self, request: RouteRequest, context: RequestContext) -> Result[Route]: ...
    async def matrix(self, request: MatrixRequest, context: RequestContext) -> Result[TravelMatrix]: ...
    async def catchments(self, request: CatchmentRequest, context: RequestContext) -> Result[list[Catchment]]: ...
class Budget(Protocol):
    async def reserve(self, provider_id: str, calls: int, estimated_cost: Decimal) -> bool: ...
    async def record(self, provider_id: str, actual_cost: Decimal) -> None: ...
# Reserve is atomic and counted BEFORE each attempt, including retries.
# period_limits/shared enforcement belong to caller-supplied Budget; in-memory
# reference implementation supports a single process only and must declare it.

# geometry.py (geometry extra)
def distance_m(a: Point, b: Point) -> float: ...
def circle(request: CircleRequest, *, limits: GeometryLimits) -> Result[Region]: ...
def combine(regions: list[Region], operation: SpatialOperation, *, limits: GeometryLimits) -> Result[Region]: ...

# places.py
def normalize_places(records: list[Place], query: PlaceQuery) -> Result[PlaceSet]: ...

# configuration.py / analysis.py
def resolve_config(request: AnalyzeRequest, profile: Profile | None,
                   template: Template | None, policy: UsagePolicy) -> Result[EffectiveConfig]: ...
async def analyze(request: AnalyzeRequest, providers: ProviderRegistry,
                  policy: UsagePolicy, budget: Budget) -> Result[Analysis]: ...
# ProviderRegistry maps capability IDs to configured ports; no runtime plugin download.
def compare(analyses: list[Analysis], metric_ids: list[str]) -> Result[Comparison]: ...

# evidence.py / export.py
def apply_correction(analysis: Analysis, correction: Correction, scope_token: str) -> Result[Analysis]: ...
def snapshot(analysis: Analysis, purpose: str) -> Result[Snapshot]: ...
def export_result(snapshot: Snapshot, format: Literal["json", "geojson", "csv"],
                  language: Literal["de", "zh-CN", "en"], purpose: str) -> Result[str]: ...
```

Missing optional package raises a controlled capability-unavailable result at the public service boundary, not a top-level import error.
No REST API, scheduler, database or authentication system in first release.

## 4. First template contracts
Profiles and templates ship as package resources, independent versions. No shared arbitrary radius; caller must supply explicit region or permitted radius/duration per selected topic.

| Template | Required | Optional and completion |
|---|---|---|
| surroundings / T-01 | One confirmed location, nonempty selected topics, region per spatial topic; required topics = caller selection marked required | Allowed topics places, transport_places, company_sites, routes, population_reference. Population off by default; all selected topics reported. No fixed mandatory population/route provider |
| venue-discovery / T-02 | Confirmed location or explicit Region, categories (food-service profile supplies defaults), places required | Route times only if explicitly selected; raw hours may be unknown; no competitor/price inference |
| location-comparison / T-03 | At least two confirmed locations, same selected metrics and explicit scope/time/method per location; comparison required | Routes and population optional; missing/incomparable cells have null value + reason, no rank |

Food-service mapping v1 starts with OSM amenity=restaurant/cafe/bar/fast_food; takeaway is a qualifier, not automatic new business type or a duplicate entity. Related topics use generic office, shop, education, accommodation, parking and transit categories in separate source mapping. Unknown tags remain unknown; multiple tags retained. Mapping cannot imply completeness.
Retail/education fixtures supply their own category selections and time/entrance conditions without production profiles.

## 5. Versioning and rights
Canonical JSON for hashes sorts keys and normalizes units/time; semantically ordered lists retain order, entity collections sort by stable source key. Exclude volatile retrieval execution IDs only via documented hash projection; keep them in snapshot metadata. Hash is not evidence storage authorization.
For first implementation choose a single canonical_hash over all retained snapshot content except canonical_hash itself; snapshot comparisons ignore retrieval metadata through explicit comparability rules, not hash equality alone.
Do not retain prohibited fields to achieve reproduction. Record redactions and reduced reproducibility. Export checks each contributing source; derived output does not erase source rights.
Schema changes update generated schemas, fixtures and changelog; breaking published shape requires a new schema version. Pre-release package consumers pin commit/tag. Adopt no implicit production compatibility until first tested release.

## FF-03 unreleased ProviderConfig compatibility decision (2026-11-06)

The two authentication fields are additive inputs with defaults: older five-field
configurations remain readable by the updated model. New serialized payloads
include both fields; older strict readers reject them. Upgrade readers before
exchanging these configurations, preserve the fields when forwarding, and do not
strip them to bypass an authentication requirement. Known hosted ORS still needs
Authorization regardless of an anonymous-instance setting.

This is an explicitly revised **unreleased V1 target**, not a change to a released
V1 contract. Schema identifier 1.0 and source-candidate package 0.1.0a1 remain
unchanged for this unpublished development series; they are not sufficient
artifact identities. Use the exact commit, wheel SHA and package fingerprint.
A subsequent published distribution must use a new pre-release version instead
of replacing any previously distributed wheel under the same version. Existing
consumer pins are immutable and require their own reviewed upgrade; no new core
commit silently updates them. This decision does not assert that old readers can
consume new serialized configurations or that any source is live-approved.
