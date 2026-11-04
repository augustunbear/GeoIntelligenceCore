"""P13 gate: live Photon checks need an approved endpoint and labeled samples."""
import pytest


@pytest.mark.skip(reason='P13 approved endpoint, terms, quota and labeled samples not supplied')
def test_photon_live_quality_gate():
    pass
