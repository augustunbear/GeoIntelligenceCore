"""Build source artifacts and exercise isolated Python 3.12 consumers."""
import json
import os
import re
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BAD_NAMES = re.compile(r'(^|/)(\.env(?:\..*)?|.*\.(?:jar|pem|key|p12)|credentials[^/]*|(?:customer|client|case)[-_][^/]*\.(?:csv|json|xlsx))$', re.I)
BAD_CONTENT = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|'
                         rb'sk-[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{30,}|'
                         rb'github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|'
                         rb'Bearer\s+[A-Za-z0-9._~-]{20,}', re.I)


def test_archive_scan_positive_controls():
    for filename in ('src/.env.production', 'keys/private.pem', 'fixtures/customer-sites.csv',
                     'fixtures/client_data.json', 'data/case-records.xlsx', 'service.jar'):
        assert BAD_NAMES.search(filename), filename
    for value in (b'-----BEGIN ' + b'PRIVATE KEY', b'sk' + b'-' + b'A' * 32,
                  b'gh' + b'p_' + b'B' * 36, b'github_' + b'pat_' + b'C' * 35,
                  b'AK' + b'IA' + b'D' * 16, b'Bearer' + b' ' + b'E' * 30):
        assert BAD_CONTENT.search(value), value


@pytest.fixture(scope='module')
def distributions(tmp_path_factory):
    output = tmp_path_factory.mktemp('dist')
    built = subprocess.run([sys.executable, '-m', 'build', '--no-isolation',
                            '--outdir', str(output), str(ROOT)], capture_output=True,
                           text=True, timeout=120)
    assert built.returncode == 0, built.stderr
    wheels = list(output.glob('*.whl'))
    sdists = list(output.glob('*.tar.gz'))
    assert len(wheels) == len(sdists) == 1
    return wheels[0], sdists[0]


@pytest.mark.parametrize('extra', ['', '[geometry]', '[providers]', '[geometry,providers]', '[temporal]', '[geometry,providers,temporal]'])
def test_clean_install(distributions, extra, tmp_path):
    assert sys.version_info[:2] == (3, 12)
    environment = tmp_path / 'venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / 'bin/python'
    wheel, _ = distributions
    installed = subprocess.run([str(python), '-m', 'pip', 'install', '-q',
                                f'{wheel}{extra}'], capture_output=True,
                               text=True, timeout=120)
    assert installed.returncode == 0, installed.stderr
    env = {key: value for key, value in os.environ.items()
           if not any(secret in key.upper() for secret in ('TOKEN', 'KEY', 'SECRET', 'PASSWORD'))
           and key not in ('PYTHONPATH', 'PYTHONHOME')}
    env['GEO_CORE_DISABLE_NETWORK'] = '1'
    result = subprocess.run([str(python), str(ROOT / 'examples/python/offline_analysis.py')],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert 'export roundtrip: ok' in result.stdout
    probe = subprocess.run([str(python), '-c',
        'import geo_intelligence_core, sys; '
        'from geo_intelligence_core import Observation, normalize_observation; '
        'assert callable(normalize_observation) and Observation.model_fields["count"].default is None; '
        'assert "pyspark" not in sys.modules and "r5py" not in sys.modules; '
        'print(geo_intelligence_core.__version__)'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == '0.1.0a1'
    if 'temporal' in extra:
        env['PYTHONTZPATH'] = ''  # Force packaged IANA fallback, including on Linux CI.
    temporal_probe = subprocess.run([str(python), '-c',
        'import socket, sys; '
        'socket.socket.connect = lambda *args: (_ for _ in ()).throw(AssertionError("network")); '
        'from datetime import datetime; '
        'from geo_intelligence_core import evaluate_opening_hours; '
        'assert "opening_hours" not in sys.modules; '
        'r = evaluate_opening_hours("24/7", at=datetime.fromisoformat("2026-11-10T12:00:00+00:00"), timezone="Europe/Berlin"); '
        f'assert r.data.state == {("open" if "temporal" in extra else "unknown")!r}'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert temporal_probe.returncode == 0, temporal_probe.stderr



def test_no_bundled_secrets(distributions):
    wheel, sdist = distributions
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert any(name.endswith('data/locales/en.json') for name in names)
        for name in names:
            assert not BAD_NAMES.search(name), name
            assert not BAD_CONTENT.search(archive.read(name)), name
    with tarfile.open(sdist, 'r:gz') as archive:
        for item in archive.getmembers():
            assert not BAD_NAMES.search(item.name), item.name
            if item.isfile():
                assert not BAD_CONTENT.search(archive.extractfile(item).read()), item.name


def test_sdist_clean_install(distributions, tmp_path):
    _, sdist = distributions
    environment = tmp_path / 'venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / 'bin/python'
    installed = subprocess.run([str(python), '-m', 'pip', 'install', '-q', str(sdist)],
                               capture_output=True, text=True, timeout=120)
    assert installed.returncode == 0, installed.stderr
    env = {key: value for key, value in os.environ.items()
           if not any(secret in key.upper() for secret in ('TOKEN', 'KEY', 'SECRET', 'PASSWORD'))
           and key not in ('PYTHONPATH', 'PYTHONHOME')}
    checked = subprocess.run([str(python), '-c',
        'import socket; '
        'socket.socket.connect = lambda *args: (_ for _ in ()).throw(AssertionError("network")); '
        'from geo_intelligence_core import Point, Status; '
        'assert Point(longitude=11, latitude=49).longitude == 11; '
        'assert Status.ok == "ok"'], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=10)
    assert checked.returncode == 0, checked.stderr


def test_schema_compat_saved_consumer_fixture():
    from geo_intelligence_core import Point, RequestContext, Result, Status
    fixture = ROOT / 'tests/fixtures/consumer/result-v1.json'
    expected = json.loads(fixture.read_text(encoding='utf-8'))
    context = RequestContext(request_id='synthetic', location_versions={'site': 1})
    result = Result[Point](status=Status.ok, data=Point(longitude=11, latitude=49), context=context)
    assert result.model_dump(mode='json') == expected
    assert Result[Point].model_validate(expected) == result



def test_temporal_extra_metadata(distributions):
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        name = next(name for name in archive.namelist() if name.endswith('.dist-info/METADATA'))
        metadata = archive.read(name).decode()
        assert 'Provides-Extra: temporal' in metadata
        assert 'tzdata==2026.6' in metadata
        assert 'opening-hours-py==2.1.5; extra == \'temporal\'' in metadata
