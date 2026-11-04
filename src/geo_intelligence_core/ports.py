"""Typed provider ports and explicit in-memory capability registration."""
from decimal import Decimal
from typing import Protocol
from .models.common import Result
from .models.location import Candidate
from .models.requests import RequestContext
from .models.spatial import RouteRequest, MatrixRequest, CatchmentRequest, Route, TravelMatrix, Catchment
from .models.places import PlaceQuery, PlaceSet


class LocationResolver(Protocol):
    async def search(self, request: object, context: RequestContext) -> Result[list[Candidate]]: ...
    async def reverse(self, request: object, context: RequestContext) -> Result[list[Candidate]]: ...


class PlaceProvider(Protocol):
    async def search(self, request: PlaceQuery, context: RequestContext) -> Result[PlaceSet]: ...


class RoutingProvider(Protocol):
    async def route(self, request: RouteRequest, context: RequestContext) -> Result[Route]: ...
    async def matrix(self, request: MatrixRequest, context: RequestContext) -> Result[TravelMatrix]: ...
    async def catchments(self, request: CatchmentRequest, context: RequestContext) -> Result[list[Catchment]]: ...


class Budget(Protocol):
    async def reserve(self, provider_id: str, calls: int, estimated_cost: Decimal) -> bool: ...
    async def record(self, provider_id: str, actual_cost: Decimal) -> None: ...


class ProviderRegistry:
    def __init__(self):
        self._ports: dict[str, tuple[object, bool]] = {}

    def register(self, capability_id: str, port: object, *, configured: bool = True) -> None:
        if not capability_id or capability_id in self._ports:
            raise ValueError('capability ID must be unique and nonempty')
        self._ports[capability_id] = (port, configured)

    def status(self, capability_id: str) -> str:
        record = self._ports.get(capability_id)
        return 'unconfigured' if record is None or not record[1] else 'ok'

    def get(self, capability_id: str) -> object | None:
        record = self._ports.get(capability_id)
        return record[0] if record and record[1] else None
