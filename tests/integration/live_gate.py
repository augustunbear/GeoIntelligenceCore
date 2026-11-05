"""Conservative opt-in check; never prints credentials or sample contents."""
import json
import os
from pathlib import Path

import pytest


_REQUIRED = (
    "approved_origin", "instance_owner", "instance_version", "terms_ref",
    "rights_ref", "quota_ref", "pricing_ref", "purpose", "samples_ref",
    "thresholds_ref", "max_calls", "max_concurrency", "deadline_s",
    "max_response_bytes", "cost_ceiling", "currency", "credential_env",
)


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
    if record.get("approved") is not True or any(not record.get(key) for key in _REQUIRED):
        pytest.skip("provider approval, rights, quota, pricing, samples or budget missing")
    if not os.environ.get(record["credential_env"]):
        pytest.skip("provider credential absent; provider quality unverified")
    return record
