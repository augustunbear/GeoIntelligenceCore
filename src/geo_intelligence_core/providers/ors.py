"""OpenRouteService directions and directed matrix adapter (offline-testable)."""
from __future__ import annotations

import math
from typing import Literal
from urllib.parse import urlsplit

from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.policy import ProviderConfig
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.spatial import MatrixCell, MatrixRequest, Route, RouteRequest, TravelMatrix
from .http import HttpGateway

_PROFILES = {'walking': 'foot-walking', 'cycling': 'cycling-regular', 'driving': 'driving-car'}
_HOST = 'api.heigit.org'


def _failure(status: Status, code: str, context: RequestContext, *, kind):
    return Result[kind](status=status, data=None,
                        issues=[Issue(code=code, message_key=f'routing.{code}')], context=context)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


class OrsRoutingProvider:
    """Requires an explicitly permitted HeiGIT endpoint and gateway credentials.

    The gateway owns budgets, DNS pinning, retry, limits and authorization headers.
    No public endpoint is activated merely by constructing this adapter.
    """
    def __init__(self, gateway: HttpGateway, provider_id: str = 'ors', *,
                 distance_unit: Literal['m', 'km'] = 'm'):
        self.gateway = gateway
        self.provider_id = provider_id
        self.distance_unit = distance_unit

    def _preflight(self, mode, context, kind, *, time=None, time_kind='depart_at'):
        cfg: ProviderConfig | None = self.gateway.providers.get(self.provider_id)
        if cfg is None or not cfg.endpoint or not cfg.credential_handle:
            return _failure(Status.unconfigured, 'credentials_or_endpoint', context, kind=kind)
        url = urlsplit(cfg.endpoint)
        if url.scheme != 'https' or url.hostname != _HOST or url.path.rstrip('/') not in ('', '/openrouteservice'):
            return _failure(Status.unconfigured, 'unapproved_endpoint', context, kind=kind)
        if not cfg.capability_flags.get(kind.__name__.lower(), False) or kind.__name__.lower() not in self.gateway.policy.allowed_capabilities:
            return _failure(Status.disabled, 'capability_disabled', context, kind=kind)
        if mode not in _PROFILES:
            return _failure(Status.unsupported, 'mode', context, kind=kind)
        # ORS's ordinary graph route/matrix is not a timetable or traffic forecast.
        if time is not None or time_kind != 'depart_at':
            return _failure(Status.unsupported, 'time_condition', context, kind=kind)
        return None

    async def route(self, request: RouteRequest, context: RequestContext) -> Result[Route]:
        failure = self._preflight(request.mode, context, Route, time=request.time,
                                  time_kind=request.time_kind)
        if failure is not None:
            return failure
        body = {'coordinates': [[request.origin.longitude, request.origin.latitude],
                                [request.destination.longitude, request.destination.latitude]],
                'units': self.distance_unit}
        reply = await self.gateway.request(self.provider_id, 'POST',
            f'/v2/directions/{_PROFILES[request.mode]}/geojson', body, context)
        if reply.status != Status.ok:
            return Result[Route](status=reply.status, data=None, issues=reply.issues, context=context)
        try:
            raw = reply.data
            features = raw['features']
            if not isinstance(features, (list, tuple)) or not features:
                return _failure(Status.unavailable, 'no_route', context, kind=Route)
            summary = features[0]['properties']['summary']
            geometry = features[0]['geometry']
            unit = raw['metadata']['query']['units']
            distance, duration = summary['distance'], summary['duration']
            if unit != self.distance_unit or unit not in ('m', 'km') or not _number(distance) or not _number(duration):
                raise ValueError('missing or inconsistent unit/quantity')
            if geometry['type'] != 'LineString' or not isinstance(geometry['coordinates'], (list, tuple)) or len(geometry['coordinates']) < 2:
                raise ValueError('invalid route geometry')
            # Validate every coordinate and direction endpoints; never reverse geometry silently.
            coords = geometry['coordinates']
            if any(not isinstance(p, (list, tuple)) or len(p) < 2 or not all(type(v) in (int, float) and math.isfinite(v) for v in p[:2]) for p in coords):
                raise ValueError('invalid route coordinates')
            route = Route(distance_m=float(distance * (1000 if unit == 'km' else 1)),
                          duration_s=float(duration), geometry=geometry,
                          mode=request.mode, origin=request.origin, destination=request.destination)
            return Result[Route](status=Status.ok, data=route, context=context)
        except (KeyError, TypeError, IndexError, ValueError, OverflowError):
            return _failure(Status.unknown, 'invalid_route_response', context, kind=Route)

    async def matrix(self, request: MatrixRequest, context: RequestContext) -> Result[TravelMatrix]:
        failure = self._preflight(request.mode, context, TravelMatrix, time=request.time,
                                  time_kind=request.time_kind)
        if failure is not None:
            return failure
        if not request.origins or not request.destinations:
            return _failure(Status.invalid_input, 'empty_matrix', context, kind=TravelMatrix)
        origins, destinations = list(request.origins.items()), list(request.destinations.items())
        # Keep ordered, independent origin and destination lists even for overlapping IDs.
        body = {'locations': [[p.longitude, p.latitude] for _, p in origins + destinations],
                'sources': list(range(len(origins))),
                'destinations': list(range(len(origins), len(origins) + len(destinations))),
                'metrics': ['duration']}
        reply = await self.gateway.request(self.provider_id, 'POST',
            f'/v2/matrix/{_PROFILES[request.mode]}', body, context)
        if reply.status != Status.ok:
            return Result[TravelMatrix](status=reply.status, data=None, issues=reply.issues, context=context)
        try:
            durations = reply.data['durations']
            if (not isinstance(durations, (list, tuple)) or len(durations) != len(origins) or
                any(not isinstance(row, (list, tuple)) or len(row) != len(destinations) for row in durations)):
                raise ValueError('matrix dimensions')
            cells = []
            for i, (oid, _) in enumerate(origins):
                for j, (did, _) in enumerate(destinations):
                    duration = durations[i][j]
                    if duration is not None and not _number(duration):
                        raise ValueError('invalid duration')
                    cells.append(MatrixCell(origin_id=oid, destination_id=did,
                        duration_s=float(duration) if duration is not None else None,
                        status=Status.ok if duration is not None else Status.unavailable))
            status = Status.partial if any(c.status != Status.ok for c in cells) and any(c.status == Status.ok for c in cells) else (
                Status.unavailable if all(c.status != Status.ok for c in cells) else Status.ok)
            return Result[TravelMatrix](status=status, data=TravelMatrix(cells=tuple(cells)),
                issues=[Issue(code='no_route_cells', message_key='routing.no_route_cells')] if status != Status.ok else [],
                context=context)
        except (KeyError, TypeError, ValueError):
            return _failure(Status.unknown, 'invalid_matrix_response', context, kind=TravelMatrix)
