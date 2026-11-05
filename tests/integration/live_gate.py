"""Conservative opt-in check; never prints credentials or sample contents."""
import json
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path

import pytest


_REQUIRED = (
    "approved_origin", "instance_owner", "instance_version", "terms_ref",
    "rights_ref", "quota_ref", "pricing_ref", "purpose", "samples_ref",
    "thresholds_ref", "currency",
)


def valid_number(value, *, zero_allowed=False):
    if isinstance(value, bool):
        return False
    try:
        number = Decimal(str(value))
        return number.is_finite() and (number >= 0 if zero_allowed else number > 0)
    except (InvalidOperation, ValueError):
        return False


def require_live_activation(provider):
    if os.environ.get("GEO_LIVE_TESTS") != "1":
        pytest.skip("live opt-in absent; provider quality unverified")
    path = os.environ.get("GEO_LIVE_ACTIVATION_FILE")
    if not path:
        pytest.skip("approved activation record absent; provider quality unverified")
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))[provider]
    except (OSError, ValueError, KeyError, TypeError):
        pytest.skip("approved provider record unreadable; provider quality unverified")
    if not isinstance(record, dict):
        pytest.skip("approved provider record unreadable; provider quality unverified")
    references_valid = all(isinstance(record.get(key), str) and record[key].strip()
                           for key in _REQUIRED)
    limits_valid = all(type(record.get(key)) is int and record[key] > 0
                       for key in ("max_calls", "max_concurrency", "max_response_bytes"))
    if (record.get("approved") is not True or not references_valid or not limits_valid
            or not valid_number(record.get("deadline_s"))
            or not valid_number(record.get("cost_ceiling"), zero_allowed=True)):
        pytest.skip("provider approval, rights, quota, pricing, samples or budget missing")
    credential_env = record.get("credential_env")
    authentication_required = record.get("authentication_required", provider == "ors")
    if type(authentication_required) is not bool or (authentication_required and credential_env is None):
        pytest.skip("required provider authentication configuration absent")
    if credential_env is not None and (
            not isinstance(credential_env, str) or not credential_env.strip()
            or not os.environ.get(credential_env)):
        pytest.skip("provider credential absent; provider quality unverified")
    return record
