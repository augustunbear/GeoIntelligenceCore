import asyncio
from decimal import Decimal
import json
from pathlib import Path

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext, ReverseRequest, SearchRequest
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.http import HttpGateway
from geo_intelligence_core.providers.photon import PhotonCapabilities, PhotonResolver


def feature(osm_id, name, lon=11.58, lat=48.14, **properties):
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {'osm_type': 'N', 'osm_id': osm_id, 'name': name,
                           'countrycode': 'DE', **properties}}


def setup(reply, *, capabilities=None, max_candidates=20):
    seen = []
    async def handler(request):
        seen.append(request)
        if callable(reply):
            value = reply(request)
            return await value if asyncio.iscoroutine(value) else value
        return reply
    policy = UsagePolicy(allowed_endpoints=('https://geo.example.org',), max_calls_per_run=3,
                         max_concurrency=1, deadline_s=0.1, max_response_bytes=10000,
                         cost_ceiling=Decimal('0'), currency='EUR', pricing_ref='synthetic')
    gateway = HttpGateway({'photon': ProviderConfig(id='photon', endpoint='https://geo.example.org')},
                          policy, InMemoryBudget(3, Decimal('0')),
                          transport=httpx.MockTransport(handler), resolver=lambda _: ['93.184.215.14'],
                          cost_per_call=Decimal('0'))
    return PhotonResolver(gateway, capabilities=capabilities or PhotonCapabilities(),
                          max_candidates=max_candidates), seen


CTX = RequestContext(request_id='synthetic')


def run(coro):
    return asyncio.run(coro)


def test_candidates_distinct_and_no_entrance_claim():
    sample = json.loads((Path(__file__).parents[1] / 'fixtures/photon/ambiguous_neustadt.json').read_text())
    resolver, _ = setup(httpx.Response(200, json=sample))
    result = run(resolver.search(SearchRequest(text='Neustadt'), CTX))
    assert result.status == Status.ok and len(result.data) == 2
    assert result.data[0].id != result.data[1].id
    assert result.data[1].precision == 'locality'
    assert all(not hasattr(c, 'confirmation') and c.precision != 'entrance' for c in result.data)

    street_only, _ = setup(httpx.Response(200, json={'features': [
        feature(5, 'Hauptstraße', street='Hauptstraße')]}))
    assert run(street_only.search(SearchRequest(text='Hauptstraße'), CTX)).data[0].precision == 'street'


def test_language_fallback_and_original_name():
    resolver, seen = setup(httpx.Response(200, json={'features': [
        feature(3, 'München', city='München', extra={'name': 'München'})]}))
    result = run(resolver.search(SearchRequest(text='München', language='zh-CN'), CTX))
    assert seen[0].url.params['lang'] == 'de'
    assert result.context.effective_conditions['language'] == 'de'
    assert result.issues[0].code == 'language_fallback'
    assert result.data[0].address.native_names['und'] == 'München'


def test_empty_vs_timeout_and_reverse_mapping():
    empty, seen = setup(httpx.Response(200, json={'features': []}))
    assert run(empty.search(SearchRequest(text='Berlin'), CTX)).status == Status.no_results
    result = run(empty.reverse(ReverseRequest(point=Point(longitude=13.4, latitude=52.5)), CTX))
    assert result.status == Status.no_results
    assert seen[1].url.path == '/reverse' and seen[1].url.params['lon'] == '13.4'
    async def slow(_):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json={'features': []})
    timed, _ = setup(slow)
    result = run(timed.search(SearchRequest(text='Berlin'), CTX))
    assert result.status == Status.unavailable and result.data is None


def test_hard_filters_and_query_mapping():
    resolver, seen = setup(httpx.Response(200, json={'features': [
        feature(1, 'Inside'), feature(2, 'Wrong country', countrycode='AT'),
        feature(3, 'Outside', lon=13.0)]}))
    request = SearchRequest(text='München', country_codes=('DE',), bbox=(11.0, 48.0, 12.0, 49.0),
                            near=Point(longitude=11.5, latitude=48.1), limit=3)
    result = run(resolver.search(request, CTX))
    params = seen[0].url.params
    assert params['q'] == 'München' and params['lang'] == 'de' and params['limit'] == '3'
    assert params['countrycode'] == 'DE' and params['bbox'] == '11.0,48.0,12.0,49.0'
    assert params['lon'] == '11.5' and params['lat'] == '48.1'
    assert len(result.data) == 1 and result.data[0].source_ref == 'photon:osm:N:1'
    unsupported, calls = setup(httpx.Response(200, json={'features': []}),
                               capabilities=PhotonCapabilities(supports_bbox=False))
    assert run(unsupported.search(request, CTX)).status == Status.unsupported
    assert not calls


def test_invalid_bounded_and_unconfigured():
    with pytest.raises(ValueError, match='version'):
        PhotonCapabilities(api_version='legacy')
    resolver, seen = setup(httpx.Response(200, json={'features': []}), max_candidates=2)
    assert run(resolver.search(SearchRequest(text='a', limit=3), CTX)).status == Status.invalid_input
    assert run(resolver.search(SearchRequest(text='Berlin', country_codes=('DE', 'AT'), limit=2), CTX)).status == Status.unsupported
    assert run(resolver.search(SearchRequest(text='  ', limit=2), CTX)).status == Status.invalid_input
    assert not seen
    resolver.gateway.providers.clear()
    assert run(resolver.search(SearchRequest(text='Berlin', limit=2), CTX)).status == Status.unconfigured


def test_malformed_response_and_cancel_stale():
    malformed, _ = setup(httpx.Response(200, json={'features': [feature(1, 'X', lon=999)]}))
    result = run(malformed.search(SearchRequest(text='Berlin'), CTX))
    assert result.status == Status.unavailable and result.data is None
    calls = []
    async def retry(_):
        calls.append(1)
        await asyncio.sleep(1)
        return httpx.Response(503, headers={'Retry-After': '0'})
    resolver, _ = setup(retry)
    async def cancel():
        task = asyncio.create_task(resolver.search(SearchRequest(text='Ber'), CTX))
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    run(cancel())
    assert len(calls) == 1


@pytest.mark.parametrize('operation', ['search', 'reverse'])
@pytest.mark.parametrize('conflicting', [False, True])
def test_duplicate_osm_identity_fails_closed_without_discarding_source_evidence(operation, conflicting):
    first = feature(25299100, 'Synthetic town hall', street='Example Street', housenumber='4')
    first['properties']['osm_type'] = 'W'
    second = json.loads(json.dumps(first))
    if conflicting:
        second['geometry']['coordinates'] = [11.59, 48.15]
        second['properties']['name'] = 'Different indexed name'
    resolver, _ = setup(httpx.Response(200, json={'features': [first, second]}))
    request = (SearchRequest(text='Synthetic town hall') if operation == 'search'
               else ReverseRequest(point=Point(longitude=11.58, latitude=48.14)))
    result = run(getattr(resolver, operation)(request, CTX))
    assert result.status == Status.unavailable
    assert result.data is None
    assert [issue.code for issue in result.issues] == ['invalid_response']


def test_distinct_osm_types_with_same_numeric_id_remain_distinct_candidates():
    node = feature(17, 'Synthetic node')
    way = feature(17, 'Synthetic way')
    way['properties']['osm_type'] = 'W'
    resolver, _ = setup(httpx.Response(200, json={'features': [node, way]}))
    result = run(resolver.search(SearchRequest(text='Synthetic'), CTX))
    assert result.status == Status.ok
    assert [candidate.id for candidate in result.data] == [
        'photon:osm:N:17', 'photon:osm:W:17']


def test_address_strata_keep_distinct_towns_and_missing_house_number_unverified():
    towns = [feature(101, 'Neustadt', lon=10.1, lat=50.1, city='Neustadt'),
             feature(102, 'Neustadt', lon=11.1, lat=51.1, city='Neustadt')]
    street = feature(103, 'Synthetic Road', lon=10.2, lat=50.2,
                     city='Neustadt', street='Synthetic Road')
    resolver, seen = setup(httpx.Response(200, json={'features': [*towns, street]}))
    result = run(resolver.search(SearchRequest(
        text='Neustadt', near=Point(longitude=10.1, latitude=50.1)), CTX))
    assert result.status == Status.ok
    assert [candidate.id for candidate in result.data] == [
        'photon:osm:N:101', 'photon:osm:N:102', 'photon:osm:N:103']
    assert [candidate.precision for candidate in result.data] == [
        'locality', 'locality', 'street']
    assert result.data[2].address.house_number is None
    assert seen[0].url.params['lon'] == '10.1'  # A bias, not a hard match.


@pytest.mark.parametrize('osm_key,layer,expected', [
    ('highway', 'street', 'street'),
    ('highway', 'house', 'locality'),
    ('place', 'street', 'locality'),
])
def test_named_highway_street_without_house_number_uses_road_name(osm_key, layer, expected):
    road = feature(30825768, 'Brandenburger Straße', city='Potsdam',
                   osm_key=osm_key, type=layer)
    road['properties']['osm_type'] = 'W'
    resolver, _ = setup(httpx.Response(200, json={'features': [road]}))
    result = run(resolver.search(SearchRequest(text='Brandenburger Straße, Potsdam'), CTX))
    assert result.status == Status.ok
    assert result.data[0].precision == expected
    assert result.data[0].address.street == ('Brandenburger Straße' if expected == 'street' else None)
    assert result.data[0].address.house_number is None


def test_duplicate_identity_outside_requested_bbox_still_invalidates_response():
    first = feature(101, 'Outside', lon=13, lat=52)
    resolver, _ = setup(httpx.Response(200, json={'features': [first, first]}))
    result = run(resolver.search(SearchRequest(
        text='Synthetic', bbox=(10, 48, 12, 50)), CTX))
    assert result.status == Status.unavailable
    assert result.data is None


@pytest.mark.parametrize('endpoint,headers,expected_path', [
    ('https://public.example.org', {}, '/api'),
    ('https://paid.example.org/geocoding', {'Authorization': 'synthetic-key'}, '/geocoding/api'),
    ('https://owned.example.org/photon', {}, '/photon/api'),
])
def test_instance_switch_preserves_adapter_contract(endpoint, headers, expected_path):
    from urllib.parse import urlsplit
    origin = 'https://' + urlsplit(endpoint).netloc
    seen = []
    def reply(request):
        seen.append(request)
        return httpx.Response(200, json={'features': [feature(7, 'Synthetic')]})
    limits = UsagePolicy(allowed_endpoints=(origin,), max_calls_per_run=2,
                         max_concurrency=1, deadline_s=1, max_response_bytes=10000,
                         cost_ceiling=Decimal('0'), currency='EUR', pricing_ref='synthetic')
    gateway = HttpGateway({'instance': ProviderConfig(id='instance', endpoint=endpoint)},
                          limits, InMemoryBudget(2, Decimal('0')), headers=headers,
                          transport=httpx.MockTransport(reply),
                          resolver=lambda _: ['93.184.215.14'], cost_per_call=Decimal('0'))
    adapter = PhotonResolver(gateway, provider_id='instance', capabilities=PhotonCapabilities())
    result = run(adapter.search(SearchRequest(text='Synthetic'), CTX))
    assert result.status == Status.ok and result.data[0].id == 'photon:osm:N:7'
    assert seen[0].url.path == expected_path
    assert seen[0].headers['host'] == urlsplit(endpoint).netloc
    assert seen[0].headers.get('authorization') == headers.get('Authorization')
    reversed_result = run(adapter.reverse(ReverseRequest(point=Point(longitude=11.58, latitude=48.14)), CTX))
    assert reversed_result.status == Status.ok and reversed_result.data[0].id == result.data[0].id
    assert seen[1].url.path == expected_path.removesuffix('/api') + '/reverse'
    assert seen[1].headers.get('authorization') == headers.get('Authorization')
