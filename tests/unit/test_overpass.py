import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.providers.overpass import OverpassPlaceProvider
from geo_intelligence_core.places import normalize_places
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.places import Place, SourceKey
from test_places import query

FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/overpass/places.json").read_text())
CONTEXT = RequestContext(request_id="synthetic-test", method_version="osm-v1")

class Gateway:
    def __init__(self, payload=FIXTURE, status=Status.ok):
        self.payload, self.status, self.calls = payload, status, []
        self.providers = {"overpass": ProviderConfig(id="overpass", endpoint="https://example.org")}
        self.policy = UsagePolicy(allowed_capabilities=("places",), max_area_m2=10_000_000.0,
                                  max_geometry_vertices=100, max_items=50, max_response_bytes=100_000,
                                  deadline_s=10.0)

    async def request(self, provider_id, method, path, params, context):
        self.calls.append((provider_id, method, path, params))
        return Result[dict](status=self.status, data=self.payload if self.status == Status.ok else None, context=context)


def search(gateway, categories=("food_service", "office", "parking", "transport_stop")):
    return asyncio.run(OverpassPlaceProvider(gateway).search(query(categories=categories), CONTEXT))


def test_normalized_places_and_bounded_whitelist_query():
    gateway = Gateway()
    result = search(gateway)
    assert result.status == Status.ok and result.data.retrieved_count == 5
    assert result.data.unique_count == 5 and result.data.coverage == "unknown"
    assert len(result.evidence) == 1 and result.evidence[0].rights.attribution
    assert next(p for p in result.data.places if p.source_key.entity_type == "way").point_role == "representative"
    assert next(p for p in result.data.places if p.source_key.entity_id == "7" and p.source_key.entity_type == "node").hours_raw == "Mo-Fr 09:00-17:00"
    assert gateway.calls[0][:3] == ("overpass", "GET", "/api/interpreter")
    statement = gateway.calls[0][3]["data"]
    assert "[timeout:10]" in statement and "[maxsize:100000]" in statement and "out body center qt 50" in statement
    assert "(0.0000000,0.0000000,0.0100000,0.0100000)" in statement
    assert not any("restaurant" in str(p.raw_tags) for p in result.data.places if "office" in p.categories)


def test_partial_remark_and_empty_failure():
    payload = {**FIXTURE, "remark": "runtime error: Query timed out"}
    assert search(Gateway(payload)).status == Status.partial
    assert search(Gateway({"elements": [], "remark": "timeout"})).status == Status.unavailable


def test_parking_and_stop_have_no_invented_capacity_or_timetable():
    result = search(Gateway())
    for p in result.data.places:
        if "parking" in p.categories or "transport_stop" in p.categories:
            assert "capacity" not in p.raw_tags and "frequency" not in p.raw_tags


def test_unknown_category_and_area_cap_preflight_zero_network():
    gateway = Gateway()
    assert search(gateway, ("anything arbitrary",)).status == Status.invalid_input
    gateway.policy = gateway.policy.model_copy(update={"max_area_m2": 1.0})
    assert search(gateway).status == Status.invalid_input
    assert gateway.calls == []


def test_gateway_failure_is_preserved():
    assert search(Gateway(status=Status.rate_limited)).status == Status.rate_limited


def test_response_is_filtered_against_polygon_and_output_limit():
    payload = {"elements": [*FIXTURE["elements"],
                            {"type": "node", "id": 99, "lat": .02, "lon": .02,
                             "tags": {"amenity": "restaurant"}}]}
    gateway = Gateway(payload)
    result = search(gateway)
    assert result.status == Status.ok
    assert result.data.retrieved_count == 6 and result.data.unique_count == 5
    gateway.policy = gateway.policy.model_copy(update={"max_items": 2})
    limited = search(gateway)
    assert limited.status == Status.partial and limited.data.unique_count == 2
    assert limited.data.coverage == "unknown"


def test_empty_clean_response_is_no_results_and_malformed_is_unavailable():
    empty = search(Gateway({"elements": []}))
    assert empty.status == Status.no_results and empty.data.unique_count == 0
    assert search(Gateway({"elements": "malformed"})).status == Status.unavailable


def test_geometry_intersects_cannot_use_overpass_center_only():
    # This way crosses the search region's east edge, but its representative
    # center is outside. The local operation can see the actual footprint.
    crossing = Place(source_key=SourceKey(source_id="osm", entity_type="way", entity_id="900"),
                     point=Point(longitude=.012, latitude=.005), point_role="representative",
                     geometry={"type": "Polygon", "coordinates": [[
                         [.009, .004], [.014, .004], [.014, .006], [.009, .006], [.009, .004]]]},
                     categories=("food_service",))
    intersects = query("geometry_intersects", categories=("food_service",))
    assert normalize_places([crossing], intersects).data.unique_count == 1
    assert normalize_places([crossing], query(categories=("food_service",))).status == Status.no_results

    # Overpass `out body center` omits this footprint. Refuse the requested
    # rule before making a misleading center-only network query.
    gateway = Gateway()
    result = asyncio.run(OverpassPlaceProvider(gateway).search(intersects, CONTEXT))
    assert result.status == Status.unsupported
    assert result.data is None and result.issues[0].code == "geometry_intersects_unavailable"
    assert gateway.calls == []


def test_food_service_subtypes_are_queryable_without_takeaway_duplication():
    gateway = Gateway()
    result = search(gateway, ('restaurant', 'cafe', 'bar', 'fast_food'))
    assert result.status == Status.ok
    assert all(set(p.categories) & {'restaurant', 'cafe', 'bar', 'fast_food'} for p in result.data.places)
    assert any('restaurant' in p.categories and 'food_service' in p.categories for p in result.data.places)
    assert 'takeaway' not in {category for p in result.data.places for category in p.categories}
    assert '["amenity"="restaurant"]' in gateway.calls[0][3]['data']
