"""OpenRouteService directions and directed matrix adapter (offline-testable)."""
from __future__ import annotations

import math
from typing import Literal
from urllib.parse import urlsplit

from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.policy import ProviderConfig
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.spatial import (Catchment, CatchmentRequest, GeometryLimits,
    MatrixCell, MatrixRequest, Region, Route, RouteRequest, TravelMatrix)
from geo_intelligence_core.catchments import checked_network_polygon, nesting_violations
from geo_intelligence_core.geometry import _GeometryProblem
from .http import HttpGateway

_PROFILES = {'walking': 'foot-walking', 'cycling': 'cycling-regular', 'driving': 'driving-car'}
_HOST = 'api.heigit.org'


def _failure(status: Status, code: str, context: RequestContext, *, kind):
    return Result[kind](status=status, data=None,
                        issues=[Issue(code=code, message_key=f'routing.{code}')], context=context)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _endpoint_distance_m(coordinate, point):
    """Great-circle separation for checking provider route endpoint snapping."""
    lon1, lat1 = map(math.radians, coordinate[:2])
    lon2, lat2 = map(math.radians, (point.longitude, point.latitude))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1.0, math.sqrt(a)))


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
            if (_endpoint_distance_m(coords[0], request.origin) > 250 or
                    _endpoint_distance_m(coords[-1], request.destination) > 250):
                raise ValueError('route endpoints do not match requested direction')
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

    async def catchments(self, request: CatchmentRequest, context: RequestContext) -> Result[list[Catchment]]:
        failure = self._preflight(request.mode, context, Catchment, time=request.time,
                                  time_kind=request.time_kind)
        if failure is not None:
            return failure
        cfg = self.gateway.providers[self.provider_id]
        if request.direction == 'inbound' and not cfg.capability_flags.get('catchment_inbound', False):
            return _failure(Status.unsupported, 'inbound_not_enabled', context, kind=Catchment)
        if not request.durations_s or any(v <= 0 for v in request.durations_s):
            return _failure(Status.invalid_input, 'durations', context, kind=Catchment)
        point = request.location.point
        if request.entrance_id is not None:
            entrance = next((e for e in request.location.entrances if e.id == request.entrance_id), None)
            if entrance is None or request.mode not in entrance.modes:
                return _failure(Status.invalid_input, 'entrance', context, kind=Catchment)
            point = entrance.point
        policy = self.gateway.policy
        if policy.max_area_m2 is None or policy.max_geometry_vertices is None:
            return _failure(Status.unconfigured, 'geometry_limits', context, kind=Catchment)
        limits = GeometryLimits(max_area_m2=policy.max_area_m2,
                                max_vertices=policy.max_geometry_vertices)
        durations = sorted(set(request.durations_s))
        location_type = 'destination' if request.direction == 'inbound' else 'start'
        body = {'locations': [[point.longitude, point.latitude]], 'range': durations,
                'range_type': 'time', 'location_type': location_type}
        reply = await self.gateway.request(self.provider_id, 'POST',
            f'/v2/isochrones/{_PROFILES[request.mode]}', body, context)
        if reply.status != Status.ok:
            return Result[list[Catchment]](status=reply.status, data=None,
                                           issues=reply.issues, context=context)
        try:
            raw = reply.data
            query = raw['metadata']['query']
            if (query['location_type'] != location_type or query['range_type'] != 'time' or
                tuple(query['range']) != tuple(durations)):
                raise ValueError('response query does not match request')
            features = raw['features']
            if not isinstance(features, (list, tuple)) or len(features) != len(durations):
                raise ValueError('missing thresholds')
            by_duration = {}
            for feature in features:
                properties = feature['properties']
                duration = properties['value']
                if (type(duration) is not int or duration not in durations or
                    duration in by_duration or properties['group_index'] != 0):
                    raise ValueError('unexpected threshold or group')
                geometry = feature['geometry']
                try:
                    polygon = checked_network_polygon(geometry, limits=limits)
                except _GeometryProblem as exc:
                    if exc.code == 'geometry_extra_missing':
                        return _failure(Status.unavailable, exc.code, context, kind=Catchment)
                    return _failure(Status.unknown, 'invalid_isochrone_polygon', context, kind=Catchment)
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    return _failure(Status.unknown, 'invalid_isochrone_polygon', context, kind=Catchment)
                region = Region(id=f'{self.provider_id}:{request.location.id}:{request.location.version}:{request.direction}:{request.mode}:{duration}',
                    version='1', geometry=geometry, method='ors_isochrone_time',
                    source_ref=self.provider_id, boundary_rule='point_covers')
                by_duration[duration] = (Catchment(region=region, direction=request.direction,
                    mode=request.mode, duration_s=duration, time=request.time), polygon)
            ordered = [by_duration[d] for d in durations]
            nested = not nesting_violations([polygon for _, polygon in ordered])
            return Result[list[Catchment]](status=Status.ok if nested else Status.partial,
                data=[catchment for catchment, _ in ordered],
                issues=[] if nested else [Issue(code='non_nested_isochrones', message_key='routing.non_nested_isochrones')],
                context=context)
        except (KeyError, TypeError, IndexError, ValueError, AttributeError):
            return _failure(Status.unknown, 'invalid_isochrone_response', context, kind=Catchment)
