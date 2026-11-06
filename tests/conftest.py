from datetime import datetime, timezone
import os
import socket

import pytest

from geo_intelligence_core.models.evidence import Evidence, Quality, Rights
from geo_intelligence_core.models.location import Confirmation, Point


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch, request):
    live_files = {'test_photon_live.py', 'test_overpass_live.py', 'test_ors_live.py'}
    if (os.environ.get('GEO_LIVE_TESTS') == '1'
            and request.node.path.parent.name == 'integration'
            and request.node.path.name in live_files):
        return
    def blocked(*args, **kwargs):
        raise AssertionError("offline tests must not access the network")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def synthetic_evidence():
    return Evidence(id="manual-1", source_id="user", source_type="manual", source_ref="synthetic fixture", retrieved_at=datetime(2026, 11, 4, tzinfo=timezone.utc), method_version="manual-v1", rights=Rights(), quality=Quality())


@pytest.fixture
def manual_request(synthetic_evidence):
    from geo_intelligence_core.models.requests import ConfirmRequest
    return ConfirmRequest(point=Point(longitude=11, latitude=49), confirmation=Confirmation(method="manual", at=datetime(2026, 11, 4, tzinfo=timezone.utc), evidence_ids=[synthetic_evidence.id]), evidence=[synthetic_evidence])
