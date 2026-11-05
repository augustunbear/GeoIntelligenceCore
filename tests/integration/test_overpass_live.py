"""Live Overpass coverage requires a frozen, approved P13 activation record."""
import pytest


@pytest.mark.skip(reason="P13 approved instance, use/retention rights, quota and labeled region absent")
def test_overpass_live_coverage_gate():
    raise AssertionError("A live gate must measure coverage, not merely HTTP status")
