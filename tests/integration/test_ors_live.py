"""Live ORS activation requires verified terms, quota, credentials and separate opt-in."""
import pytest

pytestmark = pytest.mark.skip(reason='ORS production rights/quota and endpoint activation not verified')


def test_live_activation_pending():
    pass
