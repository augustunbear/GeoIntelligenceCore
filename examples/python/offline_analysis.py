"""Three synthetic template runs without credentials or external requests."""
import asyncio
import json
import os
import socket
from datetime import datetime, timezone
from decimal import Decimal

from geo_intelligence_core import (
    AnalyzeRequest, ConfirmRequest, Confirmation, Evidence, PlaceSet, Point,
    ProviderRegistry, Quality, Region, Result, Rights, Snapshot, Status,
    TopicSelection, UsagePolicy, analyze, confirm_location, export_result, snapshot,
)


class SyntheticPlaces:
    async def search(self, query, context):
        assert query.region.id.startswith('synthetic-')
        rights = Rights(use='allowed', retain='allowed', display='allowed',
                        export='allowed', permitted_purpose='example',
                        attribution='Synthetic fixture; no real source')
        evidence = Evidence(id='fixture-place', source_id='synthetic',
                            source_type='fixture', source_ref='offline example',
                            retrieved_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
                            method_version='fixture-v1', rights=rights, quality=Quality())
        return Result(status=Status.ok, data=PlaceSet(places=[], retrieved_count=0,
                       unique_count=0), evidence=[evidence], context=context)


class LocalBudget:
    async def reserve(self, provider_id, calls, estimated_cost):
        assert calls == 1 and estimated_cost == Decimal(0)
        return True

    async def record(self, provider_id, actual_cost):
        assert actual_cost == Decimal(0)


def location(identity, longitude):
    evidence = Evidence(id=f'manual-{identity}', source_id='synthetic',
                        source_type='manual', source_ref='offline example',
                        retrieved_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
                        method_version='manual-v1', rights=Rights(), quality=Quality())
    result = confirm_location(ConfirmRequest(
        location_id=identity, point=Point(longitude=longitude, latitude=48),
        confirmation=Confirmation(method='manual', at=evidence.retrieved_at,
                                  evidence_ids=[evidence.id]), evidence=[evidence]))
    assert result.status == Status.ok
    return result.data


def region(identity, longitude):
    return Region(id=f'synthetic-{identity}', version='1', method='fixture',
                  geometry={'type': 'Polygon', 'coordinates': [[
                      [longitude - .01, 47.99], [longitude + .01, 47.99],
                      [longitude + .01, 48.01], [longitude - .01, 48.01],
                      [longitude - .01, 47.99]]]})


async def main():
    if os.getenv('GEO_CORE_DISABLE_NETWORK') == '1':
        def blocked(*args, **kwargs):
            raise AssertionError('an offline consumer attempted network access')
        socket.socket.connect = blocked
        socket.create_connection = blocked

    first, second = location('a', 11), location('b', 12)
    registry = ProviderRegistry()
    registry.register('places', SyntheticPlaces())
    policy = UsagePolicy(allowed_capabilities=['places'], max_calls_per_run=3)
    common = {'topics': [TopicSelection(id='places')],
              'explicit_parameters': {'category_ids': ['restaurant']},
              'profile_ref': 'food-service@1'}

    surrounding = await analyze(AnalyzeRequest(
        locations=[first], regions=[region('a', 11)],
        topics=[*common['topics'], TopicSelection(id='population_reference')],
        explicit_parameters=common['explicit_parameters'], profile_ref=common['profile_ref'],
        template_ref='surroundings@1'), registry, policy, LocalBudget())
    assert surrounding.status == Status.partial
    assert surrounding.data.topic_results['population_reference'].data is None
    print(f'surroundings: {surrounding.status}')

    venue = await analyze(AnalyzeRequest(
        **common, locations=[first], regions=[region('a', 11)],
        template_ref='venue-discovery@1'), registry, policy, LocalBudget())
    assert venue.status == Status.ok
    print(f'venue-discovery: {venue.status}')

    comparison = await analyze(AnalyzeRequest(
        **common, locations=[first, second], regions=[region('a', 11), region('b', 12)],
        template_ref='location-comparison@1'), registry, policy, LocalBudget())
    assert comparison.data is not None and comparison.data.comparison is not None
    print(f'location-comparison: {comparison.status}')

    retained = snapshot(venue.data, purpose='example')
    assert retained.data is not None
    restored = Snapshot.model_validate_json(retained.data.model_dump_json())
    exported = export_result(restored, format='json', language='en', purpose='example')
    assert exported.data is not None
    assert json.loads(exported.data)['schema_version'] == '1.0'
    print('export roundtrip: ok')


if __name__ == '__main__':
    asyncio.run(main())
