"""ORS live activation requires verified current terms, quota and direction cases."""
import pytest
from .live_gate import require_live_activation


def test_ors_live_quality_gate():
    record = require_live_activation("ors")
    pytest.fail("approved ORS record detected; implement and independently review route, matrix and inbound/outbound isochrone measurements before activation")
