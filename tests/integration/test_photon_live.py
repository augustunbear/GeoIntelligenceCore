"""Photon live activation requires a frozen sample and explicit approval."""
import pytest
from .live_gate import require_live_activation


def test_photon_live_quality_gate():
    record = require_live_activation("photon")
    pytest.fail("approved Photon record detected; implement and independently review labeled German candidate, ambiguity and failure measurements before activation")
