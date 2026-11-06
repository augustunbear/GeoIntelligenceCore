"""Explicit, offline construction of bounded free trial adapters.

The caller owns persistent daily quotas and provider activation. No credentials
belong in settings; pass authentication headers only at construction time.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
import re
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import ConfigDict, Field, ValidationError, model_validator

from geo_intelligence_core.models.common import FrozenModel
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.ports import Budget, LocationResolver, PlaceProvider, RoutingProvider
from .http import HttpGateway, UnsafeEndpoint, origin
from .ors import OrsRoutingProvider
from .overpass import OverpassPlaceProvider
from .photon import PhotonCapabilities, PhotonResolver

Protocol = Literal['photon', 'overpass', 'ors']


class TrialSettings(FrozenModel):
    """Serializable instance selection. Construct explicitly or use ``public``.

    ``period_limits`` must stay empty: a number in settings cannot enforce a
    daily quota across workers. Supply a caller-owned shared Budget to the factory.
    """
    model_config = ConfigDict(hide_input_in_errors=True)

    protocol: Protocol
    instance_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
    endpoint: str = Field(min_length=1)
    policy: UsagePolicy
    authentication_required: bool
    authentication_header: str = 'Authorization'
    capability_flags: dict[str, bool]
    photon_capabilities: PhotonCapabilities = Field(default_factory=PhotonCapabilities)
    cost_per_call: Decimal = Decimal(0)
    terms_ref: str = Field(min_length=1)
    rights_ref: str = Field(min_length=1)
    attribution: str = Field(min_length=1)
    user_agent: str = Field(min_length=1)
    daily_budget_requirement: Literal['caller_shared_budget_required'] = 'caller_shared_budget_required'

    @model_validator(mode='after')
    def validate_trial(self):
        # Reject credentials/query strings and ambiguous paths before they can be
        # copied into provenance. DNS/public-IP validation stays in HttpGateway.
        try:
            u = urlsplit(self.endpoint)
            endpoint_origin = origin(self.endpoint)
        except (ValueError, UnsafeEndpoint):
            raise ValueError('invalid trial endpoint') from None
        path = unquote(u.path)
        if (u.query or u.fragment or '\\' in path or
                any(c.isspace() or ord(c) < 32 for c in self.endpoint) or
                any(part in ('.', '..') for part in path.split('/'))):
            raise ValueError('invalid trial endpoint')
        p = self.policy
        if (p.allowed_endpoints != (endpoint_origin,) or p.max_calls_per_run < 1 or
                p.max_concurrency != 1 or p.deadline_s is None or
                p.max_response_bytes is None or p.cost_ceiling != 0 or
                not p.currency or not p.pricing_ref or p.period_limits or
                p.cache_policy != 'disabled' or self.cost_per_call != 0):
            raise ValueError('trial requires explicit bounded zero-cost policy; daily budget is caller-owned')
        if (not self.authentication_header or
                any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
                    for c in self.authentication_header) or
                self.authentication_header.lower() in ('host', 'user-agent', 'content-type', 'accept')):
            raise ValueError('invalid authentication header name')
        if any(ord(c) < 32 or ord(c) > 126 for c in self.user_agent):
            raise ValueError('invalid User-Agent')
        if self.protocol == 'ors' and u.hostname == 'api.heigit.org':
            if not self.authentication_required or self.authentication_header.lower() != 'authorization':
                raise ValueError('hosted ORS requires Authorization')
        if self.protocol == 'photon':
            if not all(self.capability_flags.get(c) and c in p.allowed_capabilities
                       for c in ('search', 'reverse')):
                raise ValueError('Photon trial requires declared search and reverse capabilities')
        elif p.max_area_m2 is None or p.max_geometry_vertices is None or p.max_items is None:
            raise ValueError('trial requires geometry and item limits')
        return self

    @model_validator(mode='wrap')
    @classmethod
    def redact_invalid_input(cls, value, handler):
        # Wrap every validator (including validate_trial). str(exc) alone hides
        # too little: structured errors otherwise retain rejected credentials.
        try:
            return handler(value)
        except ValidationError as exc:
            errors = []
            for error in exc.errors(include_input=False, include_context=False):
                field = error['loc'][0] if error['loc'] else None
                errors.append({'type': 'value_error',
                               'loc': (field,) if field in cls.model_fields else (),
                               'input': None,
                               'ctx': {'error': ValueError('invalid trial configuration')}})
            raise ValidationError.from_exception_data(cls.__name__, errors,
                                                     hide_input=True) from None

    @classmethod
    def public(cls, protocol: Protocol, *, application_name: str, contact_url: str) -> TrialSettings:
        """Select one public instance; selection/construction never calls it.

        References are policy evidence pointers, not a live quality/rights grant.
        Check current operator terms before opting in to actual use.
        """
        if protocol not in ('photon', 'overpass', 'ors'):
            raise ValueError('unsupported trial protocol')
        if (not application_name.strip() or any(c in application_name for c in '\r\n') or
                not contact_url.startswith('https://') or not urlsplit(contact_url).hostname or
                urlsplit(contact_url).username or urlsplit(contact_url).password):
            raise ValueError('application name and public HTTPS contact URL required')
        endpoint, instance_id, terms, capabilities = {
            'photon': ('https://photon.komoot.io', 'photon-komoot-demo',
                       'https://github.com/komoot/photon', {'search': True, 'reverse': True}),
            'overpass': ('https://overpass.private.coffee', 'overpass-private-coffee',
                         'https://overpass.private.coffee/', {'places': True}),
            'ors': ('https://api.heigit.org/openrouteservice', 'ors-heigit-standard',
                    'https://api.heigit.org/',
                    {'route': True, 'travelmatrix': True, 'catchment': True, 'catchment_inbound': False}),
        }[protocol]
        enabled = tuple(key for key, enabled in capabilities.items() if enabled)
        return cls(protocol=protocol, instance_id=instance_id, endpoint=endpoint,
                   authentication_required=protocol == 'ors', capability_flags=capabilities,
                   policy=UsagePolicy(allowed_endpoints=(origin(endpoint),), allowed_capabilities=enabled,
                       max_calls_per_run=5, max_concurrency=1, deadline_s=10.0,
                       max_response_bytes=1_000_000, max_area_m2=10_000_000.0,
                       max_geometry_vertices=1000, max_items=100,
                       cost_ceiling=Decimal(0), currency='EUR', pricing_ref=terms,
                       cache_policy='disabled'),
                   terms_ref=terms, rights_ref='https://www.openstreetmap.org/copyright',
                   attribution='© OpenStreetMap contributors' + ('; openrouteservice / HeiGIT' if protocol == 'ors' else ''),
                   user_agent=f'{application_name} (+{contact_url})')


class _RunBudget:
    """Enforce this gateway's run cap in addition to the injected shared budget."""
    def __init__(self, shared: Budget, max_calls: int):
        self.shared, self.max_calls, self.calls = shared, max_calls, 0
        self._lock = asyncio.Lock()

    async def reserve(self, provider_id: str, calls: int, estimated_cost: Decimal) -> bool:
        async with self._lock:
            if estimated_cost != 0 or self.calls + calls > self.max_calls:
                return False
            if not await self.shared.reserve(provider_id, calls, estimated_cost):
                return False
            self.calls += calls
            return True

    async def record(self, provider_id: str, actual_cost: Decimal) -> None:
        await self.shared.record(provider_id, actual_cost)


def build_trial_provider(settings: TrialSettings, *, budget: Budget,
                         headers: dict[str, str] | None = None) -> LocationResolver | PlaceProvider | RoutingProvider:
    """Build one existing adapter with a dedicated gateway; never perform I/O.

    Missing required authentication leaves the adapter unconfigured. A new
    gateway starts a new local run cap; the injected Budget must retain daily
    usage across constructions, retries, processes and restarts (FF-02).
    """
    # Revalidate rather than trusting model_construct or the factory caller.
    settings = TrialSettings.model_validate(settings.model_dump())
    if settings.protocol == 'ors':
        u = urlsplit(settings.endpoint)
        if u.hostname != 'api.heigit.org' or u.path.rstrip('/') not in ('', '/openrouteservice'):
            raise ValueError('ORS instance switching requires FF-03')
    runtime_headers = dict(headers or {})
    if (any(not isinstance(k, str) or not isinstance(v, str) or
            not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", k) or
            any(ord(c) < 32 or ord(c) > 126 for c in v)
            for k, v in runtime_headers.items()) or
            len({k.lower() for k in runtime_headers}) != len(runtime_headers)):
        raise ValueError('invalid runtime headers')
    auth = next((v.strip() for k, v in runtime_headers.items()
                 if k.lower() == settings.authentication_header.lower()), '')
    # Drop caller UA spelling first to avoid duplicate case-insensitive headers.
    runtime_headers = {k: v for k, v in runtime_headers.items() if k.lower() != 'user-agent'}
    runtime_headers['User-Agent'] = settings.user_agent
    configured = not settings.authentication_required or bool(auth)
    cfg = ProviderConfig(id=settings.instance_id, endpoint=settings.endpoint if configured else None,
                         capability_flags=settings.capability_flags, rights_ref=settings.rights_ref,
                         credential_handle='runtime-header' if auth else None)
    gateway = HttpGateway({cfg.id: cfg}, settings.policy,
                          _RunBudget(budget, settings.policy.max_calls_per_run),
                          headers=runtime_headers, cost_per_call=settings.cost_per_call)
    if settings.protocol == 'photon':
        return PhotonResolver(gateway, provider_id=cfg.id, capabilities=settings.photon_capabilities)
    if settings.protocol == 'overpass':
        return OverpassPlaceProvider(gateway, provider_id=cfg.id)
    return OrsRoutingProvider(gateway, provider_id=cfg.id)
