"""FF-02 executable, synthetic shared-budget integration contract.

Run with the providers extra: PYTHONPATH=src python examples/python/shared_budget.py
No live network or database is used. This models one atomic service with several
clients; asyncio locks/dictionaries do NOT establish real cross-worker durability.
Replace StoreClient with the consumer's existing durable storage and shared-lock
adapter, then independently validate actual workers/restarts before activation.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import math
from types import MappingProxyType

import httpx

from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.providers.budget import BudgetUnavailable
from geo_intelligence_core.providers.http import HttpGateway


class SyntheticQuotaStore:
    """Test service: authoritative source mapping, policy, clock and transactions.

    State lives here, never in client/Budget objects. Retaining this object while
    recreating clients simulates client restart, not storage-process persistence.
    ``available`` supports synthetic outage scenarios only.
    """
    RUN_LIMIT = 5
    DAILY_LIMIT = 50

    def __init__(self, source_domains, *, clock=lambda: datetime.now(timezone.utc)):
        self.domains = MappingProxyType(dict(source_domains))
        if not self.domains or any(not k or not v for k, v in self.domains.items()):
            raise ValueError('explicit source quota domains required')
        self.clock, self.available = clock, True
        self._daily, self._runs, self._slots = {}, {}, {}
        self._transaction = asyncio.Lock()

    def _check(self):
        if not self.available:
            raise BudgetUnavailable('synthetic-backend-detail')

    def domain(self, provider_id):
        self._check()
        try:
            return self.domains[provider_id]
        except KeyError:
            raise BudgetUnavailable('source quota domain not configured') from None

    def _day(self):
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise BudgetUnavailable('authoritative UTC clock required')
        return now.astimezone(timezone.utc).date()

    async def reserve(self, provider_id, run_id, calls, estimated_cost):
        cost = Decimal(estimated_cost)
        if type(calls) is not int or calls < 1 or not cost.is_finite() or cost < 0:
            raise ValueError('invalid reservation')
        async with self._transaction:
            domain = self.domain(provider_id)
            day_key, run_key = (domain, self._day()), run_id
            day_used, run_used = self._daily.get(day_key, 0), self._runs.get(run_key, 0)
            # Model a storage scheduling boundary. Without the transaction lock,
            # two clients could both read the last available slot before writing.
            await asyncio.sleep(0)
            self._check()
            # One atomic conditional write; client/key aliases cannot raise caps.
            if cost != 0 or day_used + calls > self.DAILY_LIMIT or run_used + calls > self.RUN_LIMIT:
                return False
            self._daily[day_key], self._runs[run_key] = day_used + calls, run_used + calls
            return True

    async def record(self, provider_id, actual_cost):
        self.domain(provider_id)
        if Decimal(actual_cost) != 0:
            raise ValueError('zero-cost policy forbids actual charges')
        # Recording zero never refunds attempts or opens a new allowance.

    def daily_calls(self, domain):
        self._check()
        return self._daily.get((domain, self._day()), 0)

    @asynccontextmanager
    async def source_slot(self, provider_id):
        domain = self.domain(provider_id)
        lock = self._slots.setdefault(domain, asyncio.Lock())
        # Acquire outside try: cancellation while queued must not release owner.
        await lock.acquire()
        try:
            self._check()  # the store can fail while a caller was waiting
            yield
        finally:
            lock.release()  # consumed attempts remain charged on every exit


class StoreClient:
    """A distinct client of the shared service; owns no usage counter or lock."""
    def __init__(self, store):
        self.store = store

    async def reserve(self, provider_id, run_id, calls, estimated_cost):
        return await self.store.reserve(provider_id, run_id, calls, estimated_cost)

    async def record(self, provider_id, actual_cost):
        await self.store.record(provider_id, actual_cost)

    def source_slot(self, provider_id):
        return self.store.source_slot(provider_id)


class RunBudget:
    """Existing Budget port bound to a stable logical run ID, not an API key."""
    def __init__(self, client, run_id):
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError('stable run ID required')
        self.client, self.run_id = client, run_id

    async def reserve(self, provider_id: str, calls: int, estimated_cost: Decimal) -> bool:
        return await self.client.reserve(provider_id, self.run_id, calls, estimated_cost)

    async def record(self, provider_id: str, actual_cost: Decimal) -> None:
        await self.client.record(provider_id, actual_cost)


async def invoke_guarded(client, provider_id, invoke, context, *, timeout_s=10.0):
    """Caller wraps the full provider operation, separately from reserve().

    The timeout covers waiting for the shared slot plus the invocation. A real
    adapter must release only its own lock, handle lost ownership safely, and
    keep its lease valid until HTTP work/cancellation has finished.
    """
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError('finite positive shared operation deadline required')
    try:
        async with asyncio.timeout(timeout_s):
            async with client.source_slot(provider_id):
                return await invoke()
    except BudgetUnavailable:
        code = 'budget_unavailable'
    except TimeoutError:
        code = 'shared_deadline'
    return Result(status=Status.unavailable, data=None, context=context,
                  issues=(Issue(code=code, message_key=f'provider.{code}'),))


async def main():
    store = SyntheticQuotaStore({'instance-a': 'source-a', 'instance-alias': 'source-a'})
    # Consume 49 of the default 50 attempts via successful synthetic reservations.
    for i in range(10):
        await RunBudget(StoreClient(store), f'prefill-{i}').reserve('instance-a', min(5, 49 - 5 * i), Decimal(0))
    attempts = 0
    def reply(_):
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={'synthetic': True})
    async def worker(provider_id, run_id):
        client = StoreClient(store)
        policy = UsagePolicy(allowed_endpoints=('https://geo.example.org',),
            max_calls_per_run=5, max_concurrency=1, deadline_s=1.0, max_response_bytes=1000,
            cost_ceiling=Decimal(0), currency='EUR', pricing_ref='synthetic-zero-cost')
        gateway = HttpGateway({provider_id: ProviderConfig(id=provider_id, endpoint='https://geo.example.org')},
            policy, RunBudget(client, run_id), cost_per_call=Decimal(0),
            resolver=lambda _: ['93.184.215.14'], transport=httpx.MockTransport(reply))
        context = RequestContext(request_id=run_id)
        return await invoke_guarded(client, provider_id,
            lambda: gateway.request(provider_id, 'GET', '/api', {}, context), context)
    results = await asyncio.gather(worker('instance-a', 'run-a'), worker('instance-alias', 'run-b'))
    print('synthetic service with two clients; NOT persistent multi-worker validation')
    print('HTTP attempts:', attempts, '; statuses:', ', '.join(r.status for r in results))


if __name__ == '__main__':
    asyncio.run(main())
