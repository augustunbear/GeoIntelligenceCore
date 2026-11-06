import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Confirmation, Entrance, Location, Point
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.spatial import CatchmentRequest
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.http import HttpGateway
from geo_intelligence_core.providers.ors import OrsRoutingProvider

FIX = Path(__file__).parents[1] / 'fixtures' / 'ors' / 'isochrones.json'
CTX = RequestContext(request_id='synthetic')
P = Point(longitude=10.0, latitude=50.0)
LOC = Location(id='synthetic', version=1, point=P, confirmation=Confirmation(
    method='manual', at=datetime(2026, 11, 4, tzinfo=timezone.utc), evidence_ids=('manual',)),
    entrances=(Entrance(id='door', point=Point(longitude=10.001, latitude=50.001), role='public', modes=('walking',)),))


def run(c):
    return asyncio.run(c)


def fixture():
    return json.loads(FIX.read_text())


def provider(response, *, inbound=False, status=200, limits=True):
    seen = []
    def reply(req):
        seen.append(req)
        return httpx.Response(status, json=response)
    policy = UsagePolicy(allowed_endpoints=('https://api.heigit.org',),
        allowed_capabilities=('catchment',), max_calls_per_run=2, max_response_bytes=20000,
        deadline_s=3.0, cost_ceiling=Decimal('0'), currency='EUR', pricing_ref='synthetic',
        max_area_m2=1e10 if limits else None, max_geometry_vertices=500 if limits else None)
    config = ProviderConfig(id='ors', endpoint='https://api.heigit.org/openrouteservice',
        capability_flags={'catchment': True, 'catchment_inbound': inbound}, credential_handle='synthetic')
    gateway = HttpGateway({'ors': config}, policy, InMemoryBudget(2, Decimal('0')),
        resolver=lambda _: ['93.184.215.14'], transport=httpx.MockTransport(reply),
        cost_per_call=Decimal('0'), headers={'Authorization': 'synthetic-secret'})
    return OrsRoutingProvider(gateway), seen


def request(direction='outbound', **changes):
    return CatchmentRequest(**dict(location=LOC, entrance_id='door', direction=direction,
                            mode='walking', durations_s=(900, 300, 600, 300)) | changes)


def test_barrier_multipolygon_holes_and_sorted_ranges():
    p, seen = provider(fixture())
    result = run(p.catchments(request(), CTX))
    assert result.status == Status.ok and [c.duration_s for c in result.data] == [300, 600, 900]
    assert all(c.direction == 'outbound' and c.region.method == 'ors_isochrone_time' for c in result.data)
    assert result.data[0].region.geometry['type'] == 'MultiPolygon'
    assert len(result.data[0].region.geometry['coordinates']) == 2
    assert len(result.data[0].region.geometry['coordinates'][0]) == 2  # barrier hole, not a circle
    body = json.loads(seen[0].content)
    assert body == {'locations': [[10.001, 50.001]], 'range': [300, 600, 900],
                    'range_type': 'time', 'location_type': 'start'}
    assert seen[0].url.path == '/openrouteservice/v2/isochrones/foot-walking'


def test_integral_float_isochrone_values_from_live_api():
    raw = fixture()
    for feature in raw['features']:
        feature['properties']['value'] = float(feature['properties']['value'])
    raw['metadata']['query']['range'] = [300.0, 600.0, 900.0]
    p, _ = provider(raw)
    result = run(p.catchments(request(), CTX))
    assert result.status == Status.ok
    assert [c.duration_s for c in result.data] == [300, 600, 900]
    raw['features'][0]['properties']['value'] = 300.5
    p, _ = provider(raw)
    assert run(p.catchments(request(), CTX)).status == Status.unknown


def test_inbound_requires_capability_and_echoed_direction():
    p, seen = provider(fixture())
    result = run(p.catchments(request('inbound'), CTX))
    assert result.status == Status.unsupported and result.data is None and not seen
    inbound = fixture()
    inbound['metadata']['query']['location_type'] = 'destination'
    p, seen = provider(inbound, inbound=True)
    result = run(p.catchments(request('inbound'), CTX))
    assert result.status == Status.ok
    assert json.loads(seen[0].content)['location_type'] == 'destination'
    p, _ = provider(fixture(), inbound=True)
    assert run(p.catchments(request('inbound'), CTX)).status == Status.unknown


def test_non_nested_polygons_are_partial_without_repair():
    raw = fixture()
    raw['features'][1]['geometry'] = {'type': 'Polygon', 'coordinates': [[[10.04, 50.04], [10.05, 50.04], [10.05, 50.05], [10.04, 50.04]]]}
    p, _ = provider(raw)
    result = run(p.catchments(request(), CTX))
    assert result.status == Status.partial and result.issues[0].code == 'non_nested_isochrones'
    assert result.data[1].region.model_dump(mode='json')['geometry']['coordinates'] == raw['features'][1]['geometry']['coordinates']


def test_failure_never_substitutes_circle_and_temporal_preflight():
    p, seen = provider({}, status=429)
    result = run(p.catchments(request(), CTX))
    assert result.status == Status.rate_limited and result.data is None
    assert len(seen) >= 1
    instant = datetime(2026, 11, 4, tzinfo=timezone.utc)
    for req in (request(time=instant), request(time_kind='arrive_by')):
        result = run(p.catchments(req, CTX))
        assert result.status == Status.unsupported and result.data is None
    assert len(seen) >= 1


def test_invalid_polygon_and_bad_response_diagnostics():
    raw = fixture()
    raw['features'][0]['geometry']['coordinates'][0][0][0] = [10, 50]
    p, _ = provider(raw)
    result = run(p.catchments(request(), CTX))
    assert result.status == Status.unknown and result.data is None
    assert result.issues[0].code == 'invalid_isochrone_polygon'
    raw = fixture()
    raw['features'].pop()
    p, _ = provider(raw)
    assert run(p.catchments(request(), CTX)).status == Status.unknown


def test_invalid_input_and_missing_policy_limits_do_not_call():
    p, seen = provider(fixture())
    assert run(p.catchments(request(durations_s=()), CTX)).status == Status.invalid_input
    assert not seen
    p, seen = provider(fixture(), limits=False)
    assert run(p.catchments(request(), CTX)).status == Status.unconfigured
    assert not seen


def test_time_requires_offset_even_when_provider_cannot_execute_it():
    with pytest.raises(ValidationError):
        request(time=datetime(2026, 11, 4))
