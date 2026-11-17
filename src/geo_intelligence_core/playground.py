"""Explicit, local playground adapters; never executes arbitrary public functions."""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import sqlite3
import time
import threading
from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import get_type_hints

from pydantic import TypeAdapter, ValidationError, create_model
import geo_intelligence_core as core
from .geometry import point_in_region
from .places import normalize_places, company_site
from .inputs.company import import_company
from .inputs.transport import import_transport
from .history import compare_snapshots
from .configuration import resolve_config
from .models.places import PlaceQuery
from .models.requests import SearchRequest, ReverseRequest, RequestContext
from .models.spatial import RouteRequest, MatrixRequest, CatchmentRequest
from .providers.budget import InMemoryBudget
from .providers.trial import TrialSettings, build_trial_provider

POINT = {'longitude': 11.0767, 'latitude': 49.4521}
SECOND = {'longitude': 11.08, 'latitude': 49.455}
LIMITS = {'max_area_m2': 100_000_000.0, 'max_vertices': 500}
REGION = {'id': 'synthetic-region', 'version': '1', 'method': 'synthetic', 'source_ref': 'synthetic',
          'geometry': {'type': 'Polygon', 'coordinates': [[[11.07,49.45],[11.09,49.45],[11.09,49.46],[11.07,49.46],[11.07,49.45]]]}}
PLACES = [{'source_key': {'source_id': 'synthetic', 'entity_type': 'node', 'entity_id': '1'},
           'native_names': {'name': '示例餐馆'}, 'point': POINT, 'categories': ['restaurant'],
           'address': {'locality': 'Nürnberg'}}]
EVIDENCE = {'id': 'sample', 'source_id': 'synthetic', 'source_type': 'fixture',
            'source_ref': 'playground', 'retrieved_at': '2026-11-17T00:00:00Z', 'method_version': 'synthetic-v1',
            'rights': {'use': 'allowed', 'retain': 'allowed', 'export': 'allowed', 'permitted_purpose': 'demo'}, 'quality': {}}
LOCATION = {'id': 'synthetic', 'version': 1, 'point': POINT,
            'confirmation': {'method': 'manual', 'at': '2026-11-17T00:00:00Z', 'evidence_ids': ['sample']}}
QUERY = {'region': REGION, 'category_ids': ['restaurant'], 'mapping_version': 'osm-v1'}

# Explicit registration is the sole execution authority. Public API coverage is checked in CI.
# tuple: display name, category, example, callable, mode, dependencies, reason.
DIRECT = {
 'distance_m': ('两点距离','地理计算',{'a':POINT,'b':SECOND},core.distance_m,'offline',['geometry']),
 'circle': ('圆形区域','地理计算',{'request':{'center':POINT,'radius_m':500.0},'limits':LIMITS},core.circle,'offline',['geometry']),
 'combine': ('区域合并、相交或差集','地理计算',{'regions':[REGION,REGION], 'operation':{'kind':'union'},'limits':LIMITS},core.combine,'offline',['geometry']),
 'point_in_region': ('点是否位于区域','地理计算',{'point':POINT,'region':REGION},point_in_region,'offline',['geometry']),
 'parse_map_link': ('解析 OpenStreetMap 链接','地址与位置',{'url':'https://www.openstreetmap.org/?mlat=49.4521&mlon=11.0767'},core.parse_map_link,'offline',[]),
 'confirm_location': ('人工确认地点','地址与位置',{'request':{'point':POINT,'confirmation':{'method':'manual','at':'2026-11-17T00:00:00Z','evidence_ids':['sample']},'evidence':[EVIDENCE]}},core.confirm_location,'offline',[]),
 'normalize_comparison_text': ('文本标准化','数据处理',{'value':'Café Müller Nürnberg'},core.normalize_comparison_text,'offline',[]),
 'find_duplicate_candidates': ('地点去重候选','数据处理',{'records':PLACES},core.find_duplicate_candidates,'offline',['geometry']),
 'summarize_place_quality': ('字段完整性与质量','数据处理',{'records':PLACES},core.summarize_place_quality,'offline',[]),
 'normalize_observation': ('计数观测验证','数据处理',{'observation':{'id':'sample','point':POINT,'start':'2026-11-17T09:00:00Z','end':'2026-11-17T10:00:00Z','timezone':'Europe/Berlin','direction':'northbound','count_object':'visit','count':0,'method':'synthetic','dedupe':'unknown','evidence':[EVIDENCE]}},core.normalize_observation,'offline',[]),
 'company_site': ('识别已提供的办公室地点','数据处理',{'place':{**PLACES[0],'categories':['office']}},company_site,'offline',[]),
 'import_company': ('导入已提供的公司场所','数据处理',{'records':[{'id':'site-1','source_id':'synthetic','source_ref':'playground','site_role':'branch','point':POINT}], 'evidence':EVIDENCE, 'purpose':'demo'},import_company,'offline',[]),
 'import_transport': ('导入已提供的交通事实','数据处理',{'records':[{'id':'parking-1','kind':'parking_capacity','value':80,'unit':'spaces','location':POINT,'valid_from':'2026-11-17T09:00:00Z','valid_until':'2026-11-17T14:00:00Z','measured_at':'2026-11-17T10:00:00Z','evidence_ids':['sample']}], 'evidence':[EVIDENCE], 'purpose':'demo', 'as_of':'2026-11-17T12:00:00Z'},import_transport,'offline',[]),
 'normalize_places': ('地点类别与区域标准化','数据处理',{'records':PLACES,'query':QUERY},normalize_places,'offline',['geometry']),
 'evaluate_opening_hours': ('营业时间解析','数据处理',{'hours_raw':'Mo-Fr 09:00-18:00','at':'2026-11-17T10:00:00Z','timezone':'Europe/Berlin'},core.evaluate_opening_hours,'offline',['temporal']),
 'load_profile': ('加载行业配置','分析与结果',{'ref':'food-service@1'},core.load_profile,'offline',[]),
 'load_template': ('加载分析模板','分析与结果',{'ref':'surroundings@1'},core.load_template,'offline',[]),
 'import_region': ('导入本地 GeoJSON 区域','地理计算',{'document':{'type':'Feature','properties':{'id':'sample','version':'1','source_ref':'playground','reference_period':'2026','crs':'EPSG:4326','scale_denominator':1000},'geometry':REGION['geometry']},'evidence':{**EVIDENCE,'reference_period':'2026'},'purpose':'demo'},core.import_region,'offline',['geometry']),
}

class SyntheticPlaces:
    async def search(self, query, context):
        from .models.common import Result, Status
        from .models.places import PlaceSet
        from .models.evidence import Evidence
        return Result(status=Status.ok, data=PlaceSet(places=[], retrieved_count=0, unique_count=0),
                      context=context, evidence=[Evidence.model_validate(EVIDENCE)])

def _analysis(params, action):
    from .models.configuration import AnalyzeRequest
    from .models.policy import UsagePolicy
    registry = core.ProviderRegistry()
    registry.register('places', SyntheticPlaces())
    request = AnalyzeRequest.model_validate({
        'locations': [LOCATION], 'regions': [REGION], 'topics': [{'id': 'places'}],
        'explicit_parameters': {'category_ids': params.get('category_ids', ['restaurant'])},
        'profile_ref': params.get('profile_ref', 'food-service@1'),
        'template_ref': params.get('template_ref', 'venue-discovery@1'), 'request_id': 'playground-offline'})
    result = asyncio.run(core.analyze(request, registry,
        UsagePolicy(allowed_capabilities=['places'], max_calls_per_run=3), InMemoryBudget(3, Decimal(0))))
    if action == 'analyze' or result.data is None: return result
    if action == 'snapshot': return core.snapshot(result.data, purpose='demo')
    if action == 'export_result':
        snap = core.snapshot(result.data, purpose='demo')
        return core.export_result(snap.data, format=params.get('format','json'), language=params.get('language','zh-CN'), purpose='demo')
    if action == 'resolve_config':
        from .models.configuration import AnalyzeRequest
        from .models.policy import UsagePolicy
        registry=core.ProviderRegistry(); registry.register('places',SyntheticPlaces())
        return resolve_config(AnalyzeRequest(topics=[{'id':'places'}],explicit_parameters={'category_ids':params.get('category_ids',['restaurant'])},request_id='playground-config'),None,None,UsagePolicy(allowed_capabilities=['places'],max_calls_per_run=3),registry=registry)
    if action == 'compare_snapshots':
        from .models.analysis import Analysis
        from .models.common import Result, Status
        from .models.evidence import Evidence
        from .models.places import Place, PlaceSet
        context=RequestContext(request_id='synthetic-history',location_versions={'site':1},method_version='analysis-v1',effective_conditions={'query':'synthetic-500m'})
        evidence=Evidence.model_validate(EVIDENCE)
        def snap(ids):
            places=[Place.model_validate({**PLACES[0],'source_key':{'source_id':'synthetic','entity_type':'site','entity_id':str(i)},'evidence_ids':['sample']}) for i in ids]
            topic=Result(status=Status.ok,data=PlaceSet(places=places,retrieved_count=len(places),unique_count=len(places),coverage='complete:synthetic-area-v1'),evidence=[evidence],context=context)
            return core.snapshot(Analysis(request_context=context,selected_topics=['places'],topic_results={'places':topic}),'demo').data
        return compare_snapshots(snap([1,2]),snap([1]))
    if action == 'apply_correction':
        from .models.analysis import Analysis, Correction, Metric
        from .models.common import Result, Status
        from .models.evidence import Evidence
        context=RequestContext(request_id='synthetic-correction',scope_token='synthetic-only')
        evidence=Evidence.model_validate(EVIDENCE)
        original=Analysis(request_context=context,selected_topics=['places'],topic_results={
            'places':Result(status=Status.ok,data={'count':Metric(value=4,unit='items',nature='measured',evidence_ids=['sample'])},context=context,evidence=[evidence])})
        value=params.get('value',7)
        if type(value) is not int or value<0 or value>1_000_000: raise ValueError('value must be a bounded nonnegative integer')
        correction=Correction(target_ref='places/count',action='correct',replacement={'value':value,'unit':'items','nature':'measured','evidence_ids':['sample']},evidence_ids=['sample'],reason='synthetic fixture',scope_token='synthetic-only',at='2026-11-17T00:00:00Z')
        return core.apply_correction(original,correction,'synthetic-only')
    if action == 'compare':
        from .models.analysis import Analysis
        from .models.common import Result, Status
        from .models.places import PlaceSet
        def row(identity):
            context=RequestContext(request_id=identity,location_versions={identity:1},effective_conditions={'config.category_ids':"('restaurant',)",'config.radius_m':'500','region_method':'synthetic','region_version':'1','boundary_rule':'point_covers'})
            from .models.evidence import Evidence
            topic=Result(status=Status.ok,data=PlaceSet(places=[],retrieved_count=0,unique_count=0,coverage='known'),context=context,evidence=[Evidence.model_validate({**EVIDENCE,'reference_period':'2025'})])
            return Analysis(request_context=context,topic_results={'places':topic},selected_topics=['places'])
        return core.compare([row('first'),row('second')],params.get('metric_ids',['places.unique_count']))
    raise ValueError('不支持的操作')

SPECIAL = {
 'analyze': ('离线分析执行','分析与结果',{'category_ids':['restaurant'],'template_ref':'venue-discovery@1'},'offline',['geometry']),
 'resolve_config': ('配置与能力预检','分析与结果',{'category_ids':['restaurant']},'offline',[]),
 'compare_snapshots': ('合成历史快照比较','分析与结果',{},'offline',[]),
 'apply_correction': ('合成案件的事实更正','分析与结果',{'value':7},'offline',[]),
 'compare': ('地点事实比较','分析与结果',{'metric_ids':['places.unique_count']},'offline',['geometry']),
 'snapshot': ('保留结果快照','分析与结果',{},'offline',['geometry']),
 'export_result': ('结果导出','分析与结果',{'format':'json','language':'zh-CN'},'offline',['geometry']),
}
LIVE = {
 'photon_search': ('Photon 地址搜索','地址与位置',{'text':'Nürnberg Hauptbahnhof','limit':3},'photon','search',SearchRequest),
 'photon_reverse': ('Photon 坐标反查','地址与位置',{'point':POINT},'photon','reverse',ReverseRequest),
 'overpass_places': ('Overpass 周边 POI','周边 POI',{'region':REGION,'category_ids':['restaurant'],'mapping_version':'osm-v1'},'overpass','search',PlaceQuery),
 'ors_route': ('ORS 路线','路网',{'origin':POINT,'destination':SECOND,'mode':'walking'},'ors','route',RouteRequest),
 'ors_matrix': ('ORS 路线矩阵','路网',{'origins':{'a':POINT},'destinations':{'b':SECOND},'mode':'walking'},'ors','matrix',MatrixRequest),
 'ors_catchments': ('ORS 等时线','路网',{'location':LOCATION,'direction':'outbound','mode':'walking','durations_s':[600]},'ors','catchments',CatchmentRequest),
}

# An explicit exception with reason protects complex mutable correction workflows.
EXCEPTIONS = {}

def _schema(fn):
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    fields = {key: (hints.get(key, object), ... if p.default is inspect.Parameter.empty else p.default)
              for key, p in sig.parameters.items() if key != 'context'}
    return create_model('Playground_' + fn.__name__, **fields).model_json_schema()

PARAM_HELP = {
 'a':'起点经纬度（longitude、latitude）','b':'终点经纬度（longitude、latitude）',
 'point':'WGS84 经纬度','region':'已知的 GeoJSON 区域','regions':'要合并或比较的区域列表',
 'operation':'union 合并、intersection 相交、difference 差集','limits':'面积与顶点数上限',
 'request':'对应功能的请求对象','url':'完整 OpenStreetMap 地图链接',
 'value':'文字或合成修正值','records':'已提供的结构化记录列表',
 'query':'区域、类别和映射版本','threshold':'疑似重复阈值','max_records':'记录数量上限',
 'hours_raw':'原始营业时间表达式','at':'带时区的 ISO-8601 测试时刻',
 'timezone':'地点的 IANA 时区','ref':'精确的资源名称和版本，如 food-service@1',
 'document':'一个已获授权的 GeoJSON Feature','evidence':'来源、时间与使用权证据',
 'purpose':'与证据使用权一致的用途','category_ids':'已知 POI 类别 ID',
 'template_ref':'分析模板及版本','profile_ref':'行业配置及版本',
 'format':'json、geojson 或 csv','language':'de、zh-CN 或 en',
 'metric_ids':'要比较的事实指标 ID','text':'地址或地点关键词',
 'limit':'候选数量上限','country_codes':'国家代码列表','bbox':'经纬度边界框',
 'near':'可选的邻近坐标','origin':'路线起点','destination':'路线终点',
 'origins':'矩阵起点 ID 到坐标','destinations':'矩阵终点 ID 到坐标',
 'mode':'walking、cycling 或 driving','time':'带时区的时刻；部分路网模式不支持',
 'time_kind':'depart_at 或 arrive_by','location':'已确认的合成地点',
 'entrance_id':'可选入口 ID','direction':'outbound 或 inbound',
 'durations_s':'等时线时长（秒）列表','mapping_version':'OSM 类别映射版本',
 'boundary_rule':'点与区域的边界判定','as_of':'带时区的事实验证时刻',
}

def _annotate_schema(schema):
    for key, field in schema.get('properties', {}).items():
        field.setdefault('description', PARAM_HELP.get(key, '对应接口的结构化输入'))
    return schema

def catalog():
    operations = {}
    for name,(title,cat,example,fn,mode,deps) in DIRECT.items():
        operations[name] = {'name':title,'category':cat,'description': (inspect.getdoc(fn) or title).splitlines()[0],
          'schema':_annotate_schema(_schema(fn)),'example':example,'status':'executable','reason':'真实本地实现，使用固定示例。',
          'mode':mode,'dependencies':deps,'api_key':False,'permission':'只处理本机提交的样本；请勿粘贴未经许可的数据。','available':True}
    for name,(title,cat,example,mode,deps) in SPECIAL.items():
        operations[name] = {'name':title,'category':cat,'description':'使用内置合成地点与授权样本执行真实核心分析。',
          'schema':_annotate_schema({'type':'object','additionalProperties':False,'properties':{k:{'type':'array' if isinstance(v,list) else 'integer' if isinstance(v,int) else 'string'} for k,v in example.items()}}),
          'example':example,'status':'executable','reason':'合成样本；不代表真实周边数据。', 'mode':mode,'dependencies':deps,'api_key':False,'permission':'仅合成数据。','available':True}
    for name,(title,cat,example,protocol,method,model) in LIVE.items():
        operations[name] = {'name':title,'category':cat,'description':f'离线调用同一 {protocol} Provider 的固定响应；实时调用需服务端显式开启。',
          'schema':_annotate_schema(model.model_json_schema()),'example':example,
          'status':'needs_configuration' if protocol=='ors' and not os.getenv('ORS_API_KEY') else 'executable',
          'reason':'实时需 GEO_PLAYGROUND_LIVE=1；ORS 还需服务端 ORS_API_KEY。',
          'mode':'live','dependencies':['providers']+(['geometry'] if protocol in ('overpass','ors') else []),
          'api_key':protocol=='ors','permission':'仅本机、一次确认、固定公开端点；每天每来源最多 50 次尝试。','available':True}
    for name,reason in EXCEPTIONS.items():
        operations[name]={'name':name,'category':'数据处理','description':reason,'schema':{'type':'object'},'example':{},
          'status':'not_suitable','reason':reason,'mode':'offline','dependencies':[],'api_key':False,'permission':reason,'available':False}
    return operations

LIVE_SLOT = threading.BoundedSemaphore(1)

class DailyBudget:
    """Persistent, atomic same-host daily reserve. Conservative: failures consume allowance."""
    def __init__(self, path): self.path = str(path)
    async def reserve(self, provider_id, calls, estimated_cost):
        if calls != 1 or estimated_cost != 0: return False
        try:
            with sqlite3.connect(self.path, timeout=2, isolation_level=None) as db:
                db.execute('PRAGMA busy_timeout=2000')
                db.execute('CREATE TABLE IF NOT EXISTS usage(day TEXT, source TEXT, calls INTEGER, PRIMARY KEY(day,source))')
                db.execute('BEGIN IMMEDIATE')
                day = datetime.now(timezone.utc).date().isoformat()
                count = db.execute('SELECT calls FROM usage WHERE day=? AND source=?',(day,provider_id)).fetchone()
                if count and count[0] >= 50: db.execute('ROLLBACK'); return False
                db.execute('INSERT INTO usage VALUES (?,?,1) ON CONFLICT(day,source) DO UPDATE SET calls=calls+1',(day,provider_id))
                db.execute('COMMIT'); return True
        except sqlite3.Error:
            from .providers.budget import BudgetUnavailable
            raise BudgetUnavailable('local quota unavailable') from None
    async def record(self, provider_id, actual_cost): pass

async def _provider(name, params, live=False):
    import httpx
    from .models.common import Status
    title,cat,example,protocol,method,model = LIVE[name]
    request = model.model_validate(params)
    if protocol == 'photon' and name == 'photon_search' and request.limit > 5:
        raise ValueError('一次最多返回 5 个地点候选')
    if name == 'ors_matrix' and (len(request.origins) > 5 or len(request.destinations) > 5 or len(request.origins)*len(request.destinations)>25):
        raise ValueError('路线矩阵最多 5 × 5')
    if name == 'ors_catchments' and (len(request.durations_s)>3 or any(v>1800 for v in request.durations_s)):
        raise ValueError('等时线最多 3 档，每档不超过 1800 秒')
    if name == 'ors_route' and core.distance_m(request.origin, request.destination)>20_000:
        raise ValueError('测试路线端点最多相距 20 km')
    if live and os.getenv('GEO_PLAYGROUND_LIVE') != '1': raise ValueError('实时服务未在本机开启')
    key = os.getenv('ORS_API_KEY') if live and protocol=='ors' else None
    if live and protocol=='ors' and not key: raise ValueError('ORS_API_KEY 未配置')
    settings = TrialSettings.public(protocol, application_name='GeoPlayground',
                                  contact_url='https://github.com/augustunbear/GeoIntelligenceCore')
    budget = DailyBudget(Path(os.getenv('GEO_PLAYGROUND_QUOTA_FILE',str(Path.home()/'.geo-playground-quota.sqlite3')))) if live else InMemoryBudget(5,Decimal(0))
    provider = build_trial_provider(settings,budget=budget,headers={'Authorization':key} if key else None)
    if not live:
        responses = {
          'photon': {'features':[]}, 'overpass':{'elements':[]},
          'ors_route': {'features':[{'geometry':{'type':'LineString','coordinates':[[11.0767,49.4521],[11.08,49.455]]},'properties':{'summary':{'distance':400,'duration':360}}}],'metadata':{'query':{'units':'m'}}},
          'ors_matrix': {'durations':[[360]],'metadata':{'query':{'sources':[0],'destinations':[1]}}},
          'ors_catchments': {'metadata':{'query':{'range_type':'time','range':[600],'location_type':'start'}},'features':[{'type':'Feature','properties':{'group_index':0,'value':600},'geometry':{'type':'Polygon','coordinates':[[[11.075,49.451],[11.079,49.451],[11.079,49.456],[11.075,49.456],[11.075,49.451]]]}}]},
        }
        payload=responses.get(name,responses.get(protocol))
        provider.gateway.transport=httpx.MockTransport(lambda request:httpx.Response(200,json=payload))
        provider.gateway.resolver=lambda _: ['93.184.215.14']
        if protocol=='ors':
            # Hosted ORS requires credentials even for synthetic responses; never use an actual key offline.
            provider=build_trial_provider(settings,budget=budget,headers={'Authorization':'offline-fixture-only'})
            provider.gateway.transport=httpx.MockTransport(lambda request:httpx.Response(200,json=payload))
            provider.gateway.resolver=lambda _: ['93.184.215.14']
    return await getattr(provider,method)(request,RequestContext(request_id='playground-'+name))

def _json(value):
    if hasattr(value,'model_dump'): return value.model_dump(mode='json')
    return json.loads(json.dumps(value,default=str))

def execute(name,params,*,live=False):
    if not isinstance(params,dict) or name not in catalog() or name in EXCEPTIONS:
        raise ValueError('未知或不可执行的功能')
    if name in DIRECT:
        _,_,_,fn,_,_=DIRECT[name]
        sig=inspect.signature(fn)
        if set(params)-set(sig.parameters): raise ValueError('多余参数')
        hints=get_type_hints(fn)
        parsed={key:TypeAdapter(hints[key]).validate_python(value) if key in hints else value for key,value in params.items()}
        if name == 'import_transport': parsed['context']=RequestContext(request_id='playground-transport')
        sig.bind(**parsed)
        if name in ('circle','combine') and (parsed['limits'].max_vertices>1000 or parsed['limits'].max_area_m2>1_000_000_000):
            raise ValueError('Playground 区域上限为 1000 顶点和 1000 km²')
        if name == 'circle' and parsed['request'].radius_m>10_000:
            raise ValueError('Playground 圆形半径最多 10 km')
        return _json(fn(**parsed))
    if name in SPECIAL:
        if set(params)-set(SPECIAL[name][2]): raise ValueError('多余参数')
        return _json(_analysis(params,name))
    if name in LIVE:
        if live and os.getenv('GEO_PLAYGROUND_LIVE')!='1': raise ValueError('实时服务未开启')
        return _json(asyncio.run(_provider(name,params,live)))
    raise ValueError('未知功能')

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(35)
    def _headers(self,status,mime,length):
        self.send_response(status); self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(length));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
    def _local(self):
        host=self.headers.get('Host',''); origin=self.headers.get('Origin')
        port=str(self.server.server_port)
        if host in ('127.0.0.1:'+port,'localhost:'+port):
            return origin is None or origin=='http://'+host
        name=os.getenv('CODESPACE_NAME','')
        domain=os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN','')
        # Only this codespace's exact HTTPS forwarding host is accepted.
        if (os.getenv('CODESPACES')!='true' or
            not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name) or
            not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*',domain)):
            return False
        expected=f'{name}-{port}.{domain}'
        return host==expected and (origin is None or origin=='https://'+expected)
    def do_GET(self):
        if not self._local():self.send_error(403);return
        if self.path=='/': body=files('geo_intelligence_core').joinpath('playground.html').read_bytes(); mime='text/html; charset=utf-8'
        elif self.path=='/playground.js': body=files('geo_intelligence_core').joinpath('playground.js').read_bytes();mime='text/javascript; charset=utf-8'
        elif self.path=='/api/operations': body=json.dumps({'operations':catalog()},ensure_ascii=False).encode();mime='application/json'
        else:self.send_error(404);return
        self._headers(200,mime,len(body));self.wfile.write(body)
    def do_POST(self):
        if not self._local():self.send_error(403);return
        if self.path!='/api/run':self.send_error(404);return
        start=time.monotonic()
        try:
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('需要 application/json')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=100_000:raise ValueError('请求过大或为空')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict) or set(body)-{'operation','params','live'} or not {'operation','params'}<=set(body) or type(body.get('live',False)) is not bool:raise ValueError('无效请求')
            live=body.get('live',False)
            if live and not LIVE_SLOT.acquire(blocking=False): raise ValueError('已有实时请求正在运行')
            try:
                data=execute(body['operation'],body['params'],live=live)
            finally:
                if live: LIVE_SLOT.release()
            result={'ok':True,'data':data,'source':'public_provider' if live else 'synthetic_offline','elapsed_ms':round((time.monotonic()-start)*1000)};status=200
        except (ValueError,TypeError,KeyError,ValidationError,TypeError,json.JSONDecodeError) as exc:
            result={'ok':False,'error':type(exc).__name__,'message':str(exc)[:300],'elapsed_ms':round((time.monotonic()-start)*1000)};status=400
        except Exception:
            result={'ok':False,'error':'unavailable','message':'执行失败；请检查依赖、超时和本地配额。','elapsed_ms':round((time.monotonic()-start)*1000)};status=503
        content=json.dumps(result,ensure_ascii=False).encode();self._headers(status,'application/json',len(content));self.wfile.write(content)

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'Core playground: http://127.0.0.1:{server.server_port}');server.serve_forever()
if __name__=='__main__':main()
