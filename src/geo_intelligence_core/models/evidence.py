"""Provenance and permissions for confirmed facts."""
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field, field_validator

from .common import FrozenModel


class Permission(StrEnum):
    allowed = "allowed"
    denied = "denied"
    unknown = "unknown"


class Rights(FrozenModel):
    use: Permission = Permission.unknown
    retain: Permission = Permission.unknown
    cache: Permission = Permission.unknown
    display: Permission = Permission.unknown
    export: Permission = Permission.unknown
    redistribute: Permission = Permission.unknown
    attribution: str | None = None
    license_url: str | None = None
    source_url: str | None = None
    checked_at: datetime | None = None
    permitted_purpose: str | None = None

    def allows(self, action: str, purpose: str) -> bool:
        """Unknown permission or mismatched purpose does not grant use."""
        if action not in ('use', 'retain', 'cache', 'display', 'export', 'redistribute'):
            raise ValueError('unknown permission')
        return getattr(self, action) == Permission.allowed and bool(purpose) and self.permitted_purpose == purpose

    @field_validator("checked_at")
    @classmethod
    def utc_checked_at(cls, value):
        return utc(value) if value else None


class Quality(FrozenModel):
    precision: str | None = None
    coverage: str | None = None
    freshness: str | None = None
    source_reliability: str | None = None
    uncertainty: str | None = None
    verification: str | None = None


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone offset")
    return value.astimezone(timezone.utc)


class Evidence(FrozenModel):
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    retrieved_at: datetime
    reference_period: str | None = None
    valid_period: str | None = None
    method_version: str = Field(min_length=1)
    rights: Rights
    quality: Quality

    @field_validator("retrieved_at")
    @classmethod
    def utc_retrieved_at(cls, value):
        return utc(value)


