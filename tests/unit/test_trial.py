"""Factory contracts use synthetic HTTP only; no public provider is activated."""
import asyncio
import json
from pathlib import Path
import runpy
import socket

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.requests import RequestContext, SearchRequest
from geo_intelligence_core.models.spatial import RouteRequest
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.trial import TrialSettings, build_trial_provider


CTX = RequestContext(request_id='synthetic-trial')
ROUTE = RouteRequest(origin=Point(longitude=10.0, latitude=50.0),
                     destination=Point(longitude=10.01, latitude=50.01), mode='walking')


def settings(protocol):
    return TrialSettings.public(protocol, application_name='SyntheticApp',
                                contact_url='https://app.example.org/contact')


def wire(provider, payload=None, status=200):
    seen = []
    def reply(request):
        seen.append(request)
        return httpx.Response(status, json=payload or {'features': []},
                              headers={'Retry-After': '0'} if status == 429 else {})
    provider.gateway.transport = httpx.MockTransport(reply)
    provider.gateway.resolver = lambda _: ['93.184.215.14']
    return seen


def test_trial_defaults_and_opt_in(monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail('construction/dry-run must not access network')
    monkeypatch.setattr(socket, 'getaddrinfo', no_network)
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    providers = [build_trial_provider(settings(p), budget=InMemoryBudget(50, 0))
                 for p in ('photon', 'overpass', 'ors')]
    assert len({p.provider_id for p in providers}) == 3
    for p in providers:
        assert p.gateway.policy.max_calls_per_run == 5
        assert p.gateway.policy.max_concurrency == 1
        assert p.gateway.policy.cost_ceiling == 0
        assert p.gateway.cost_per_call == 0
    for protocol in ('photon', 'overpass', 'ors'):
        s = settings(protocol)
        assert s.daily_budget_requirement == 'caller_shared_budget_required'
        assert s.policy.period_limits == {}  # not a persistent daily quota
        assert s.policy.cache_policy == 'disabled'
        assert s.terms_ref and s.rights_ref and s.attribution
        assert 'SyntheticApp' in s.user_agent and 'https://app.example.org/contact' in s.user_agent
    with pytest.raises(ValueError):
        TrialSettings()


@pytest.mark.parametrize('protocol,path', [
    ('photon', '/api'), ('overpass', '/api/interpreter'),
    ('ors', '/openrouteservice/v2/directions/foot-walking/geojson'),
])
def test_public_presets_wire_existing_adapters(protocol, path):
    from geo_intelligence_core.models.spatial import Region
    from geo_intelligence_core.models.places import PlaceQuery
    headers = {'Authorization': 'synthetic-ors-key'} if protocol == 'ors' else None
    provider = build_trial_provider(settings(protocol), budget=InMemoryBudget(50, 0), headers=headers)
    payload = json.loads((Path(__file__).parents[1] / 'fixtures/ors/route_km.json').read_text())
    payload['metadata']['query']['units'] = 'm'
    seen = wire(provider, payload if protocol == 'ors' else
                {'elements': []} if protocol == 'overpass' else {'features': []})
    if protocol == 'photon':
        result = asyncio.run(provider.search(SearchRequest(text='Synthetic'), CTX))
    elif protocol == 'ors':
        result = asyncio.run(provider.route(ROUTE, CTX))
    else:
        region = Region(id='synthetic', version='1', method='synthetic',
                        geometry={'type': 'Polygon', 'coordinates': [[[10.0, 50.0],
                            [10.001, 50.0], [10.001, 50.001], [10.0, 50.001], [10.0, 50.0]]]})
        result = asyncio.run(provider.search(PlaceQuery(region=region,
                              category_ids=('food_service',), mapping_version='osm-v1',
                              boundary_rule='point_covers'), CTX))
    assert result.status in (Status.ok, Status.no_results)
    assert len(seen) == 1 and seen[0].url.path == path
    assert seen[0].headers['host'] == {'photon': 'photon.komoot.io',
           'overpass': 'overpass.private.coffee', 'ors': 'api.heigit.org'}[protocol]
    assert seen[0].headers.get('authorization') == (headers or {}).get('Authorization')


def test_auth_and_zero_cost():
    for protocol in ('photon', 'overpass'):
        assert build_trial_provider(settings(protocol), budget=InMemoryBudget(50, 0))
    for headers in (None, {}, {'User-Agent': 'Synthetic'}, {'Authorization': '  '}):
        provider = build_trial_provider(settings('ors'), budget=InMemoryBudget(50, 0), headers=headers)
        seen = wire(provider)
        result = asyncio.run(provider.route(ROUTE, CTX))
        assert result.status == Status.unconfigured and result.data is None
        assert not seen
    s = settings('ors')
    with pytest.raises(ValueError):
        s.model_copy(update={'authentication_required': False})
    with pytest.raises(ValueError):
        settings('photon').model_copy(update={'cost_per_call': '0.01'})
    custom = s.model_copy(update={'endpoint': 'https://owned.example.org/ors',
        'instance_id': 'synthetic-ors', 'authentication_required': False,
        'policy': s.policy.model_copy(update={'allowed_endpoints': ('https://owned.example.org',)})})
    assert build_trial_provider(custom, budget=InMemoryBudget(50, 0)).provider_id == 'synthetic-ors'


def test_runtime_credentials_are_not_settings_or_errors():
    secret = 'synthetic-only-value'
    s = settings('ors')
    headers = {'Authorization': secret}
    p = build_trial_provider(s, budget=InMemoryBudget(50, 0), headers=headers)
    headers['Authorization'] = 'changed-after-construction'
    seen = wire(p, status=403)
    result = asyncio.run(p.route(ROUTE, CTX))
    assert seen[0].headers['authorization'] == secret
    assert secret not in s.model_dump_json() + repr(s) + result.model_dump_json()
    for update in ({'headers': {'Authorization': secret}},
                   {'endpoint': 'https://user:' + secret + '@api.heigit.org'},
                   {'protocol': secret}, {secret: 'extra-field'},
                   {'policy': {'unexpected': secret}}):
        for construct in (lambda: s.model_copy(update=update),
                          lambda: TrialSettings(**{**s.model_dump(), **update}),
                          lambda: TrialSettings.model_validate({**s.model_dump(), **update})):
            with pytest.raises(ValueError) as exc:
                construct()
            assert secret not in str(exc.value)
            assert secret not in exc.value.json()
            assert secret not in repr(exc.value.errors())


@pytest.mark.parametrize('retry', [False, True])
def test_factory_enforces_run_limit_even_with_larger_shared_budget(retry):
    shared = InMemoryBudget(50, 0)
    provider = build_trial_provider(settings('photon'), budget=shared)
    seen = wire(provider, status=429 if retry else 200)
    async def run():
        results = []
        for _ in range(6):
            results.append(await provider.search(SearchRequest(text='Synthetic'), CTX))
        return results
    result = asyncio.run(run())[-1]
    assert result.status == Status.rate_limited and result.data is None
    assert len(seen) == shared.calls == 5


def test_shared_budget_is_not_replaced():
    shared = InMemoryBudget(1, 0)
    a = build_trial_provider(settings('photon'), budget=shared)
    b = build_trial_provider(settings('photon'), budget=shared)
    seen_a, seen_b = wire(a), wire(b)
    assert asyncio.run(a.search(SearchRequest(text='Synthetic'), CTX)).status == Status.no_results
    assert asyncio.run(b.search(SearchRequest(text='Synthetic'), CTX)).status == Status.rate_limited
    assert len(seen_a) == 1 and not seen_b


def test_runtime_header_validation_hides_values():
    for headers in ({'Authorization': 'synthetic-\u4e2d-key'},
                    {'Bad Header': 'synthetic-key'},
                    {'Authorization': 'synthetic-key\nsecond-line'}):
        with pytest.raises(ValueError) as exc:
            build_trial_provider(settings('ors'), budget=InMemoryBudget(5, 0), headers=headers)
        assert 'synthetic-' not in str(exc.value)


def test_required_auth_for_custom_photon_and_prefix():
    s = settings('photon')
    s = s.model_copy(update={'instance_id': 'synthetic-custom-photon',
        'endpoint': 'https://owned.example.org/geo/photon', 'authentication_required': True,
        'policy': s.policy.model_copy(update={'allowed_endpoints': ('https://owned.example.org',)})})
    p = build_trial_provider(s, budget=InMemoryBudget(5, 0))
    seen = wire(p)
    assert asyncio.run(p.search(SearchRequest(text='Synthetic'), CTX)).status == Status.unconfigured
    assert not seen
    p = build_trial_provider(s, budget=InMemoryBudget(5, 0), headers={'authorization': 'synthetic-custom-key'})
    seen = wire(p)
    assert asyncio.run(p.search(SearchRequest(text='Synthetic'), CTX)).status == Status.no_results
    assert seen[0].url.path == '/geo/photon/api'
    assert seen[0].headers['authorization'] == 'synthetic-custom-key'


def test_concurrent_calls_share_run_cap_and_single_gateway_slot():
    shared = InMemoryBudget(50, 0)
    p = build_trial_provider(settings('photon'), budget=shared)
    active = peak = attempted = 0
    async def reply(request):
        nonlocal active, peak, attempted
        active += 1
        peak = max(peak, active)
        attempted += 1
        await asyncio.sleep(0.001)
        active -= 1
        return httpx.Response(200, json={'features': []})
    p.gateway.transport = httpx.MockTransport(reply)
    p.gateway.resolver = lambda _: ['93.184.215.14']
    async def run():
        return await asyncio.gather(*(p.search(SearchRequest(text='Synthetic'), CTX) for _ in range(8)))
    results = asyncio.run(run())
    assert sum(r.status == Status.no_results for r in results) == 5
    assert sum(r.status == Status.rate_limited for r in results) == 3
    assert peak == 1 and attempted == shared.calls == 5


@pytest.mark.parametrize('change', [
    {'cost_ceiling': '1'}, {'max_calls_per_run': 0}, {'max_concurrency': 2},
    {'deadline_s': None}, {'max_response_bytes': None}, {'currency': None},
    {'pricing_ref': None}, {'cache_policy': None}, {'period_limits': {'day': 50}},
    {'allowed_endpoints': ('https://other.example.org',)},
])
def test_incomplete_or_nonzero_trial_policy_is_rejected(change):
    s = settings('photon')
    with pytest.raises(ValueError):
        s.model_copy(update={'policy': s.policy.model_copy(update=change)})


@pytest.mark.parametrize('change', [
    {'endpoint': 'http://geo.example.org'},
    {'endpoint': 'https://photon.komoot.io?key=synthetic'},
    {'endpoint': 'https://photon.komoot.io/api/../other'},
    {'instance_id': ''}, {'authentication_header': 'User-Agent'},
])
def test_invalid_trial_configuration(change):
    with pytest.raises(ValueError):
        settings('photon').model_copy(update=change)


def test_dry_run_example_is_offline(monkeypatch, capsys):
    def blocked(*args, **kwargs):
        pytest.fail('dry-run reached networking')
    monkeypatch.setattr(socket, 'getaddrinfo', blocked)
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.delenv('ORS_API_KEY', raising=False)
    monkeypatch.setattr('sys.argv', ['free_trial.py'])
    runpy.run_path(str(Path(__file__).parents[2] / 'examples/python/free_trial.py'), run_name='__main__')
    out = capsys.readouterr().out
    assert 'dry-run' in out and 'photon' in out and 'overpass' in out
    assert 'ors: unconfigured' in out and 'caller_shared_budget_required' in out
