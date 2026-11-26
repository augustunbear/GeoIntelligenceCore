"""Manual location confirmation request and operation context."""
import re
from urllib.parse import unquote, urlsplit

from pydantic import Field, model_validator
from typing import Literal

from .common import FrozenModel
from .location import Address, Candidate, Confirmation, Entrance, Point
from .evidence import Evidence


class ConfirmRequest(FrozenModel):
    candidate: Candidate | None = None
    point: Point | None = None
    address: Address | None = None
    entrances: tuple[Entrance, ...] = Field(default_factory=list)
    confirmation: Confirmation
    evidence: tuple[Evidence, ...] = Field(min_length=1)
    location_id: str | None = None
    request_id: str | None = None

    @model_validator(mode="after")
    def selected_source(self):
        if (self.candidate is None) == (self.point is None):
            raise ValueError("select exactly one candidate or manual point")
        expected = "candidate" if self.candidate else "manual"
        if self.confirmation.method != expected:
            raise ValueError("confirmation method must match selected source")
        if self.location_id == "" or self.request_id == "":
            raise ValueError("IDs must be nonempty")
        ids = [e.id for e in self.evidence]
        if len(set(ids)) != len(ids) or not set(self.confirmation.evidence_ids).issubset(ids):
            raise ValueError("confirmation evidence must be present and unique")
        return self


class RequestContext(FrozenModel):
    request_id: str = Field(min_length=1)
    location_versions: dict[str, int] = Field(default_factory=dict)
    effective_conditions: dict[str, str] = Field(default_factory=dict)
    profile_ref: str | None = None
    template_ref: str | None = None
    method_version: str = "manual-v1"
    scope_token: str | None = None


_SERVING_PROVENANCE_KEYS = frozenset(('provider_instance', 'provider_endpoint', 'provider_http_method'))


def _serving_provenance(context: RequestContext) -> dict[str, str]:
    """Keep public metadata from a provider context without trusting other fields."""
    conditions = context.effective_conditions
    fields = {}
    instance = conditions.get('provider_instance', '')
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', instance):
        fields['provider_instance'] = instance
    method = conditions.get('provider_http_method')
    if method in ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
        fields['provider_http_method'] = method
    endpoint = conditions.get('provider_endpoint')
    if endpoint:
        try:
            url = urlsplit(endpoint)
            decoded = unquote(endpoint)
            if (url.scheme == 'https' and url.hostname and not url.hostname.endswith('.')
                    and url.username is None and url.password is None and url.port in (None, 443)
                    and '?' not in endpoint and '#' not in endpoint and '\\' not in decoded
                    and not any(char.isspace() or ord(char) < 32 for char in endpoint)
                    and not any(ord(char) < 32 or ord(char) == 127 for char in decoded)
                    and not any(part in ('.', '..') for part in unquote(url.path).split('/'))):
                fields['provider_endpoint'] = endpoint
        except ValueError:
            pass
    return fields


class SearchRequest(FrozenModel):
    text: str = Field(min_length=1)
    language: Literal['de', 'zh-CN', 'en'] = 'de'
    country_codes: tuple[str, ...] = ()
    bbox: tuple[float, float, float, float] | None = None
    near: Point | None = None
    limit: int = Field(default=10, ge=1)


class ReverseRequest(FrozenModel):
    point: Point
    language: Literal['de', 'zh-CN', 'en'] = 'de'
