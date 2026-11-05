"""Permission and resource policy shape; enforcement belongs to later tasks."""
from decimal import Decimal
from pydantic import Field, StrictInt, StrictFloat
from .common import FrozenModel


class UsagePolicy(FrozenModel):
    allowed_endpoints: tuple[str, ...] = Field(default_factory=list)
    allowed_capabilities: tuple[str, ...] = Field(default_factory=list)
    max_calls_per_run: StrictInt = Field(default=0, ge=0)
    max_concurrency: StrictInt = Field(default=1, ge=1)
    max_area_m2: StrictFloat | None = Field(default=None, gt=0)
    max_geometry_vertices: StrictInt | None = Field(default=None, ge=3)
    max_items: StrictInt | None = Field(default=None, ge=1)
    deadline_s: StrictFloat | None = Field(default=None, gt=0)
    max_response_bytes: StrictInt | None = Field(default=None, ge=1)
    cost_ceiling: Decimal | None = None
    currency: str | None = None
    pricing_ref: str | None = None
    period_limits: dict[str, int] = Field(default_factory=dict)
    cache_policy: str | None = None


class ProviderConfig(FrozenModel):
    id: str
    endpoint: str | None = None
    capability_flags: dict[str, bool] = Field(default_factory=dict)
    rights_ref: str | None = None
    credential_handle: str | None = None
