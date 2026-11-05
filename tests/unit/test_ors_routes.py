import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import httpx
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.spatial import MatrixRequest, RouteRequest
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.http import HttpGateway
from geo_intelligence_core.providers.ors import OrsRoutingProvider

FIX = Path(__file__).parents[1] / 'fixtures' / 'ors'
A = Point(longitude=10.0, latitude=50.0)
B = Point(longitude=10.01, latitude=50.01)
CTX = RequestContext(request_id='synthetic')


def run(coro):
    return asyncio.run(coro)


def provider(response, *, unit='m', endpoint='https://api.heigit.org/openrouteservice', status=200):
    seen = []
    def reply(req):
        seen.append(req)
        return httpx.Response(status, json=response)
    policy = UsagePolicy(allowed_endpoints=('https://api.heigit.org',),
        allowed_capabilities=('route', 'travelmatrix'), max_calls_per_run=2,
        max_response_bytes=10000, deadline_s=3.0, cost_ceiling=Decimal('0'),
        currency='EUR', pricing_ref='synthetic')
    config = ProviderConfig(id='ors', endpoint=endpoint,
        capability_flags={'route': True, 'travelmatrix': True}, credential_handle='configured-by-caller')
    gateway = HttpGateway({'ors': config}, policy, InMemoryBudget(2, Decimal('0')),
        resolver=lambda _: ['93.184.215.14'], transport=httpx.MockTransport(reply),
        cost_per_call=Decimal('0'), headers={'Authorization': 'synthetic-secret'})
    return OrsRoutingProvider(gateway, distance_unit=unit), seen


def test_route_explicit_km_to_m_and_seconds():
    p, seen = provider(json.loads((FIX / 'route_km.json').read_text()), unit='km')
    result = run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX))
    assert result.status == Status.ok
    assert result.data.distance_m == 1250.0 and result.data.duration_s == 600.0
    assert result.data.origin == A and result.data.destination == B
    assert len(seen) == 1 and seen[0].method == 'POST'
    assert seen[0].url.path == '/openrouteservice/v2/directions/foot-walking/geojson'
    assert json.loads(seen[0].content)['coordinates'] == [[10, 50], [10.01, 50.01]]
    assert json.loads(seen[0].content)['units'] == 'km'
    assert seen[0].headers['authorization'] == 'synthetic-secret'


def test_missing_or_mismatched_unit_is_unknown():
    raw = json.loads((FIX / 'route_km.json').read_text())
    raw['metadata']['query'].pop('units')
    p, _ = provider(raw, unit='km')
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX)).status == Status.unknown


def test_reversed_or_unrelated_route_geometry_is_rejected():
    raw = json.loads((FIX / 'route_km.json').read_text())
    raw['features'][0]['geometry']['coordinates'].reverse()
    p, _ = provider(raw, unit='km')
    reversed_route = run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX))
    assert reversed_route.status == Status.unknown and reversed_route.data is None
    assert reversed_route.issues[0].code == 'invalid_route_response'

    raw['features'][0]['geometry']['coordinates'] = [[11, 51], [11.01, 51.01]]
    p, _ = provider(raw, unit='km')
    unrelated_route = run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX))
    assert unrelated_route.status == Status.unknown and unrelated_route.data is None


def test_directed_matrix_order_and_null():
    p, seen = provider(json.loads((FIX / 'matrix_directed.json').read_text()))
    result = run(p.matrix(MatrixRequest(origins={'A': A, 'B': B},
        destinations={'A': A, 'B': B}, mode='driving'), CTX))
    assert result.status == Status.partial
    cells = {(c.origin_id, c.destination_id): c for c in result.data.cells}
    assert cells['A', 'B'].duration_s == 600 and cells['B', 'A'].duration_s == 900
    assert cells['B', 'B'].duration_s is None and cells['B', 'B'].status == Status.unavailable
    body = json.loads(seen[0].content)
    assert body['sources'] == [0, 1] and body['destinations'] == [2, 3]
    assert seen[0].url.path == '/openrouteservice/v2/matrix/driving-car'


def test_no_route_and_temporal_unsupported_without_network():
    p, seen = provider({'features': [], 'metadata': {'query': {'units': 'm'}}})
    result = run(p.route(RouteRequest(origin=A, destination=B, mode='cycling'), CTX))
    assert result.status == Status.unavailable and result.data is None
    assert result.issues[0].code == 'no_route'
    t = datetime(2026, 11, 4, tzinfo=timezone.utc)
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='cycling', time=t), CTX)).status == Status.unsupported
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='cycling', time_kind='arrive_by'), CTX)).status == Status.unsupported
    assert run(p.matrix(MatrixRequest(origins={'A': A}, destinations={'B': B}, mode='driving', time=t), CTX)).status == Status.unsupported
    assert len(seen) == 1


def test_old_endpoint_no_fallback_and_rate_limit():
    p, seen = provider({}, endpoint='https://api.openrouteservice.org')
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX)).status == Status.unconfigured
    assert not seen
    p, _ = provider({}, status=429)
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX)).status == Status.rate_limited


def test_gateway_post_rejects_nested_scope_and_redirect():
    p, seen = provider({'ok': True})
    assert run(p.gateway.request('ors', 'POST', '/v2/test', {'x': {'scope_token': 'secret'}}, CTX)).status == Status.invalid_input
    assert not seen
    p, _ = provider({}, status=302)
    assert run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX)).status == Status.unavailable
