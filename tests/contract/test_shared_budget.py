"""Synthetic shared-service contracts, NOT real multi-worker storage validation."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import runpy

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.providers.http import HttpGateway


EXAMPLE = Path(__file__).parents[2] / 'examples/python/shared_budget.py'
spec = importlib.util.spec_from_file_location('shared_budget_example', EXAMPLE)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)

CTX = RequestContext(request_id='synthetic-budget')


class Clock:
    now = datetime(2026, 11, 4, 23, 59, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


def backend(clock=None):
    return example.SyntheticQuotaStore({'p': 'source-a', 'alias': 'source-a', 'other': 'source-b'},
                                       clock=clock or Clock())


def client(store):
    # Separate client objects model independent callers of one atomic service.
    return example.StoreClient(store)


def gateway(budget, *, provider_id='p', reply=None, deadline=1.0, price='0', headers=None):
    seen = []
    async def handler(request):
        seen.append(request)
        if reply is not None:
            result = reply(request)
            return await result if asyncio.iscoroutine(result) else result
        return httpx.Response(200, json={'synthetic': True})
    policy = UsagePolicy(allowed_endpoints=('https://geo.example.org',),
                         max_calls_per_run=5, max_concurrency=1, deadline_s=deadline,
                         max_response_bytes=1000, cost_ceiling=Decimal(0),
                         currency='EUR', pricing_ref='synthetic-zero-cost')
    g = HttpGateway({provider_id: ProviderConfig(id=provider_id, endpoint='https://geo.example.org')},
                    policy, budget, cost_per_call=Decimal(price), headers=headers,
                    transport=httpx.MockTransport(handler), resolver=lambda _: ['93.184.215.14'],
                    allowed_redirect_hosts=('geo.example.org',))
    return g, seen


async def request(g, provider_id='p'):
    return await g.request(provider_id, 'GET', '/api', {}, CTX)


async def fill(store, calls, domain_provider='p'):
    for i in range((calls + 4) // 5):
        budget = example.RunBudget(client(store), f'prefill-{domain_provider}-{i}')
        assert await budget.reserve(domain_provider, min(5, calls - i * 5), Decimal(0))


def test_shared_last_slot():
    async def run():
        store = backend()
        await fill(store, 49)
        a, seen_a = gateway(example.RunBudget(client(store), 'worker-a'))
        b, seen_b = gateway(example.RunBudget(client(store), 'worker-b'), provider_id='alias')
        results = await asyncio.gather(request(a), request(b, 'alias'))
        assert sorted(r.status for r in results) == [Status.ok, Status.rate_limited]
        assert len(seen_a) + len(seen_b) == 1
        assert store.daily_calls('source-a') == 50
    asyncio.run(run())


def test_retry_counts():
    async def run():
        store = backend()
        a, seen = gateway(example.RunBudget(client(store), 'same-run'),
                          reply=lambda _: httpx.Response(429, headers={'Retry-After': '0'}))
        assert (await request(a)).status == Status.rate_limited
        assert len(seen) == store.daily_calls('source-a') == 5
        # Reconstruct both client and Budget and rotate key/instance alias.
        b, more = gateway(example.RunBudget(client(store), 'same-run'), provider_id='alias',
                          headers={'Authorization': 'synthetic-rotated'})
        assert (await request(b, 'alias')).status == Status.rate_limited
        assert not more
        c, other_run = gateway(example.RunBudget(client(store), 'new-run'))
        assert (await request(c)).status == Status.ok
        assert len(other_run) == 1 and store.daily_calls('source-a') == 6
    asyncio.run(run())


def test_redirect_attempts_share_the_last_daily_slots():
    async def run():
        store = backend()
        await fill(store, 49)
        g, seen = gateway(example.RunBudget(client(store), 'redirect-run'),
                          reply=lambda _: httpx.Response(302, headers={'Location': '/next'}))
        result = await request(g)
        assert result.status == Status.rate_limited and result.data is None
        assert len(seen) == 1 and store.daily_calls('source-a') == 50
    asyncio.run(run())


def test_zero_cost_cannot_be_raised_or_refunded():
    async def run():
        store = backend()
        budget = example.RunBudget(client(store), 'free-run')
        g, seen = gateway(budget, price='0.01')
        assert (await request(g)).status == Status.rate_limited
        assert not seen and store.daily_calls('source-a') == 0
        assert await budget.reserve('p', 5, Decimal(0))
        await budget.record('alias', Decimal(0))
        with pytest.raises(ValueError):
            await budget.record('p', Decimal('0.01'))
        assert not await budget.reserve('alias', 1, Decimal(0))
        assert store.daily_calls('source-a') == 5
    asyncio.run(run())


def test_restart_and_utc_reset():
    async def run():
        clock = Clock()
        # Local date is already Nov 5, but source quota still belongs to UTC Nov 4.
        clock.now = datetime(2026, 11, 5, 0, 59, tzinfo=timezone(timedelta(hours=1)))
        store = backend(clock)
        await fill(store, 50)
        restarted, seen = gateway(example.RunBudget(client(store), 'fresh-worker'))
        assert (await request(restarted)).status == Status.rate_limited
        assert not seen
        clock.now = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
        again, seen = gateway(example.RunBudget(client(store), 'fresh-worker'))
        assert (await request(again)).status == Status.ok
        assert len(seen) == 1 and store.daily_calls('source-a') == 1
        # A UTC day boundary must not reset the five attempts in an existing run.
        old_run, seen = gateway(example.RunBudget(client(store), 'prefill-p-0'))
        assert (await request(old_run)).status == Status.rate_limited and not seen
        # Distinct source domains retain independent quotas.
        other, seen = gateway(example.RunBudget(client(store), 'separate-source-run'), provider_id='other')
        assert (await request(other, 'other')).status == Status.ok and len(seen) == 1
    asyncio.run(run())


def test_run_limit_is_shared_between_sources():
    async def run():
        store = backend()
        budget = example.RunBudget(client(store), 'multi-source-run')
        assert await budget.reserve('p', 5, Decimal(0))
        other, seen = gateway(example.RunBudget(client(store), 'multi-source-run'), provider_id='other')
        assert (await request(other, 'other')).status == Status.rate_limited
        assert not seen and store.daily_calls('source-b') == 0
    asyncio.run(run())


@pytest.mark.parametrize('timeout', [None, float('inf'), float('nan'), -1, 0])
def test_shared_slot_requires_a_finite_deadline(timeout):
    async def run():
        store = backend()
        c = client(store)
        g, seen = gateway(example.RunBudget(c, 'deadline'))
        with pytest.raises(ValueError):
            await example.invoke_guarded(c, 'p', lambda: request(g), CTX, timeout_s=timeout)
        assert not seen and store.daily_calls('source-a') == 0
    asyncio.run(run())


@pytest.mark.parametrize('when', ['before', 'retry'])
def test_store_unavailable(when):
    async def run():
        store = backend()
        def reply(_):
            store.available = False
            return httpx.Response(429, headers={'Retry-After': '0'})
        g, seen = gateway(example.RunBudget(client(store), 'store-failure'), reply=reply)
        store.available = when != 'before'
        result = await request(g)
        assert result.status == Status.unavailable and result.data is None
        assert result.issues[0].code == 'budget_unavailable'
        assert len(seen) == (0 if when == 'before' else 1)
        assert 'synthetic-backend-detail' not in result.model_dump_json()
        store.available = True
        assert store.daily_calls('source-a') == len(seen)
    asyncio.run(run())


def test_source_slot_store_failure_is_explicit_and_does_not_invoke():
    async def run():
        store = backend()
        c = client(store)
        g, seen = gateway(example.RunBudget(c, 'slot-failure'))
        store.available = False
        result = await example.invoke_guarded(c, 'p', lambda: request(g), CTX)
        assert result.status == Status.unavailable and result.data is None
        assert result.issues[0].code == 'budget_unavailable' and not seen
    asyncio.run(run())


@pytest.mark.parametrize('outcome', ['success', 'network_error', 'exception', 'timeout', 'cancel'])
def test_shared_concurrency_release(outcome):
    async def run():
        store = backend()
        a_client, b_client = client(store), client(store)
        entered, release, queued, second_entered = (asyncio.Event() for _ in range(4))
        active = peak = 0
        async def first_reply(_):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            entered.set()
            try:
                await release.wait()
                if outcome == 'network_error':
                    raise httpx.ConnectError('synthetic')
                if outcome == 'exception':
                    raise RuntimeError('synthetic-adapter-exception')
                return httpx.Response(200, json={'ok': True})
            finally:
                active -= 1
        async def second_reply(_):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            second_entered.set()
            await asyncio.sleep(0)
            active -= 1
            return httpx.Response(200, json={'ok': True})
        a, seen_a = gateway(example.RunBudget(a_client, 'first'), reply=first_reply,
                            deadline=0.2 if outcome == 'timeout' else 1.0)
        b, seen_b = gateway(example.RunBudget(b_client, 'second'), provider_id='alias', reply=second_reply)
        t1 = asyncio.create_task(example.invoke_guarded(a_client, 'p', lambda: request(a), CTX))
        await asyncio.wait_for(entered.wait(), 0.5)
        async def second():
            queued.set()
            return await example.invoke_guarded(b_client, 'alias', lambda: request(b, 'alias'), CTX)
        t2 = asyncio.create_task(second())
        await queued.wait()
        # Give the competing HTTP task a bounded opportunity to enter while the
        # first remains blocked. Merely scheduling t2 would not prove exclusion.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(second_entered.wait(), 0.01)
        assert not seen_b  # queued on the shared source, not just a local gateway slot
        if outcome == 'cancel':
            t1.cancel()
        elif outcome != 'timeout':
            release.set()
        if outcome == 'cancel':
            with pytest.raises(asyncio.CancelledError):
                await t1
        elif outcome == 'exception':
            with pytest.raises(RuntimeError, match='synthetic-adapter'):
                await t1
        else:
            first = await t1
            assert first.status == (Status.ok if outcome == 'success' else Status.unavailable)
        assert (await asyncio.wait_for(t2, 0.5)).status == Status.ok
        assert peak == 1 and active == 0 and len(seen_a) == len(seen_b) == 1
        assert store.daily_calls('source-a') == 2  # failures never refund consumed attempts
    asyncio.run(run())


def test_cancelled_waiter_does_not_release_owners_slot_or_spend():
    async def run():
        store = backend()
        a_client, b_client = client(store), client(store)
        async with a_client.source_slot('p'):
            b, seen = gateway(example.RunBudget(b_client, 'waiter'))
            task = asyncio.create_task(example.invoke_guarded(b_client, 'alias', lambda: request(b), CTX))
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            timed = await example.invoke_guarded(b_client, 'alias', lambda: request(b), CTX, timeout_s=0.01)
            assert timed.status == Status.unavailable and timed.issues[0].code == 'shared_deadline'
            assert not seen and store.daily_calls('source-a') == 0
        assert (await example.invoke_guarded(b_client, 'alias', lambda: request(b), CTX)).status == Status.ok
        assert len(seen) == 1
    asyncio.run(run())


def test_unknown_alias_cannot_create_new_quota():
    async def run():
        store = backend()
        g, seen = gateway(example.RunBudget(client(store), 'unknown'), provider_id='unregistered')
        result = await request(g, 'unregistered')
        assert result.status == Status.unavailable and not seen
    asyncio.run(run())


def test_example_runs_without_network(monkeypatch, capsys):
    monkeypatch.setattr('socket.getaddrinfo', lambda *a, **k: pytest.fail('example requested DNS'))
    runpy.run_path(str(EXAMPLE), run_name='__main__')
    out = capsys.readouterr().out
    assert 'synthetic' in out and 'HTTP attempts: 1' in out and 'rate_limited' in out
