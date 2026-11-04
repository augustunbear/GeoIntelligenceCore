import json
import subprocess
import sys

from geo_intelligence_core.location import confirm_location
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.location import Location, Point
from geo_intelligence_core.models.requests import ConfirmRequest


def test_schema_round_trip(manual_request):
    request = ConfirmRequest.model_validate_json(manual_request.model_dump_json())
    result = confirm_location(request)
    restored = Result[Location].model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.schema_version == "1.0" and restored.context.request_id
    assert Result[Location].model_json_schema()["properties"]["status"]


def test_import_offline():
    script = '''
import sys, socket
socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
sys.modules["shapely"] = None
sys.modules["pyproj"] = None
sys.modules["httpx"] = None
import geo_intelligence_core
from geo_intelligence_core.location import confirm_location
from datetime import datetime, timezone
r = confirm_location({"point": {"longitude": 11, "latitude": 49}, "confirmation": {"method": "manual", "at": datetime.now(timezone.utc).isoformat(), "evidence_ids": ["e1"]}, "evidence": [{"id":"e1", "source_id":"user", "source_type":"manual", "source_ref":"synthetic", "retrieved_at":datetime.now(timezone.utc).isoformat(), "method_version":"manual-v1", "rights":{}, "quality":{}}]})
assert r.status == "ok" and r.data.version == 1
'''
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "src"})
    assert completed.returncode == 0, completed.stderr


def test_nested_collections_cannot_change_prior_result(manual_request):
    result = confirm_location(manual_request)
    original = result.model_dump_json()
    import pytest
    from pydantic import ValidationError
    with pytest.raises((AttributeError, TypeError)):
        result.data.entrances.append("later")
    with pytest.raises((AttributeError, TypeError)):
        result.data.confirmation.evidence_ids.append("later")
    with pytest.raises((AttributeError, TypeError)):
        result.evidence.append("later")
    with pytest.raises((AttributeError, TypeError)):
        result.context.location_versions[result.data.id] = 999
    with pytest.raises(ValidationError):
        result.evidence[0].rights.use = "allowed"
    assert result.model_dump_json() == original


def test_model_copy_keeps_nested_collections_immutable(manual_request):
    original = confirm_location(manual_request)
    copied = original.model_copy(update={"issues": [original.issues[0]] if original.issues else []})
    import pytest
    with pytest.raises((AttributeError, TypeError)):
        copied.issues.append("later")
    assert copied == original
