"""Overpass live activation requires bounded representative-region coverage."""
import pytest
from .live_gate import require_live_activation


def test_overpass_live_coverage_gate():
    record = require_live_activation("overpass")
    pytest.fail("approved Overpass record detected; implement and independently review labeled POI coverage, truncation and failure measurements before activation")
