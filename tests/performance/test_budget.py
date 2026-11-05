"""Offline single-process budget replay; not a provider throughput benchmark."""
import asyncio
from decimal import Decimal
import statistics
import time
import tracemalloc

from geo_intelligence_core.providers.budget import InMemoryBudget


def test_budget_concurrent_reservation_never_exceeds_run_cap():
    max_calls = 3
    budget = InMemoryBudget(max_calls, Decimal("0"))

    async def replay():
        async def reserve():
            started = time.perf_counter()
            permitted = await budget.reserve("synthetic", 1, Decimal("0"))
            return permitted, (time.perf_counter() - started) * 1000

        return await asyncio.gather(*(reserve() for _ in range(12)))

    tracemalloc.start()
    try:
        measured = asyncio.run(replay())
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    accepted = sum(ok for ok, _ in measured)
    latencies_ms = sorted(duration for _, duration in measured)
    p50_ms = statistics.median(latencies_ms)
    p95_ms = latencies_ms[min(len(latencies_ms) - 1, int(0.95 * len(latencies_ms)))]
    assert accepted == budget.calls == max_calls
    assert budget.calls <= max_calls
    assert p50_ms >= 0 and p95_ms >= p50_ms and peak_bytes > 0
    # Values are observations only: real representative regions and multi-worker
    # shared-budget topology require a separately approved P13 activation run.
