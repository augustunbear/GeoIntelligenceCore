"""A downstream caller imports only the documented public facade."""
import ast
import os
import subprocess
import sys
from pathlib import Path

from geo_intelligence_core import AnalyzeRequest, ConfirmRequest, Point, Result, Status


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/python/offline_analysis.py'


def test_consumer_offline_roundtrip():
    tree = ast.parse(EXAMPLE.read_text(encoding='utf-8'))
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert all(node.module == 'geo_intelligence_core' for node in imports
               if node.module and node.module.startswith('geo_intelligence_core'))
    env = {key: value for key, value in os.environ.items()
           if not any(secret in key.upper() for secret in ('TOKEN', 'KEY', 'SECRET', 'PASSWORD'))}
    env['GEO_CORE_DISABLE_NETWORK'] = '1'
    completed = subprocess.run([sys.executable, str(EXAMPLE)], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert 'surroundings: partial' in completed.stdout
    assert 'venue-discovery: ok' in completed.stdout
    assert 'location-comparison:' in completed.stdout
    assert 'export roundtrip: ok' in completed.stdout


def test_public_models_and_status_stable():
    assert Point(longitude=11, latitude=49).model_dump() == {'longitude': 11, 'latitude': 49}
    assert Status.disabled.value == 'disabled'
    assert AnalyzeRequest.model_fields['topics'].is_required()
    assert ConfirmRequest.model_fields['confirmation'].is_required()
    assert Result.model_fields['schema_version'].default == '1.0'
