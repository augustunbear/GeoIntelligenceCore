import asyncio
from decimal import Decimal
import json
from pathlib import Path

import httpx

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
