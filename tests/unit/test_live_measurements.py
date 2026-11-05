import asyncio
from decimal import Decimal
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.requests import RequestContext

PATH = Path(__file__).parents[1] / 'integration/live_measurements.py'
spec = importlib.util.spec_from_file_location('measurements', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CTX = RequestContext(request_id='synthetic-measurement')


@pytest.mark.parametrize('status', ['no_results', 'partial', 'unavailable', 'unknown', 'rate_limited'])
def test_missing_or_failed_response_cannot_pass_quality(status):
    async def invoke(case):
        return Result(status=Status(status), data=None, context=CTX)
    report = asyncio.run(m.measure_cases([{'id': 'case-1', 'operation': 'search',
        'expect': {'status': 'ok', 'candidate_ids': ['photon:osm:N:1'],
                   'candidate_points': {'photon:osm:N:1': [10, 50]}, 'max_error_m': 100,
                   'precisions': {'photon:osm:N:1': ['unknown']}, 'min_candidates': 1, 'max_candidates': 1}}], invoke=invoke, clock=lambda: 1.0))
    assert report['status'] == 'failed' and not report['cases'][0]['quality_passed']


def test_missing_labels_block_before_any_invocation():
    calls = []
    async def invoke(case):
        calls.append(case)
        raise AssertionError('unapproved label')
    report = asyncio.run(m.measure_cases([{'id': 'missing', 'operation': 'search'}], invoke=invoke, clock=lambda: 1.0))
    assert report['status'] == 'blocked' and not calls


def test_correct_photon_id_with_wrong_coordinates_is_not_accuracy_pass():
    from geo_intelligence_core.models.location import Candidate, Point
    async def invoke(case):
        return Result(status=Status.ok, data=[Candidate(id='right', source_ref='synthetic',
            point=Point(longitude=0, latitude=0), precision='house')], context=CTX)
    case = {'id': 'accuracy-1', 'operation': 'search', 'expect': {'status': 'ok',
            'candidate_ids': ['right'], 'candidate_points': {'right': [10, 50]}, 'max_error_m': 100, 'precisions': {'right': ['house']}, 'min_candidates': 1, 'max_candidates': 1}}
    assert asyncio.run(m.measure_cases([case], invoke=invoke, clock=lambda: 1.0))['status'] == 'failed'


def test_wrong_photon_candidate_and_exception_are_failed_and_redacted():
    from geo_intelligence_core.models.location import Candidate, Point
    async def wrong(case):
        return Result(status=Status.ok, data=[Candidate(id='wrong', source_ref='synthetic',
            point=Point(longitude=10, latitude=50), precision='unknown')], context=CTX)
    case = {'id': 'match-1', 'operation': 'search', 'expect': {'status': 'ok', 'candidate_ids': ['right'],
            'candidate_points': {'right': [10, 50]}, 'max_error_m': 100, 'precisions': {'right': ['house']}, 'min_candidates': 1, 'max_candidates': 1}}
    assert asyncio.run(m.measure_cases([case], invoke=wrong, clock=lambda: 1.0))['status'] == 'failed'
    async def throws(case):
        raise RuntimeError('synthetic-private-key-and-address')
    report = asyncio.run(m.measure_cases([case], invoke=throws, clock=lambda: 1.0))
    assert report['status'] == 'failed' and 'private-key' not in json.dumps(report)


@pytest.mark.parametrize('provider,operation,request_payload,expect,payload', [
    ('photon', 'search', {'text': 'Synthetic'}, {'status': 'ok', 'candidate_ids': ['photon:osm:N:1'],
     'candidate_points': {'photon:osm:N:1': [10, 50]}, 'max_error_m': 100,
                   'precisions': {'photon:osm:N:1': ['unknown']}, 'min_candidates': 1, 'max_candidates': 1},
     {'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [10, 50]},
                    'properties': {'osm_type': 'N', 'osm_id': 1, 'name': 'Synthetic'}}]}),
    ('ors', 'matrix', {'origins': {'A': {'longitude': 10, 'latitude': 50}},
                     'destinations': {'B': {'longitude': 10.01, 'latitude': 50.01}}, 'mode': 'walking'},
     {'status': 'ok', 'cells': {'A>B': [500, 700]}}, {'durations': [[600]]}),
    ('overpass', 'places', {'region': {'id': 'synthetic', 'version': '1', 'method': 'synthetic',
        'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [.01, 0], [.01, .01], [0, .01], [0, 0]]]}},
        'category_ids': ['food_service'], 'mapping_version': 'osm-v1'},
     {'status': 'ok', 'source_keys': ['osm:node:7', 'osm:node:8'], 'min_precision': 1.0, 'min_recall': 1.0},
     json.loads((Path(__file__).parents[1] / 'fixtures/overpass/places.json').read_text())),
])
def test_real_adapter_runner_uses_frozen_inputs_and_counted_budget(tmp_path, provider, operation, request_payload, expect, payload):
    from geo_intelligence_core.providers.budget import InMemoryBudget
    samples, thresholds = tmp_path/'samples.json', tmp_path/'thresholds.json'
    samples.write_text(json.dumps([{'id': 'sample-1', 'operation': operation, 'request': request_payload}]))
    thresholds.write_text(json.dumps({'cases': {'sample-1': expect}, 'max_p95_s': 5, 'max_peak_bytes': 50_000_000}))
    record = dict(approved=True, approved_origin={'ors': 'https://api.heigit.org', 'photon': 'https://photon.komoot.io',
                  'overpass': 'https://overpass.private.coffee'}[provider],
        samples_ref=str(samples), thresholds_ref=str(thresholds), max_calls=5, max_concurrency=1,
        max_response_bytes=100000, deadline_s=5.0, cost_ceiling=0, currency='EUR',
        purpose='synthetic', rights_ref='synthetic-rights', quota_ref='synthetic-quota',
        instance_owner='synthetic', instance_version='unknown', pricing_ref='synthetic-zero', terms_ref='synthetic')
    calls = []
    def reply(req):
        calls.append(req)
        return httpx.Response(200, json=payload)
    report = asyncio.run(m.run_provider(provider, record, budget=InMemoryBudget(5, Decimal(0)),
        headers={'Authorization': 'synthetic'} if provider == 'ors' else {},
        transport=httpx.MockTransport(reply), resolver=lambda _: ['93.184.215.14']))
    assert report['status'] == 'passed' and report['calls'] == len(calls) == 1
    assert len(report['samples_sha256']) == len(report['thresholds_sha256']) == 64
    assert report['provider'] == provider and 'synthetic' not in json.dumps(report.get('headers', {}))


def test_persistent_ledger_shared_across_objects_and_run_ids(tmp_path):
    async def run():
        db = tmp_path/'quota.sqlite'
        a, b = m.LiveBudget(db, 'photon', 'run-a'), m.LiveBudget(db, 'photon', 'run-b')
        for i in range(10):
            assert await m.LiveBudget(db, 'photon', f'prefill-{i}').reserve('instance', 5, Decimal(0))
        assert not await a.reserve('alias-key-a', 1, Decimal(0))
        assert not await b.reserve('alias-key-b', 1, Decimal(0))
        assert await m.LiveBudget(db, 'overpass', 'other-run').reserve('instance', 1, Decimal(0))
    asyncio.run(run())


def test_negative_controls_are_typed_and_cause_specific():
    from geo_intelligence_core.models.spatial import TravelMatrix, MatrixCell
    from geo_intelligence_core.models.places import PlaceSet
    from geo_intelligence_core.models.common import Issue
    positive={'id':'positive','operation':'matrix','expect':{'status':'ok','cells':{'A>B':[1,3]}}}
    negative={'id':'no-route','operation':'route','expect':{'status':'unavailable','issue_code':'no_route'}}
    async def timeout(case):
        if case['id']=='positive':
            return Result(status=Status.ok,data=TravelMatrix(cells=[MatrixCell(origin_id='A',destination_id='B',duration_s=2,status=Status.ok)]),context=CTX)
        return Result(status=Status.unavailable,data=None,context=CTX,issues=[Issue(code='network_failure',message_key='provider.network_failure')])
    assert asyncio.run(m.measure_cases([positive,negative],invoke=timeout,clock=lambda:1.0))['status']=='failed'
    no_cell={'id':'no-cell','operation':'matrix','expect':{'status':'unavailable','issue_code':'no_route_cells','cells':{'A>B':None}}}
    empty={'id':'empty','operation':'places','expect':{'status':'no_results'}}
    async def valid(case):
        if case['id']=='positive':return await timeout(case)
        if case['id']=='empty':return Result(status=Status.no_results,data=PlaceSet(places=[],retrieved_count=0,unique_count=0),context=CTX)
        return Result(status=Status.unavailable,data=TravelMatrix(cells=[MatrixCell(origin_id='A',destination_id='B',duration_s=None,status=Status.unavailable)]),context=CTX,issues=[Issue(code='no_route_cells',message_key='routing.no_route_cells')])
    assert asyncio.run(m.measure_cases([positive,no_cell,empty],invoke=valid,clock=lambda:1.0))['status']=='passed'


def test_precision_ambiguity_and_unknown_expectations_cannot_be_ignored():
    from geo_intelligence_core.models.location import Candidate,Point
    async def invoke(case):
        return Result(status=Status.ok,data=[Candidate(id='wrong',source_ref='synthetic',point=Point(longitude=10,latitude=50),precision='house'),
            Candidate(id='right',source_ref='synthetic',point=Point(longitude=10,latitude=50),precision='unknown')],context=CTX)
    case={'id':'precision','operation':'search','expect':{'status':'ok','candidate_ids':['right'],
        'candidate_points':{'right':[10,50]},'max_error_m':100,'precisions':{'right':['house']},
        'min_candidates':1,'max_candidates':1}}
    assert asyncio.run(m.measure_cases([case],invoke=invoke,clock=lambda:1.0))['status']=='failed'
    case['expect']['unsupported_quality_rule']=True
    assert asyncio.run(m.measure_cases([case],invoke=invoke,clock=lambda:1.0))['status']=='blocked'


@pytest.mark.parametrize('credential_env',[None,'SYNTHETIC_OLD_INSTANCE_KEY'])
def test_null_credential_name_for_public_source_does_not_crash(tmp_path,monkeypatch,credential_env):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    import integration.live_gate as gate
    record={'credential_env':credential_env,'authentication_required':False,'deadline_s':1.0,'application_name':'Synthetic','contact_url':'https://app.example.org'}
    if credential_env:monkeypatch.setenv(credential_env,'synthetic-old-private-instance-key')
    monkeypatch.setattr(gate,'require_live_activation',lambda _:record)
    monkeypatch.setattr(m,'__package__','integration')
    monkeypatch.setattr(m,'__spec__',importlib.util.spec_from_file_location('integration.measurements',PATH))
    monkeypatch.setattr(m,'package_identity',lambda:{'verified':True,'source_commit':'a'*40,'code_sha256':'b'*64,'runner_sha256':'c'*64},raising=False)
    monkeypatch.setenv('GEO_LIVE_BUDGET_DB',str(tmp_path/'quota.sqlite'))
    monkeypatch.setenv('GEO_LIVE_REPORT_DIR',str(tmp_path/'reports'))
    seen=[]
    async def invoke(provider,record,**kwargs):
        seen.append(kwargs['headers'])
        return {'status':'passed','calls':1}
    monkeypatch.setattr(m,'run_provider',invoke)
    m.run_live_test('photon')
    assert seen==[{}]


def test_code_identity_is_bound_to_imported_package_not_cwd(tmp_path,monkeypatch):
    before=m.package_identity()
    monkeypatch.chdir(tmp_path)
    after=m.package_identity()
    assert before==after and len(after['code_sha256'])==64


def test_runner_honors_explicit_inbound_and_auth_configuration(tmp_path):
    from geo_intelligence_core.providers.budget import InMemoryBudget
    request_payload={'location':{'id':'synthetic','version':1,'point':{'longitude':10,'latitude':50},
        'confirmation':{'method':'manual','at':'2026-11-05T00:00:00Z','evidence_ids':['synthetic']}},
        'direction':'inbound','mode':'walking','durations_s':[300,600,900]}
    samples,thresholds=tmp_path/'samples.json',tmp_path/'thresholds.json'
    samples.write_text(json.dumps([{'id':'inbound','operation':'catchments','request':request_payload}]))
    thresholds.write_text(json.dumps({'cases':{'inbound':{'status':'ok','durations_s':[300,600,900],
        'direction':'inbound','area_m2':[1,1e10]}},'max_p95_s':5,'max_peak_bytes':50_000_000}))
    record=dict(approved=True,approved_origin='https://owned.example.org',endpoint='https://owned.example.org/prefix',
        instance_id='owned-ors',authentication_required=True,authentication_header='X-Api-Key',
        capability_flags={'route':True,'travelmatrix':True,'catchment':True,'catchment_inbound':True},
        samples_ref=str(samples),thresholds_ref=str(thresholds),max_calls=5,max_concurrency=1,max_response_bytes=100000,
        deadline_s=5,cost_ceiling=0,currency='EUR',purpose='synthetic',rights_ref='synthetic',quota_ref='synthetic',
        pricing_ref='synthetic',terms_ref='synthetic',instance_owner='synthetic',instance_version='unknown',max_area_m2=1e10)
    payload=json.loads((Path(__file__).parents[1]/'fixtures/ors/isochrones.json').read_text())
    payload['metadata']['query']['location_type']='destination'
    seen=[]
    def reply(req):
        seen.append(req)
        return httpx.Response(200,json=payload)
    report=asyncio.run(m.run_provider('ors',record,budget=InMemoryBudget(5,Decimal(0)),headers={'X-Api-Key':'synthetic-only'},
        transport=httpx.MockTransport(reply),resolver=lambda _:['93.184.215.14']))
    assert report['status']=='passed' and len(seen)==1
    assert seen[0].headers['x-api-key']=='synthetic-only'


def test_live_ledger_last_slot_and_source_lock_cancellation(tmp_path):
    async def run():
        db=tmp_path/'shared.sqlite'
        for i in range(10):
            assert await m.LiveBudget(db,'photon',f'fill-{i}').reserve('alias',min(5,49-i*5),Decimal(0))
        a,b=m.LiveBudget(db,'photon','a'),m.LiveBudget(db,'photon','b')
        granted=await asyncio.gather(a.reserve('key-a',1,Decimal(0)),b.reserve('key-b',1,Decimal(0)))
        assert sorted(granted)==[False,True]
        async with a.source_slot():
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(.02):
                    async with b.source_slot():raise AssertionError('source overlap')
        entered=asyncio.Event()
        async def holder():
            async with b.source_slot():
                entered.set()
                await asyncio.Event().wait()
        task=asyncio.create_task(holder());await entered.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        async with a.source_slot():pass
        assert not await m.LiveBudget(db,'photon','new-client').reserve('new-alias',1,Decimal(0))
    asyncio.run(run())
