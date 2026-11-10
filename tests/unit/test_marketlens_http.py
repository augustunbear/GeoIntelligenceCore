import asyncio
import time
from urllib.parse import parse_qs

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.providers.overpass import OverpassPlaceProvider
from test_http_policy import FakeTransport, context, gateway, policy, run
from test_overpass import Gateway, CONTEXT
from test_places import query


def test_form_post_keeps_query_in_body_and_handles_unicode():
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={'elements': []})
    g = gateway(FakeTransport([respond]), limits=policy(size=10000))
    ql = '[out:json];nwr["name"="Café & 茶"];out center;'
    result = run(g.request('p', 'POST', '/api/interpreter', {'data': ql}, context(), form=True))
    assert result.status == Status.ok
    assert seen[0].url.query == b''
    assert seen[0].headers['content-type'] == 'application/x-www-form-urlencoded;charset=UTF-8'
    assert parse_qs(seen[0].content.decode()) == {'data': [ql]}


def test_transient_retry_counts_each_attempt_and_is_opt_in():
    responses = [httpx.Response(502), httpx.Response(504), httpx.Response(200, json={'ok': 1})]
    transport = FakeTransport(responses)
    result = run(gateway(transport, limits=policy(calls=3)).request('p', 'GET', '/x', {}, context(), retry_transient=True))
    assert result.status == Status.ok and transport.calls == 3
    transport = FakeTransport(responses)
    assert run(gateway(transport).request('p', 'GET', '/x', {}, context())).status == Status.unavailable
    assert transport.calls == 1


def test_transient_retries_cannot_exceed_budget_or_deadline():
    transport = FakeTransport([httpx.Response(502)])
    result = run(gateway(transport, limits=policy(calls=1)).request('p', 'POST', '/x', {'data': 'q'}, context(), form=True, retry_transient=True))
    assert result.status == Status.rate_limited and transport.calls == 1
    transport = FakeTransport([httpx.Response(503, headers={'Retry-After': '60'})])
    result = run(gateway(transport, limits=policy(deadline=.1)).request('p', 'GET', '/x', {}, context(), retry_transient=True))
    assert result.status == Status.unavailable and transport.calls == 1


@pytest.mark.parametrize('method,params', [('GET', {'data': 'x'}), ('POST', {'data': {'nested': 1}}), ('POST', {'scope_token': 'secret'})])
def test_invalid_form_requests_do_not_connect(method, params):
    transport = FakeTransport([httpx.Response(200, json={})])
    result = run(gateway(transport).request('p', method, '/x', params, context(), form=True))
    assert result.status == Status.invalid_input and transport.calls == 0


def test_json_post_remains_json():
    seen = []
    transport = FakeTransport([lambda r: (seen.append(r) or httpx.Response(200, json={}))])
    assert run(gateway(transport).request('p', 'POST', '/x', {'x': 1}, context())).status == Status.ok
    assert seen[0].headers['content-type'] == 'application/json'
    assert seen[0].content == b'{"x": 1}'


def test_overpass_can_select_post_without_changing_default():
    class FormGateway(Gateway):
        async def request(self, *args, **kwargs):
            self.options = kwargs
            return await super().request(*args)
    g = FormGateway()
    result = asyncio.run(OverpassPlaceProvider(g, request_method='POST').search(query(), CONTEXT))
    assert result.status == Status.ok
    assert g.calls[0][1] == 'POST'
    assert g.options == {'form': True, 'retry_transient': True}
    assert result.context.effective_conditions['provider_http_method'] == 'POST'
    with pytest.raises(ValueError):
        OverpassPlaceProvider(g, request_method='PUT')


def test_factory_exposes_post_and_transient_network_failure_is_retryable():
    from geo_intelligence_core.providers.trial import TrialSettings, build_trial_provider
    from geo_intelligence_core.providers.budget import InMemoryBudget
    settings = TrialSettings.public('overpass', application_name='synthetic', contact_url='https://example.com/contact')
    provider = build_trial_provider(settings, budget=InMemoryBudget(5, 0), overpass_request_method='POST')
    assert provider.request_method == 'POST'
    def broken(request):
        raise httpx.ConnectError('synthetic network failure', request=request)
    transport = FakeTransport([broken, httpx.Response(200, json={'ok': True})])
    result = run(gateway(transport).request('p', 'GET', '/x', {}, context(), retry_transient=True))
    assert result.status == Status.ok and transport.calls == 2


def test_deadline_also_bounds_response_cleanup():
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.Event().wait()
            yield b'{}'
        async def aclose(self):
            await asyncio.sleep(.3)
    transport = FakeTransport([httpx.Response(200, stream=Stream())])
    started = time.monotonic()
    result = run(gateway(transport, limits=policy(deadline=.02)).request('p', 'GET', '/x', {}, context()))
    assert result.status == Status.unavailable
    assert time.monotonic() - started < .15
