import asyncio
from decimal import Decimal
import logging

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.evidence import Permission, Rights
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.cache import Cache, CacheKey
from geo_intelligence_core.providers.http import HttpGateway


class FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, replies):
        self.replies = replies
        self.calls = 0

    async def handle_async_request(self, request):
        self.calls += 1
        value = self.replies[min(self.calls - 1, len(self.replies) - 1)]
        if callable(value):
            return value(request)
        return value


def policy(calls=2, deadline=3, size=128):
    return UsagePolicy(allowed_endpoints=('https://api.example.com',), max_calls_per_run=calls,
                       max_concurrency=2, deadline_s=float(deadline), max_response_bytes=size,
                       cost_ceiling=Decimal('0'), currency='EUR', pricing_ref='documented-free-test')


def gateway(transport, budget=None, *, limits=None, clock=None, redirect_hosts=()):
    limits = limits or policy()
    return HttpGateway({'p': ProviderConfig(id='p', endpoint='https://api.example.com')}, limits,
                       budget or InMemoryBudget(limits.max_calls_per_run, limits.cost_ceiling),
                       transport=transport, resolver=lambda host: ['93.184.215.14'],
                       clock=clock or __import__('time').monotonic,
                       allowed_redirect_hosts=redirect_hosts, cost_per_call=Decimal('0'))


def context(scope=None):
    return RequestContext(request_id='synthetic', scope_token=scope)


def run(coro):
    return asyncio.run(coro)


def test_retry_budget():
    transport = FakeTransport([httpx.Response(429, headers={'Retry-After': '0'}), httpx.Response(429)])
    result = run(gateway(transport).request('p', 'GET', '/v1/query', {}, context()))
    assert transport.calls == 2
    assert result.status == Status.rate_limited and result.data is None

    clock = lambda: 100.0
    delayed = FakeTransport([httpx.Response(429, headers={'Retry-After': '10'})])
    result = run(gateway(delayed, limits=policy(deadline=1), clock=clock).request('p', 'GET', '/v1/query', {}, context()))
    assert delayed.calls == 1 and result.status == Status.rate_limited


def test_read_timeout_can_use_remaining_provider_deadline(monkeypatch):
    original = httpx.AsyncClient
    captured = []

    def client(**kwargs):
        captured.append(kwargs['timeout'])
        return original(**kwargs)

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    result = run(gateway(FakeTransport([httpx.Response(200, json={'ok': True})]),
                         limits=policy(deadline=40)).request('p', 'GET', '/v1/query', {}, context()))
    assert result.status == Status.ok
    assert captured[0].read == 40
    assert captured[0].connect == 5


def test_concurrent_reservation():
    transport = FakeTransport([httpx.Response(200, json={'ok': True})])
    async def two():
        g = gateway(transport, limits=policy(calls=1))
        return await asyncio.gather(*(g.request('p', 'GET', '/v1/query', {}, context()) for _ in range(2)))
    results = run(two())
    assert transport.calls == 1
    assert sorted(r.status for r in results) == [Status.ok, Status.rate_limited]


def test_ssrf_redirect():
    for url in ('http://api.example.com/private', 'https://127.0.0.1/x',
                'https://192.168.1.1/x', 'https://elsewhere.example/x'):
        transport = FakeTransport([httpx.Response(302, headers={'Location': url})])
        result = run(gateway(transport, redirect_hosts=('api.example.com',)).request('p', 'GET', '/v1/query', {}, context()))
        assert result.status == Status.unavailable and transport.calls == 1


def test_private_cache():
    rights = Rights(use=Permission.allowed, retain=Permission.allowed, cache=Permission.allowed,
                    permitted_purpose='analysis')
    cache = Cache(enabled=True)
    def key(scope):
        return CacheKey(provider_id='p', source_id='s', source_version='v1', language='de',
                        method='GET', path='/x', params={'q': 'a'}, purpose='analysis',
                        private=True, scope_token=scope)
    assert not cache.put(key(None), {'value': 1}, rights)
    assert cache.put(key('A'), {'value': 1}, rights)
    assert cache.get(key('B'), rights) is None
    assert cache.get(key('A'), rights) == {'value': 1}
    assert not cache.put(key('B'), {'value': 2}, Rights())
    assert not cache.put(key('B'), {'value': 2}, Rights(use=Permission.allowed, retain=Permission.allowed,
                                                         cache=Permission.denied, permitted_purpose='analysis'))
    transport = FakeTransport([httpx.Response(200, json={'ok': 1})])
    run(gateway(transport).request('p', 'GET', '/v1/query', {'x': 'a'}, context('opaque-secret')))
    assert 'opaque-secret' not in str(transport.replies)


def test_response_limit():
    transport = FakeTransport([httpx.Response(200, content=b'x' * 1024)])
    result = run(gateway(transport, limits=policy(size=16)).request('p', 'GET', '/v1/query', {}, context()))
    assert result.status == Status.unavailable and result.data is None


def test_no_secret_logs(caplog):
    transport = FakeTransport([httpx.Response(200, json={'ok': 1})])
    with caplog.at_level(logging.DEBUG):
        result = run(gateway(transport).request('p', 'GET', '/v1/query',
                            {'address': 'private address'}, context('opaque-secret')))
    assert result.status == Status.ok
    assert 'opaque-secret' not in caplog.text and 'private address' not in caplog.text


def test_invalid_and_unconfigured_do_not_connect():
    transport = FakeTransport([httpx.Response(200, json={})])
    g = gateway(transport)
    assert run(g.request('p', 'PUT', '/x', {}, context())).status == Status.invalid_input
    assert run(g.request('missing', 'GET', '/x', {}, context())).status == Status.unconfigured
    assert run(g.request('p', 'GET', '//localhost/x', {}, context())).status == Status.invalid_input
    assert transport.calls == 0


def test_dns_pinned_and_scope_not_on_wire():
    seen = []
    def reply(request):
        seen.append(request)
        return httpx.Response(200, json={'ok': True})
    transport = FakeTransport([reply])
    result = run(gateway(transport).request('p', 'GET', '/v1/query', {'q': 'synthetic'}, context('opaque-secret')))
    assert result.status == Status.ok
    assert seen[0].url.host == '93.184.215.14'
    assert seen[0].headers['host'] == 'api.example.com'
    assert seen[0].extensions['sni_hostname'] == 'api.example.com'
    assert 'opaque-secret' not in str(seen[0].url) and 'opaque-secret' not in str(seen[0].headers)


def test_explicit_trusted_proxy_uses_approved_hostname_without_local_dns():
    g = HttpGateway({'p': ProviderConfig(id='p', endpoint='https://api.example.com')},
                    policy(), InMemoryBudget(2, Decimal('0')),
                    resolver=lambda _: (_ for _ in ()).throw(AssertionError('local DNS called')),
                    trusted_proxy_url='http://proxy:8080',
                    cost_per_call=Decimal('0'))
    assert run(g._validate_url('https://api.example.com/v1/query')) == 'api.example.com'


def test_trusted_proxy_cannot_bypass_dns_with_custom_transport(monkeypatch):
    with pytest.raises(ValueError, match='invalid trusted proxy'):
        HttpGateway({'p': ProviderConfig(id='p', endpoint='https://api.example.com')},
                    policy(), InMemoryBudget(2, Decimal('0')),
                    transport=FakeTransport([httpx.Response(200, json={'ok': True})]),
                    trusted_proxy_url='http://proxy:8080',
                    cost_per_call=Decimal('0'))

    transport = FakeTransport([httpx.Response(200, json={'ok': True})])
    g = HttpGateway({'p': ProviderConfig(id='p', endpoint='https://api.example.com')},
                    policy(), InMemoryBudget(2, Decimal('0')),
                    trusted_proxy_url='http://proxy:8080', cost_per_call=Decimal('0'))
    g.transport = transport
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **_: (_ for _ in ()).throw(AssertionError('client opened')))
    result = run(g.request('p', 'GET', '/v1/query', {}, context()))
    assert result.status == Status.unconfigured and transport.calls == 0


def test_trusted_proxy_rejects_embedded_credentials_before_requests():
    with pytest.raises(ValueError, match='invalid trusted proxy'):
        HttpGateway({'p': ProviderConfig(id='p', endpoint='https://api.example.com')},
                    policy(), InMemoryBudget(2, Decimal('0')),
                    trusted_proxy_url='http://user:secret@proxy:8080',
                    cost_per_call=Decimal('0'))


def test_private_dns_and_auth_do_not_retry():
    transport = FakeTransport([httpx.Response(200, json={'ok': 1})])
    g = gateway(transport)
    g.resolver = lambda host: ['10.0.0.4', '93.184.215.14']
    assert run(g.request('p', 'GET', '/x', {}, context())).status == Status.unconfigured
    assert transport.calls == 0
    auth = FakeTransport([httpx.Response(401), httpx.Response(200, json={})])
    assert run(gateway(auth).request('p', 'GET', '/x', {}, context())).status == Status.unconfigured
    assert auth.calls == 1


def test_cost_reservation_is_atomic():
    budget = InMemoryBudget(2, Decimal('0.50'))
    async def spend():
        return await asyncio.gather(*(budget.reserve('p', 1, Decimal('0.40')) for _ in range(2)))
    assert run(spend()) == [True, False]
    assert budget.calls == 1 and budget.reserved_cost == Decimal('0.40')


def test_same_origin_redirect_explicit_only():
    transport = FakeTransport([httpx.Response(302, headers={'Location': '/next'}), httpx.Response(200, json={'ok': 1})])
    result = run(gateway(transport, redirect_hosts=('api.example.com',)).request('p', 'GET', '/start', {}, context()))
    assert result.status == Status.ok and transport.calls == 2
    no_redirect = FakeTransport([httpx.Response(302, headers={'Location': '/next'})])
    assert run(gateway(no_redirect).request('p', 'GET', '/start', {}, context())).status == Status.unavailable
    assert no_redirect.calls == 1


def test_deadline_covers_dns_before_network():
    async def slow_dns(host):
        await asyncio.sleep(0.05)
        return ['93.184.215.14']
    transport = FakeTransport([httpx.Response(200, json={})])
    limits = policy(deadline=0.001)
    g = gateway(transport, limits=limits)
    g.resolver = slow_dns
    result = run(g.request('p', 'GET', '/x', {}, context()))
    assert result.status == Status.unavailable and transport.calls == 0
