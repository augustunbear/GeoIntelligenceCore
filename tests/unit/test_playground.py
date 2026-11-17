"""Playground registry, examples, quota and HTTP contracts."""
import asyncio
import http.client
import inspect
import json
import threading
from http.server import ThreadingHTTPServer

import pytest
import geo_intelligence_core as core
from geo_intelligence_core.playground import catalog, execute, Handler, DailyBudget, LIVE


def test_public_function_coverage_and_examples():
    ops = catalog()
    assert all(name in ops for name in core.__all__ if inspect.isfunction(getattr(core,name,None)))
    for name, info in ops.items():
        assert info['status'] in {'executable','needs_configuration','unsupported','not_suitable'}
        assert info['reason'] and info['category'] and info['name']
        assert info['schema']['type']=='object'
        if info['available']:
            assert isinstance(info['example'],dict)
            assert set(info['example']) <= set(info['schema']['properties'])
            result = execute(name,info['example'])
            if isinstance(result,dict) and 'status' in result:
                assert result['status'] not in ('invalid_input','unavailable','unconfigured','unknown')
    assert ops['parse_map_link']['example']['url'].startswith('https://')
    assert {'normalize_places','company_site','import_company','import_transport','resolve_config','compare_snapshots','apply_correction'} <= set(ops)


def test_offline_execution_and_invalid():
    assert execute('parse_map_link',catalog()['parse_map_link']['example'])['status']=='ok'
    assert execute('normalize_comparison_text',{'value':'Café Müller'})=='cafe muller'
    for name,params in [('__dict__',{}),('apply_correction',{'value':-1}),('distance_m',{'a':{'longitude':181,'latitude':49},'b':{'longitude':11,'latitude':49}}),('distance_m',{'a':{},'b':{},'__class__':1})]:
        with pytest.raises((ValueError,TypeError)):
            execute(name,params)


def test_live_opt_in_and_key_never_in_catalog(monkeypatch):
    monkeypatch.setenv('ORS_API_KEY','PRIVATE-SENTINEL')
    assert 'PRIVATE-SENTINEL' not in json.dumps(catalog())
    with pytest.raises(ValueError): execute('ors_route',LIVE['ors_route'][2],live=True)
    assert execute('ors_route',LIVE['ors_route'][2])['status']=='ok'


def test_atomic_daily_quota(tmp_path):
    async def scenario():
        budget=DailyBudget(tmp_path/'quota.sqlite3')
        assert all(await asyncio.gather(*(budget.reserve('photon',1,0) for _ in range(50))))
        assert not await budget.reserve('photon',1,0)
        assert await DailyBudget(tmp_path/'quota.sqlite3').reserve('ors',1,0)
    asyncio.run(scenario())


def test_http_assets_origin_and_run(monkeypatch):
    # This test opens only an ephemeral 127.0.0.1 socket, never a remote endpoint.
    monkeypatch.undo()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def call(method,path,payload=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        conn.request(method,path,body=payload,headers=headers or {})
        response=conn.getresponse();body=response.read();status=response.status;conn.close()
        return status,body
    try:
        assert b'playground.js' in call('GET','/')[1]
        assert b'copy-response' in call('GET','/playground.js')[1]
        ops=json.loads(call('GET','/api/operations')[1])['operations']
        assert len(ops)>=28
        headers={'Content-Type':'application/json'}
        payload=json.dumps({'operation':'distance_m','params':catalog()['distance_m']['example'],'live':False})
        status,body=call('POST','/api/run',payload,headers)
        assert status==200 and json.loads(body)['data']>0
        assert call('POST','/api/run',payload,{**headers,'Origin':'http://evil.test'})[0]==403
        assert call('POST','/api/run',payload,{**headers,'Host':'evil.test'})[0]==403
        assert call('POST','/api/run','{}',headers)[0]==400
    finally:
        server.shutdown();server.server_close();thread.join()


def test_provider_method_coverage():
    from geo_intelligence_core.providers.photon import PhotonResolver
    from geo_intelligence_core.providers.overpass import OverpassPlaceProvider
    from geo_intelligence_core.providers.ors import OrsRoutingProvider
    from geo_intelligence_core.playground import LIVE
    registrations={(row[3],row[4]) for row in LIVE.values()}
    for protocol,cls in [('photon',PhotonResolver),('overpass',OverpassPlaceProvider),('ors',OrsRoutingProvider)]:
        public={name for name,fn in inspect.getmembers(cls,inspect.iscoroutinefunction) if not name.startswith('_')}
        assert public == {method for source,method in registrations if source==protocol}
