"""Opt-in ors measurement; approved labels, thresholds and persistent quotas required."""
from .live_measurements import run_live_test

def test_ors_live_quality_gate():
    run_live_test("ors")
