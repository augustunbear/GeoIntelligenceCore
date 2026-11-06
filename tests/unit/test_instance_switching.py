"""Same-protocol instance contracts; every response and DNS answer is synthetic."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Confirmation, Location, Point
from geo_intelligence_core.models.requests import RequestContext, SearchRequest, ReverseRequest
from geo_intelligence_core.models.places import PlaceQuery
from geo_intelligence_core.models.spatial import Region, RouteRequest, MatrixRequest, CatchmentRequest
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.trial import TrialSettings, build_trial_provider

FIX = Path(__file__).parents[1] / 'fixtures'
CTX = RequestContext(request_id='synthetic-switch')
A, B = Point(longitude=10.0, latitude=50.0), Point(longitude=10.01, latitude=50.01)
LOC = Location(id='synthetic', version=1, point=A, confirmation=Confirmation(
    method='manual', at=datetime(2026, 11, 5, tzinfo=timezone.utc), evidence_ids=('synthetic',)))
REGION = Region(id='synthetic', version='1', method='synthetic', geometry={'type': 'Polygon',
    'coordinates': [[[10, 50], [10.001, 50], [10.001, 50.001], [10, 50.001], [10, 50]]]})


def make(protocol, kind, *, ident=None, headers=None):
    s = TrialSettings.public(protocol, application_name='Synthetic', contact_url='https://app.example.org/contact')
    if kind != 'public':
        s = s.model_copy(update={'instance_id': ident or f'{protocol}-{kind}',
            'endpoint': f'https://{kind}.example.org/prefix/{protocol}',
            'authentication_required': kind == 'keyed',
            'policy': s.policy.model_copy(update={'allowed_endpoints': (f'https://{kind}.example.org',),
                                                  'max_area_m2': 1e10})})
    else:
        s = s.model_copy(update={'policy': s.policy.model_copy(update={'max_area_m2': 1e10})})
    if headers is None:
        headers = {'Authorization': 'synthetic-instance-key'} if s.authentication_required else {}
    return build_trial_provider(s, budget=InMemoryBudget(5, Decimal(0)), headers=headers), s


def wire(provider, payload, *, addresses=('93.184.215.14',), status=200):
    seen = []
    def reply(request):
        seen.append(request)
        return httpx.Response(status, json=payload, headers={'Retry-After': '0'} if status == 429 else {})
    provider.gateway.transport = httpx.MockTransport(reply)
    provider.gateway.resolver = lambda _: addresses
    return seen


@pytest.mark.parametrize('kind', ['public', 'keyed', 'owned'])
@pytest.mark.parametrize('operation', ['search', 'reverse', 'places', 'route', 'matrix', 'catchments'])
def test_same_protocol_paths_units_and_instance_provenance(kind, operation):
    protocol = 'photon' if operation in ('search', 'reverse') else 'overpass' if operation == 'places' else 'ors'
    p, s = make(protocol, kind)
    if protocol == 'photon':
        payload = {'features': []}
        req = SearchRequest(text='Synthetic') if operation == 'search' else ReverseRequest(point=A)
        invoke = lambda: getattr(p, operation)(req, CTX)
        suffix = '/api' if operation == 'search' else '/reverse'
    elif operation == 'places':
        payload = {'elements': []}
        invoke = lambda: p.search(PlaceQuery(region=REGION, category_ids=('food_service',), mapping_version='osm-v1'), CTX)
        suffix = '/api/interpreter'
    elif operation == 'route':
        payload = json.loads((FIX / 'ors/route_km.json').read_text())
        payload['metadata']['query']['units'] = 'm'
        invoke = lambda: p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX)
        suffix = '/v2/directions/foot-walking/geojson'
    elif operation == 'matrix':
        payload = {'durations': [[600.0]]}
        invoke = lambda: p.matrix(MatrixRequest(origins={'A': A}, destinations={'B': B}, mode='driving'), CTX)
        suffix = '/v2/matrix/driving-car'
    else:
        payload = json.loads((FIX / 'ors/isochrones.json').read_text())
        invoke = lambda: p.catchments(CatchmentRequest(location=LOC, direction='outbound', mode='walking', durations_s=(300, 600, 900)), CTX)
        suffix = '/v2/isochrones/foot-walking'
    seen = wire(p, payload)
    result = asyncio.run(invoke())
    assert result.status in (Status.ok, Status.no_results)
    assert len(seen) == 1
    prefix = '' if kind == 'public' and protocol != 'ors' else '/openrouteservice' if kind == 'public' else f'/prefix/{protocol}'
    assert seen[0].url.path == prefix + suffix
    assert result.context.effective_conditions['provider_instance'] == s.instance_id
    assert result.context.effective_conditions['provider_endpoint'] == s.endpoint
    if operation == 'route':
        assert result.data.distance_m == 1.25 and result.data.duration_s == 600
    if operation == 'matrix':
        assert result.data.cells[0].duration_s == 600


def test_credentials_isolated_between_instances_and_no_paid_fallback():
    a, _ = make('ors', 'keyed', headers={'Authorization': 'synthetic-key-A'})
    b, _ = make('ors', 'owned')
    sa, sb = wire(a, {}, status=429), wire(b, {'durations': [[2.0]]})
    req = MatrixRequest(origins={'A': A}, destinations={'B': B}, mode='walking')
    assert asyncio.run(a.matrix(req, CTX)).status == Status.rate_limited
    assert asyncio.run(b.matrix(req, CTX)).status == Status.ok
    assert len(sa) == 5 and len(sb) == 1
    assert all(r.headers.get('authorization') == 'synthetic-key-A' for r in sa)
    assert 'authorization' not in sb[0].headers


@pytest.mark.parametrize('address', ['10.0.0.1', '127.0.0.1', '169.254.1.1'])
def test_self_hosted_private_dns_still_rejected(address):
    p, _ = make('ors', 'owned')
    seen = wire(p, {}, addresses=(address,))
    result = asyncio.run(p.route(RouteRequest(origin=A, destination=B, mode='walking'), CTX))
    assert result.status == Status.unconfigured and not seen


def test_instance_cache_identity_and_historical_context():
    from geo_intelligence_core.providers.cache import CacheKey
    a, sa = make('photon', 'keyed')
    b, sb = make('photon', 'owned')
    wire(a, {'features': []}); wire(b, {'features': []})
    ra = asyncio.run(a.search(SearchRequest(text='Synthetic'), CTX))
    frozen = ra.context.model_dump_json()
    asyncio.run(b.search(SearchRequest(text='Synthetic'), CTX))
    assert ra.context.model_dump_json() == frozen
    def key(ident):
        return CacheKey(provider_id=ident, source_id='osm', source_version='synthetic', language='de',
                        method='GET', path='/api', params={'q': 'Synthetic'}, purpose='analysis', private=False)
    assert key(sa.instance_id) != key(sb.instance_id)
    from geo_intelligence_core.providers.cache import Cache
    from geo_intelligence_core.models.evidence import Rights, Permission
    rights = Rights(use=Permission.allowed, retain=Permission.allowed, cache=Permission.allowed,
                    permitted_purpose='analysis')
    cache = Cache(enabled=True)
    assert cache.put(key(sa.instance_id), {'synthetic': 1}, rights)
    assert cache.get(key(sb.instance_id), rights) is None
    assert cache.get(key(sa.instance_id), rights) == {'synthetic': 1}


def test_unconfigured_instance_does_not_inherit_previous_endpoint():
    old = CTX.model_copy(update={'effective_conditions': {'provider_instance':'A','provider_endpoint':'https://old.example.org'}})
    p,_=make('ors','keyed',headers={})
    result=asyncio.run(p.route(RouteRequest(origin=A,destination=B,mode='walking'),old))
    assert result.context.effective_conditions['provider_instance']=='ors-keyed'
    assert 'provider_endpoint' not in result.context.effective_conditions
    assert old.effective_conditions['provider_endpoint']=='https://old.example.org'


def test_terminal_dot_host_cannot_bypass_hosted_authentication():
    s=TrialSettings.public('ors',application_name='Synthetic',contact_url='https://app.example.org/contact')
    with pytest.raises(ValueError):
        s.model_copy(update={'endpoint':'https://api.heigit.org./openrouteservice',
            'authentication_required':False,'policy':s.policy.model_copy(update={'allowed_endpoints':('https://api.heigit.org.',)})})


@pytest.mark.parametrize('query,options', [
    (SearchRequest(text='x'), {}),
    (SearchRequest(text='Synthetic', country_codes=['DE','FR']), {}),
    (SearchRequest(text='Synthetic', bbox=[1,2,0,3]), {}),
    (SearchRequest(text='Synthetic', bbox=[0,0,1,1]), {'supports_bbox':False}),
])
def test_photon_local_rejection_has_current_instance(query,options):
    from geo_intelligence_core.providers.photon import PhotonCapabilities
    provider,settings=make('photon','owned')
    provider.capabilities=PhotonCapabilities(**options)
    old=CTX.model_copy(update={'effective_conditions':{'provider_instance':'previous','provider_endpoint':'https://previous.example'}})
    result=asyncio.run(provider.search(query,old))
    assert result.status in (Status.invalid_input,Status.unsupported)
    assert result.context.effective_conditions['provider_instance']==settings.instance_id
    assert result.context.effective_conditions['provider_endpoint']==settings.endpoint
    assert old.effective_conditions['provider_instance']=='previous'


@pytest.mark.parametrize('operation,payload', [
    ('search', {'text':''}),
    ('reverse', {'point':{'longitude':181,'latitude':50}}),
])
def test_photon_invalid_request_has_current_instance(operation,payload):
    provider,settings=make('photon','owned')
    old=CTX.model_copy(update={'effective_conditions':{'provider_instance':'previous','provider_endpoint':'https://previous.example'}})
    result=asyncio.run(getattr(provider,operation)(payload,old))
    assert result.status==Status.invalid_input
    assert result.context.effective_conditions['provider_instance']==settings.instance_id
    assert result.context.effective_conditions['provider_endpoint']==settings.endpoint
    assert old.effective_conditions['provider_instance']=='previous'
