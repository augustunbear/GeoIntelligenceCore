import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from geo_intelligence_core.analysis import analyze, load_profile, load_template
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.configuration import AnalyzeRequest, TopicSelection, TimeCondition
from geo_intelligence_core.models.location import Location, Point, Confirmation
from geo_intelligence_core.models.places import PlaceSet
from geo_intelligence_core.models.spatial import Region
from geo_intelligence_core.models.policy import UsagePolicy
from geo_intelligence_core.ports import ProviderRegistry

ROOT = Path(__file__).parents[1] / 'fixtures' / 'scenarios'


class Places:
    def __init__(self): self.calls = 0; self.queries = []
    async def search(self, query, context):
        self.calls += 1; self.queries.append(query)
        return Result(status='ok', data=PlaceSet(places=[], retrieved_count=0, unique_count=0), context=context)


class Budget:
    async def reserve(self, provider_id, calls, estimated_cost): return True
    async def record(self, provider_id, actual_cost): pass


def test_packaged_resources_and_profile_semantics():
    profile = load_profile('food-service@1')
    assert set(profile.category_ids) == {'restaurant', 'cafe', 'bar', 'fast_food'}
    assert not ({'takeaway', 'population_reference'} & set(profile.category_ids))
    for name in ('surroundings', 'venue-discovery', 'location-comparison'):
        assert load_template(f'{name}@1').profile_ref == 'food-service@1'


def test_three_industries_share_provider_port_and_static_time_is_unverified():
    for name in ('food-service', 'retail', 'education'):
        scenario = json.loads((ROOT / f'{name}.json').read_text())
        provider = Places(); registry = ProviderRegistry(); registry.register('places', provider)
        location = Location(id=scenario['location_id'], version=1, point=Point(longitude=11.1, latitude=48.1), confirmation=Confirmation(method='manual', at=datetime(2026,1,1,tzinfo=timezone.utc), evidence_ids=['synthetic']))
        region = Region(id='explicit', version='1', method='synthetic', geometry={'type':'Polygon','coordinates':[[[11,48],[12,48],[12,49],[11,49],[11,48]]]})
        req = AnalyzeRequest(locations=[location], regions=[region], topics=[TopicSelection(id='places')], explicit_parameters={'category_ids': scenario['category_ids']}, time=TimeCondition(kind='descriptive', label=scenario['time_label']))
        result = asyncio.run(analyze(req, registry, UsagePolicy(allowed_capabilities=['places'], max_calls_per_run=1), Budget()))
        assert result.status == Status.ok and provider.calls == 1
        assert provider.queries[0].category_ids == tuple(scenario['category_ids'])
        assert any(i.code == 'static_places_time_unverified' for i in result.data.topic_results['places'].issues)
        assert result.data.topic_results['places'].data.unique_count == 0
