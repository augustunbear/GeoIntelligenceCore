"""Bounded, label-driven provider measurements; no activation at import time.

The SQLite ledger/OS source lock is a same-host test harness, not the consumer's
distributed limiter. Its path must persist between batches and invocations.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
from importlib.metadata import version, PackageNotFoundError
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import time
import tracemalloc
import uuid

from geo_intelligence_core import __version__
from geo_intelligence_core.provenance import package_fingerprint
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.geometry import distance_m
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.requests import RequestContext, SearchRequest, ReverseRequest
from geo_intelligence_core.models.places import PlaceQuery
from geo_intelligence_core.models.spatial import RouteRequest, MatrixRequest, CatchmentRequest
from geo_intelligence_core.providers.budget import BudgetUnavailable
from geo_intelligence_core.providers.trial import TrialSettings, build_trial_provider


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _range(value):
    return isinstance(value, list) and len(value) == 2 and all(_number(v) for v in value) and 0 <= value[0] <= value[1]


def _valid(case):
    if not isinstance(case, dict) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', str(case.get('id', ''))):
        return False
    e, op = case.get('expect'), case.get('operation')
    if not isinstance(e, dict):
        return False
    if op == 'matrix':
        try:
            request = MatrixRequest.model_validate(case.get('request'))
        except (ValueError, TypeError):
            return False
        keys = {f'{o}>{d}' for o in request.origins for d in request.destinations}
        if (not keys or len(keys) != len(request.origins) * len(request.destinations)
                or not isinstance(e.get('cells'), dict) or set(e['cells']) != keys):
            return False
    if e.get('status') == 'no_results':
        return op in ('search', 'reverse', 'places') and set(e) == {'status'}
    if e.get('status') == 'unavailable':
        if op == 'route':
            return e == {'status': 'unavailable', 'issue_code': 'no_route'}
        return (op == 'matrix' and set(e) == {'status', 'issue_code', 'cells'}
                and e['issue_code'] == 'no_route_cells' and isinstance(e['cells'], dict)
                and bool(e['cells']) and all(isinstance(k, str) and v is None for k, v in e['cells'].items()))
    allowed = {
        'search': {'status', 'candidate_ids', 'candidate_points', 'max_error_m', 'first_id', 'precisions', 'min_candidates', 'max_candidates'},
        'reverse': {'status', 'candidate_ids', 'candidate_points', 'max_error_m', 'first_id', 'precisions', 'min_candidates', 'max_candidates'},
        'places': {'status', 'source_keys', 'min_precision', 'min_recall'},
        'route': {'status', 'distance_m', 'duration_s'},
        'matrix': {'status', 'cells'},
        'catchments': {'status', 'durations_s', 'direction', 'area_m2'},
    }
    if e.get('status') != 'ok' or op not in allowed or set(e) - allowed[op]:
        return False
    if op in ('search', 'reverse'):
        ids, points, precisions = e.get('candidate_ids'), e.get('candidate_points'), e.get('precisions')
        return (isinstance(ids, list) and bool(ids) and isinstance(points, dict) and isinstance(precisions, dict)
                and _number(e.get('max_error_m')) and e['max_error_m'] > 0
                and type(e.get('min_candidates')) is int and type(e.get('max_candidates')) is int
                and 0 < e['min_candidates'] <= e['max_candidates'] <= 20
                and all(isinstance(v, str) and v in points and isinstance(points[v], list)
                        and len(points[v]) == 2 and all(_number(n) for n in points[v])
                        and -180 <= points[v][0] <= 180 and -90 <= points[v][1] <= 90
                        and isinstance(precisions.get(v), list) and bool(precisions[v])
                        and all(k in ('house','street','locality','unknown') for k in precisions[v]) for v in ids))
    if op == 'places':
        return (isinstance(e.get('source_keys'), list) and bool(e['source_keys'])
                and all(isinstance(v, str) for v in e['source_keys'])
                and all(_number(e.get(k)) and 0 < e[k] <= 1 for k in ('min_precision', 'min_recall')))
    if op == 'route':
        return _range(e.get('distance_m')) and _range(e.get('duration_s'))
    if op == 'matrix':
        return isinstance(e.get('cells'), dict) and bool(e['cells']) and all(isinstance(k, str) and _range(v) for k, v in e['cells'].items())
    return (isinstance(e.get('durations_s'), list) and bool(e['durations_s'])
            and all(type(v) is int and v > 0 for v in e['durations_s'])
            and e.get('direction') in ('inbound', 'outbound') and _range(e.get('area_m2')))


def _matches(case, result):
    e, op = case['expect'], case['operation']
    if str(result.status) != e['status'] or result.status == Status.partial:
        return False
    if op == 'matrix':
        from geo_intelligence_core.models.spatial import TravelMatrix
        if not _valid(case) or not isinstance(result.data, TravelMatrix):
            return False
        cells = {f'{c.origin_id}>{c.destination_id}': c for c in result.data.cells}
        if len(cells) != len(result.data.cells) or set(cells) != set(e['cells']):
            return False
    if e['status'] == 'no_results':
        if op in ('search', 'reverse'):
            return isinstance(result.data, (tuple,list)) and not result.data
        from geo_intelligence_core.models.places import PlaceSet
        return isinstance(result.data, PlaceSet) and not result.data.places and result.data.unique_count == 0
    if e['status'] == 'unavailable':
        if e['issue_code'] not in {issue.code for issue in result.issues}:
            return False
        if op == 'route':
            return result.data is None
        from geo_intelligence_core.models.spatial import TravelMatrix
        if not isinstance(result.data, TravelMatrix):
            return False
        cells = {f'{c.origin_id}>{c.destination_id}': c for c in result.data.cells}
        return all(k in cells and cells[k].duration_s is None and cells[k].status == Status.unavailable for k in e['cells'])
    data = result.data
    if data is None:
        return False
    if op in ('search', 'reverse'):
        ids = [c.id for c in data]
        by_id = {c.id: c for c in data}
        return (len(ids) == len(by_id) and e['min_candidates'] <= len(ids) <= e['max_candidates']
                and all(v in ids and by_id[v].precision in e['precisions'][v] and distance_m(by_id[v].point, Point(longitude=e['candidate_points'][v][0],
                    latitude=e['candidate_points'][v][1])) <= e['max_error_m'] for v in e['candidate_ids'])
                and (not e.get('first_id') or ids[0] == e['first_id']))
    if op == 'places':
        got = {f'{p.source_key.source_id}:{p.source_key.entity_type}:{p.source_key.entity_id}' for p in data.places}
        want = set(e['source_keys'])
        matched = len(got & want)
        return bool(got) and matched / len(got) >= e['min_precision'] and matched / len(want) >= e['min_recall']
    if op == 'route':
        return all(e[k][0] <= getattr(data, k) <= e[k][1] for k in ('distance_m', 'duration_s'))
    if op == 'matrix':
        return all(cells[k].status == Status.ok and cells[k].duration_s is not None
                   and bound[0] <= cells[k].duration_s <= bound[1] for k, bound in e['cells'].items())
    from pyproj import Geod
    from shapely.geometry import shape
    geod = Geod(ellps='WGS84')
    return (sorted(c.duration_s for c in data) == sorted(e['durations_s']) and
            all(c.direction == e['direction'] and e['area_m2'][0] <=
                abs(geod.geometry_area_perimeter(shape(c.region.geometry))[0]) <= e['area_m2'][1] for c in data))


async def measure_cases(cases: list[dict], *, invoke, clock) -> dict:
    """Measure frozen, labeled cases without retaining raw provider payloads."""
    if not cases or not all(_valid(c) for c in cases) or len({c['id'] for c in cases}) != len(cases):
        return {'status': 'blocked', 'reason': 'labels_or_thresholds_missing', 'cases': []}
    if not any(c['expect']['status'] == 'ok' for c in cases):
        return {'status': 'blocked', 'reason': 'positive_quality_case_required', 'cases': []}
    rows = []
    owns_trace = not tracemalloc.is_tracing()
    if owns_trace:
        tracemalloc.start()
    try:
        for case in cases:
            started = clock()
            try:
                result = await invoke(case)
                quality = _matches(case, result)
                status = str(result.status)
            except Exception:
                quality, status = False, 'invocation_failed'
            elapsed = clock() - started
            if not _number(elapsed) or elapsed < 0:
                elapsed, quality = 0.0, False
            rows.append({'id': case['id'], 'status': status, 'quality_passed': bool(quality), 'latency_s': elapsed})
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        if owns_trace:
            tracemalloc.stop()
    times = sorted(r['latency_s'] for r in rows)
    return {'status': 'passed' if all(r['quality_passed'] for r in rows) else 'failed',
            'cases': rows, 'p50_s': statistics.median(times), 'p95_s': times[math.ceil(.95 * len(times)) - 1],
            'peak_bytes': peak, 'sample_count': len(rows), 'small_sample': len(rows) < 20}


class LiveBudget:
    """Durable same-host control for test runs, stable provider domain, UTC days."""
    def __init__(self, path, provider, run_id):
        if provider not in ('photon', 'overpass', 'ors') or not run_id:
            raise ValueError('known provider and run ID required')
        self.path, self.provider, self.run_id = Path(path), provider, run_id
        self.calls = 0

    def _reserve(self, calls, cost):
        connection = None
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(fd)
            connection = sqlite3.connect(self.path, timeout=.05)
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('CREATE TABLE IF NOT EXISTS daily (provider TEXT, day TEXT, calls INT, PRIMARY KEY(provider,day))')
            connection.execute('CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, calls INT)')
            day = datetime.now(timezone.utc).date().isoformat()
            daily = connection.execute('SELECT calls FROM daily WHERE provider=? AND day=?', (self.provider, day)).fetchone()
            run = connection.execute('SELECT calls FROM runs WHERE run_id=?', (self.run_id,)).fetchone()
            d, r = daily[0] if daily else 0, run[0] if run else 0
            if cost != 0 or d + calls > 50 or r + calls > 5:
                connection.rollback()
                return False
            connection.execute('INSERT OR REPLACE INTO daily VALUES (?,?,?)', (self.provider, day, d + calls))
            connection.execute('INSERT OR REPLACE INTO runs VALUES (?,?)', (self.run_id, r + calls))
            connection.commit()
            return True
        except (sqlite3.Error, OSError):
            raise BudgetUnavailable('live quota ledger unavailable') from None
        finally:
            if connection:
                connection.close()

    async def reserve(self, provider_id, calls, estimated_cost):
        cost = Decimal(estimated_cost)
        if type(calls) is not int or calls < 1 or not cost.is_finite() or cost < 0:
            raise ValueError('invalid reservation')
        granted = await asyncio.to_thread(self._reserve, calls, cost)
        if granted:
            self.calls += calls
        return granted

    async def record(self, provider_id, actual_cost):
        if Decimal(actual_cost) != 0:
            raise BudgetUnavailable('zero-cost test policy violated')

    @asynccontextmanager
    async def source_slot(self):
        fd = None
        acquired = False
        try:
            fd = os.open(str(self.path) + '.' + self.provider + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
            while not acquired:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except BlockingIOError:
                    await asyncio.sleep(.01)
            yield
        except OSError:
            raise BudgetUnavailable('live source lock unavailable') from None
        finally:
            if fd is not None:
                if acquired:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)


def package_identity():
    """Bind imported files to this clean source checkout, independently of cwd."""
    import geo_intelligence_core as imported
    package = Path(imported.__file__).resolve().parent
    root = Path(__file__).resolve().parents[2]
    verified, commit = False, 'unverified'
    paths = ['src', 'tests/integration']
    try:
        if package == root / 'src/geo_intelligence_core':
            clean = subprocess.run(['git', '-C', str(root), 'diff', '--quiet', 'HEAD', '--', *paths], capture_output=True).returncode == 0
            untracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--others', '--', *paths], text=True)
            unexpected = [path for path in untracked.splitlines()
                          if not (Path(path).suffix == '.pyc' and '__pycache__' in Path(path).parts)]
            if clean and not unexpected:
                commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
                verified = True
    except (OSError, subprocess.CalledProcessError):
        pass
    dependencies = {}
    for name in ('pydantic', 'httpx', 'shapely', 'pyproj'):
        try: dependencies[name] = version(name)
        except PackageNotFoundError: dependencies[name] = 'not_installed'
    return {'verified': verified, 'source_commit': commit, 'code_sha256': package_fingerprint(),
            'dependencies': dependencies,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


async def run_provider(provider, record, *, budget, headers=None, transport=None, resolver=None):
    """Run each operation through its real adapter. All inputs freeze before I/O."""
    try:
        if (record.get('approved') is not True or not 0 < record['max_calls'] <= 5 or record['max_concurrency'] != 1
                or not all(isinstance(record.get(k), str) and record[k].strip()
                           for k in ('rights_ref', 'quota_ref', 'purpose', 'pricing_ref', 'currency', 'terms_ref', 'instance_owner', 'instance_version'))):
            raise ValueError('bounded approval required')
        samples_raw = Path(record['samples_ref']).read_bytes()
        thresholds_raw = Path(record['thresholds_ref']).read_bytes()
        cases, thresholds = json.loads(samples_raw), json.loads(thresholds_raw)
        if not isinstance(cases, list) or not 0 < len(cases) <= 5:
            raise ValueError('bounded sample required')
        cases = [{**c, 'expect': thresholds['cases'][c['id']]} for c in cases]
        if not all(_valid(c) for c in cases):
            raise ValueError('labeled cases required')
        if not all(_number(thresholds[k]) and thresholds[k] > 0 for k in ('max_p95_s', 'max_peak_bytes')):
            raise ValueError('performance thresholds required')
        s = (TrialSettings.model_validate(record['settings']) if record.get('settings') else
             TrialSettings.public(provider, application_name=record.get('application_name', 'GeoControlledAcceptance'),
                                  contact_url=record.get('contact_url', 'https://example.org/contact')))
        endpoint = record.get('endpoint', s.endpoint)
        s = s.model_copy(update={'endpoint': endpoint, 'instance_id': record.get('instance_id', s.instance_id),
            'authentication_required': record.get('authentication_required', s.authentication_required),
            'authentication_header': record.get('authentication_header', s.authentication_header),
            'capability_flags': record.get('capability_flags', s.capability_flags),
            'policy': s.policy.model_copy(update={'allowed_endpoints': (record['approved_origin'],),
                'max_area_m2': float(record.get('max_area_m2', s.policy.max_area_m2)),
                'max_geometry_vertices': record.get('max_geometry_vertices', s.policy.max_geometry_vertices),
                'max_calls_per_run': record['max_calls'], 'deadline_s': float(record['deadline_s']),
                'max_response_bytes': record['max_response_bytes'], 'cost_ceiling': Decimal(str(record['cost_ceiling'])),
                'pricing_ref': record['pricing_ref'], 'currency': record['currency']})})
        models = {'search': SearchRequest, 'reverse': ReverseRequest, 'places': PlaceQuery,
                  'route': RouteRequest, 'matrix': MatrixRequest, 'catchments': CatchmentRequest}
        allowed = {'photon': {'search', 'reverse'}, 'overpass': {'places'}, 'ors': {'route', 'matrix', 'catchments'}}[provider]
        if any(c['operation'] not in allowed for c in cases):
            raise ValueError('wrong provider operation')
        if {c['operation'] for c in cases if c['expect']['status'] == 'ok'} != allowed:
            raise ValueError('positive coverage of every provider operation required')
        requests = {c['id']: models[c['operation']].model_validate(c['request']) for c in cases}
        port = build_trial_provider(s, budget=budget, headers=headers)
        port.gateway.transport, port.gateway.resolver = transport, resolver
    except (OSError, ValueError, KeyError, TypeError):
        return {'status': 'blocked', 'reason': 'frozen_inputs_or_limits_missing', 'cases': [], 'calls': 0}
    class CountedBudget:
        calls = 0
        async def reserve(self, ident, calls, cost):
            allowed = await budget.reserve(ident, calls, cost)
            if allowed:
                self.calls += calls
            return allowed
        async def record(self, ident, cost):
            await budget.record(ident, cost)
    counted = CountedBudget()
    # Preserve the factory's local cap, and count actual successful reservations.
    port.gateway.budget.shared = counted
    async def invoke(case):
        method = 'search' if case['operation'] == 'places' else case['operation']
        return await getattr(port, method)(requests[case['id']], RequestContext(request_id=case['id']))
    report = await measure_cases(cases, invoke=invoke, clock=time.monotonic)
    report.update(measured_at=datetime.now(timezone.utc).isoformat(), provider=provider, instance_id=s.instance_id, endpoint=s.endpoint, package_version=__version__,
                  calls=counted.calls, samples_sha256=hashlib.sha256(samples_raw).hexdigest(),
                  thresholds_sha256=hashlib.sha256(thresholds_raw).hexdigest(),
                  rights_ref=record['rights_ref'], quota_ref=record['quota_ref'], purpose=record['purpose'],
                  instance_owner=record['instance_owner'], instance_version=record['instance_version'],
                  terms_ref=record['terms_ref'], pricing_ref=record['pricing_ref'], currency=record['currency'],
                  effective_limits=s.policy.model_dump(mode='json'), code_identity=package_identity(),
                  configuration_sha256=hashlib.sha256(json.dumps({'settings':s.model_dump(mode='json'),
                    **{k:record[k] for k in ('terms_ref','rights_ref','quota_ref','pricing_ref','purpose','instance_owner','instance_version')}}, sort_keys=True).encode()).hexdigest())
    gates = {'quality': report['status'],
             'latency': 'passed' if report.get('p95_s', math.inf) <= thresholds['max_p95_s'] else 'failed',
             'memory': 'passed' if report.get('peak_bytes', math.inf) <= thresholds['max_peak_bytes'] else 'failed',
             'budget': 'passed' if 0 < counted.calls <= record['max_calls'] else 'failed'}
    report['gates'] = gates
    if any(value != 'passed' for value in gates.values()):
        report['status'] = 'blocked' if report['status'] == 'blocked' else 'failed'
    return report


def run_live_test(provider):
    import pytest
    from .live_gate import require_live_activation
    record = require_live_activation(provider)
    path = os.environ.get('GEO_LIVE_BUDGET_DB')
    if not path:
        pytest.skip('persistent same-host quota ledger path absent; live measurement blocked')
    if not record.get('application_name') or not record.get('contact_url'):
        pytest.skip('application/contact configuration absent; live measurement blocked')
    output = os.environ.get('GEO_LIVE_REPORT_DIR')
    identity = package_identity()
    if not output or not identity['verified']:
        pytest.skip('report destination or verified clean source identity missing; live measurement blocked')
    try:
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ('.write-check-' + uuid.uuid4().hex)
        probe.write_text(''); probe.unlink()
    except OSError:
        pytest.skip('report destination unavailable; live measurement blocked')
    key = os.environ.get(record.get('credential_env') or '', '')
    auth_header = record.get('authentication_header') or (record.get('settings') or {}).get('authentication_header') or 'Authorization'
    requires_auth = record.get('authentication_required', (record.get('settings') or {}).get('authentication_required', provider == 'ors'))
    async def run():
        budget = LiveBudget(path, provider, uuid.uuid4().hex)
        try:
            async with asyncio.timeout(float(record['deadline_s'])):
                async with budget.source_slot():
                    return await run_provider(provider, record, budget=budget,
                        headers={auth_header: key} if key and requires_auth else {})
        except (TimeoutError, BudgetUnavailable):
            return {'status': 'blocked', 'reason': 'shared_budget_or_deadline_unavailable', 'provider': provider}
    report = asyncio.run(run())
    after = package_identity()
    report['source_commit'] = identity['source_commit']
    report['code_identity'] = identity
    if after != identity:
        report['status'] = 'failed'
        report['reason'] = 'measured_code_changed'
    (folder / f'{provider}-{uuid.uuid4().hex}.json').write_text(json.dumps(report, indent=2))
    if report['status'] == 'blocked':
        pytest.skip('approved frozen inputs or shared control missing; live measurement blocked')
    assert report['status'] == 'passed', 'measured provider quality/performance gate failed; inspect sanitized report'
