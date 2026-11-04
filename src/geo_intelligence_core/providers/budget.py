"""Atomic single-process provider budget."""
import asyncio
from decimal import Decimal

class InMemoryBudget:
    def __init__(self, max_calls: int, cost_ceiling: Decimal):
        if type(max_calls) is not int or max_calls < 0 or cost_ceiling is None or cost_ceiling < 0:
            raise ValueError('finite limits required')
        self.max_calls, self.cost_ceiling = max_calls, Decimal(cost_ceiling)
        self.calls = 0
        self.reserved_cost = Decimal(0)
        self.actual_cost = Decimal(0)
        self.by_provider = {}
        self._lock = asyncio.Lock()

    async def reserve(self, provider_id: str, calls: int, estimated_cost: Decimal) -> bool:
        cost = Decimal(estimated_cost)
        if not provider_id or type(calls) is not int or calls < 1 or not cost.is_finite() or cost < 0:
            raise ValueError('invalid reservation')
        async with self._lock:
            if self.calls + calls > self.max_calls or self.reserved_cost + cost > self.cost_ceiling:
                return False
            self.calls += calls
            self.reserved_cost += cost
            self.by_provider[provider_id] = self.by_provider.get(provider_id, 0) + calls
            return True

    async def record(self, provider_id: str, actual_cost: Decimal) -> None:
        cost = Decimal(actual_cost)
        if not provider_id or not cost.is_finite() or cost < 0:
            raise ValueError('invalid cost')
        async with self._lock:
            if self.actual_cost + cost > self.reserved_cost:
                raise ValueError('actual exceeds reservations')
            self.actual_cost += cost
