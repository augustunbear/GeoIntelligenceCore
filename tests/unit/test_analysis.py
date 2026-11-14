import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from geo_intelligence_core.analysis import analyze
from geo_intelligence_core.models.configuration import AnalyzeRequest, TopicSelection, Template
from geo_intelligence_core.models.location import Location, Point, Confirmation
from geo_intelligence_core.models.spatial import Region
from geo_intelligence_core.models.places import PlaceSet
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.policy import UsagePolicy
from geo_intelligence_core.ports import ProviderRegistry


def location(id='loc'):
    return Location(id=id, version=1, point=Point(longitude=11.1, latitude=48.1), confirmation=Confirmation(method='manual', at=datetime(2026, 1, 1, tzinfo=timezone.utc), evidence_ids=['synthetic']))


def region():
    return Region(id='r', version='1', method='fixture', geometry={'type': 'Polygon', 'coordinates': [[[11,48], [12,48], [12,49], [11,49], [11,48]]]})


class Places:
    def __init__(self): self.calls = 0; self.queries = []
    async def search(self, query, context):
        self.calls += 1; self.queries.append(query)
        return Result(status='ok', data=PlaceSet(places=[], retrieved_count=0, unique_count=0), context=context)


class Budget:
    def __init__(self, allow=True): self.calls = 0; self.allow = allow
    async def reserve(self, provider_id, calls, estimated_cost):
        self.calls += calls
        return self.allow
    async def record(self, provider_id, actual_cost): pass


def run(request, registry, allowed=('places',), budget=None, template=None):
    return asyncio.run(analyze(request, registry, UsagePolicy(allowed_capabilities=allowed, max_calls_per_run=2), budget or Budget(), template=template))


def test_surroundings_selected_population_is_partial_and_null():
    provider = Places(); registry = ProviderRegistry(); registry.register('places', provider)
    req = AnalyzeRequest(locations=[location()], regions=[region()], topics=[TopicSelection(id='places')], explicit_parameters={'category_ids': ['restaurant']})
    ok = run(req, registry)
    assert ok.status == Status.ok and provider.calls == 1
    selected = req.model_copy(update={'topics': [TopicSelection(id='places'), TopicSelection(id='population_reference')]})
    result = run(selected, registry)
    assert result.status == Status.partial
    assert result.data.topic_results['population_reference'].data is None
    assert result.data.topic_results['population_reference'].status == Status.disabled


def test_required_preflight_zero_network_and_budget():
    provider = Places(); registry = ProviderRegistry(); registry.register('places', provider, configured=False)
    budget = Budget()
    req = AnalyzeRequest(locations=[location()], regions=[region()], topics=[TopicSelection(id='places')])
    result = run(req, registry, budget=budget, template=Template(id='venue-discovery', version='1', required_topics=['places']))
    assert result.status == Status.unconfigured and result.data is None
    assert provider.calls == budget.calls == 0


def test_template_upgrade_does_not_change_v1_request():
    provider = Places(); registry = ProviderRegistry(); registry.register('places', provider)
    req = AnalyzeRequest(locations=[location()], regions=[region()], topics=[TopicSelection(id='places')], template_ref='venue-discovery@1', explicit_parameters={'category_ids': ['cafe']})
    v1 = Template(id='venue-discovery', version='1', defaults={'language': 'de'}, required_topics=['places'])
    v2 = Template(id='venue-discovery', version='2', defaults={'language': 'en'}, required_topics=['places'])
    assert run(req, registry, template=v1).status == Status.ok
    assert run(req, registry, template=v2).status == Status.invalid_input


def test_explicit_region_required_and_budget_rejection():
    provider = Places(); registry = ProviderRegistry(); registry.register('places', provider)
    req = AnalyzeRequest(locations=[location()], topics=[TopicSelection(id='places')], explicit_parameters={'category_ids': ['restaurant']})
    assert run(req, registry).status == Status.invalid_input
    assert provider.calls == 0
    req = req.model_copy(update={'regions': [region()]})
    result = run(req, registry, budget=Budget(allow=False))
    assert result.status == Status.unavailable and provider.calls == 0


def test_explicit_radius_generates_tagged_local_circle_without_default_radius():
    provider = Places(); registry = ProviderRegistry(); registry.register('places', provider)
    req = AnalyzeRequest(locations=[location()], topics=[TopicSelection(id='places')], explicit_parameters={'category_ids': ['restaurant'], 'radius_m': 200})
    policy = UsagePolicy(allowed_capabilities=['places'], max_calls_per_run=1, max_area_m2=1_000_000.0, max_geometry_vertices=100)
    result = asyncio.run(analyze(req, registry, policy, Budget()))
    assert result.status == Status.ok
    assert provider.queries[0].region.method == 'geodesic_straight_line_circle'
    assert result.context.effective_conditions['config.radius_m'] == '200'


def test_geometry_intersects_adapter_failure_keeps_topic_status():
    class Unsupported:
        calls = 0
        async def search(self, query, context):
            self.calls += 1
            return Result(status='unsupported', data=None, context=context, issues=[])
    provider = Unsupported(); registry = ProviderRegistry(); registry.register('places', provider)
    crossing = region().model_copy(update={'boundary_rule': 'geometry_intersects'})
    req = AnalyzeRequest(locations=[location()], regions=[crossing], topics=[TopicSelection(id='places')], explicit_parameters={'category_ids': ['restaurant']})
    result = run(req, registry)
    assert result.status == Status.unsupported and provider.calls == 1
    assert result.data.topic_results['places'].data is None


def test_topic_preserves_provider_instance_without_overwriting_request_scope():
    class InstancePlaces:
        async def search(self, query, context):
            provider_context = context.model_copy(update={
                'request_id': 'wrong-request', 'scope_token': 'wrong-scope',
                'effective_conditions': {**context.effective_conditions,
                                         'provider_instance': 'overpass-demo',
                                         'provider_endpoint': 'https://example.org/api',
                                         'provider_http_method': 'POST'},
            })
            return Result(status='ok', data=PlaceSet(places=[], retrieved_count=0, unique_count=0),
                          context=provider_context)

    registry = ProviderRegistry()
    registry.register('places', InstancePlaces())
    req = AnalyzeRequest(locations=[location()], regions=[region()], topics=[TopicSelection(id='places')],
                         explicit_parameters={'category_ids': ['restaurant']},
                         request_id='correct-request', scope_token='correct-scope')
    result = run(req, registry)
    assert result.status == Status.ok
    topic_context = result.data.topic_results['places'].context
    assert topic_context.effective_conditions['provider_instance'] == 'overpass-demo'
    assert topic_context.effective_conditions['provider_endpoint'] == 'https://example.org/api'
    assert topic_context.effective_conditions['provider_http_method'] == 'POST'
    assert topic_context.request_id == 'correct-request'
    assert topic_context.scope_token == 'correct-scope'
    assert 'provider_instance' not in result.context.effective_conditions
