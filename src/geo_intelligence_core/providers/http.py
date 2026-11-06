"""Bounded HTTPS gateway for configured provider queries."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import inspect
import ipaddress
import json
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
import httpx
from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.policy import ProviderConfig, UsagePolicy
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.ports import Budget
from .budget import BudgetUnavailable

class UnsafeEndpoint(Exception):
    pass

class ResponseTooLarge(Exception):
    pass

def origin(url):
    u = urlsplit(url)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment or u.port not in (None, 443) or u.hostname.endswith('.'):
        raise UnsafeEndpoint()
    return f'https://{u.hostname.lower()}'

class HttpGateway:
    def __init__(self, providers: dict[str, ProviderConfig], policy: UsagePolicy, budget: Budget, *,
                 clock=time.monotonic, transport: httpx.AsyncBaseTransport | None = None,
                 resolver=None, allowed_redirect_hosts: tuple[str, ...] = (),
                 cost_per_call: Decimal | None = None, headers: dict[str, str] | None = None):
        self.providers, self.policy, self.budget = providers, policy, budget
        self.clock, self.transport, self.resolver = clock, transport, resolver
        self.redirect_hosts = frozenset(allowed_redirect_hosts)
        self.cost_per_call, self.headers = cost_per_call, headers or {}
        self._semaphore = asyncio.Semaphore(policy.max_concurrency)

    async def _validate_url(self, url, *, redirect=False):
        host = urlsplit(url).hostname
        if origin(url) not in self.policy.allowed_endpoints or (redirect and host not in self.redirect_hosts):
            raise UnsafeEndpoint()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise UnsafeEndpoint()
        if self.resolver is None:
            records = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            addresses = [r[4][0] for r in records]
        else:
            addresses = self.resolver(host)
            if inspect.isawaitable(addresses):
                addresses = await addresses
        if not addresses:
            raise UnsafeEndpoint()
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise UnsafeEndpoint() from exc
            if not ip.is_global:
                raise UnsafeEndpoint()
        return addresses[0]

    @staticmethod
    def _delay(value):
        if value is None:
            return 0.0
        try:
            delay = float(value)
            return min(86400.0, max(0.0, delay)) if delay == delay else None
        except ValueError:
            try:
                from email.utils import parsedate_to_datetime
                return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return None

    async def request(self, provider_id: str, method: str, path: str,
                      params: dict, context: RequestContext) -> Result[dict]:
        """Bound the entire operation, including DNS, queue wait and retries."""
        deadline = self.policy.deadline_s
        try:
            if deadline is None:
                return await self._request_impl(provider_id, method, path, params, context)
            return await asyncio.wait_for(self._request_impl(provider_id, method, path, params, context),
                                          timeout=deadline)
        except TimeoutError:
            return Result[dict](status=Status.unavailable, data=None,
                                issues=[Issue(code='deadline', message_key='provider.deadline')],
                                context=context)

    async def _request_impl(self, provider_id: str, method: str, path: str,
                            params: dict, context: RequestContext) -> Result[dict]:
        def fail(status, code):
            return Result[dict](status=status, data=None,
                                issues=[Issue(code=code, message_key=f'provider.{code}')], context=context)
        cfg = self.providers.get(provider_id)
        if cfg is None or cfg.id != provider_id or not cfg.endpoint:
            return fail(Status.unconfigured, 'unconfigured')
        p = self.policy
        if (p.max_calls_per_run < 1 or p.deadline_s is None or p.max_response_bytes is None or
                p.cost_ceiling is None or not p.currency or not p.pricing_ref or self.cost_per_call is None):
            return fail(Status.unconfigured, 'missing_hard_limit')
        if method not in ('GET', 'POST') or not isinstance(params, dict):
            return fail(Status.invalid_input, 'method_or_params')
        if method == 'POST':
            try:
                def contains_scope(value):
                    return (isinstance(value, dict) and
                            ('scope_token' in value or any(contains_scope(v) for v in value.values()))) or (
                            isinstance(value, (tuple, list)) and any(contains_scope(v) for v in value))
                if contains_scope(params):
                    return fail(Status.invalid_input, 'unsafe_path_or_params')
                body = json.dumps(params, allow_nan=False)
                if len(body.encode('utf-8')) > p.max_response_bytes:
                    return fail(Status.invalid_input, 'request_too_large')
            except (TypeError, ValueError, OverflowError):
                return fail(Status.invalid_input, 'unsafe_path_or_params')
        if (not path.startswith('/') or path.startswith('//') or '\\' in path or
                '?' in path or '#' in path or any(ord(c) < 32 for c in path) or
                (method == 'GET' and 'scope_token' in params) or (method == 'GET' and any(not isinstance(k, str) or
                                               not isinstance(v, (str, int, float, bool)) or
                                               (isinstance(v, float) and not __import__('math').isfinite(v))
                                               for k, v in params.items()))):
            return fail(Status.invalid_input, 'unsafe_path_or_params')
        try:
            base = cfg.endpoint.rstrip('/') + '/'
            url = urljoin(base, path.lstrip('/'))
            if origin(base) not in p.allowed_endpoints or urlsplit(url).hostname != urlsplit(base).hostname:
                raise UnsafeEndpoint()
            await self._validate_url(url)
            cost = Decimal(self.cost_per_call)
            if cost < 0 or not cost.is_finite():
                return fail(Status.unconfigured, 'unknown_cost')
        except (ValueError, TypeError, OSError, UnsafeEndpoint):
            return fail(Status.unconfigured, 'unsafe_endpoint')
        end = self.clock() + p.deadline_s
        hops = 0
        async with self._semaphore:
            async with httpx.AsyncClient(transport=self.transport, follow_redirects=False,
                                         trust_env=False, timeout=httpx.Timeout(min(5.0, p.deadline_s))) as client:
                while True:
                    remaining = end - self.clock()
                    if remaining <= 0:
                        return fail(Status.unavailable, 'deadline')
                    try:
                        pinned_ip = await self._validate_url(url, redirect=hops > 0)
                    except (OSError, UnsafeEndpoint):
                        return fail(Status.unavailable, 'unsafe_redirect')
                    try:
                        permitted = await self.budget.reserve(provider_id, 1, cost)
                    except BudgetUnavailable:
                        return fail(Status.unavailable, 'budget_unavailable')
                    if not permitted:
                        return fail(Status.rate_limited, 'budget_exhausted')
                    try:
                        async with asyncio.timeout(remaining):
                            parsed = urlsplit(url)
                            netloc = f'[{pinned_ip}]' if ':' in pinned_ip else pinned_ip
                            pinned = urlunsplit(('https', netloc, parsed.path, parsed.query, ''))
                            outbound_headers = {**self.headers, 'Host': parsed.hostname}
                            request = client.build_request(method, pinned,
                                                           params=params if method == 'GET' and hops == 0 else None,
                                                           content=body if method == 'POST' else None,
                                                           headers=outbound_headers)
                            if method == 'POST':
                                request.headers['Content-Type'] = 'application/json'
                            request.extensions['sni_hostname'] = parsed.hostname
                            response = await client.send(request, stream=True)
                            try:
                                if response.status_code in (301, 302, 303, 307, 308):
                                    if method == 'POST':
                                        return fail(Status.unavailable, 'redirect_rejected')
                                    location = response.headers.get('Location')
                                    if not location or hops >= 3:
                                        return fail(Status.unavailable, 'redirect_rejected')
                                    target = urljoin(url, location)
                                    try:
                                        if origin(target) != origin(url):
                                            return fail(Status.unavailable, 'cross_origin_redirect')
                                    except UnsafeEndpoint:
                                        return fail(Status.unavailable, 'unsafe_redirect')
                                    try:
                                        await self._validate_url(target, redirect=True)
                                    except (OSError, UnsafeEndpoint):
                                        return fail(Status.unavailable, 'unsafe_redirect')
                                    url, hops = target, hops + 1
                                    continue
                                if response.status_code in (429, 503):
                                    delay = self._delay(response.headers.get('Retry-After'))
                                    status = Status.rate_limited if response.status_code == 429 else Status.unavailable
                                    if delay is None or delay >= end - self.clock():
                                        return fail(status, 'retry_deadline')
                                elif response.status_code in (401, 403):
                                    return fail(Status.unconfigured, 'provider_authorization')
                                elif response.status_code >= 400:
                                    return fail(Status.unavailable, 'upstream_failure')
                                else:
                                    chunks = bytearray()
                                    async for chunk in response.aiter_bytes():
                                        if len(chunks) + len(chunk) > p.max_response_bytes:
                                            raise ResponseTooLarge()
                                        chunks.extend(chunk)
                                    data = json.loads(chunks)
                                    if not isinstance(data, dict):
                                        return fail(Status.unavailable, 'invalid_response')
                                    return Result[dict](status=Status.ok, data=data, context=context)
                            finally:
                                await response.aclose()
                        if delay:
                            await asyncio.sleep(delay)
                    except (ResponseTooLarge, ValueError, json.JSONDecodeError):
                        return fail(Status.unavailable, 'invalid_response')
                    except (httpx.HTTPError, TimeoutError, OSError):
                        return fail(Status.unavailable, 'network_failure')
