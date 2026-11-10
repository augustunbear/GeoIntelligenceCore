"""Run with the geometry extra; synthetic records, no provider/network required."""
from geo_intelligence_core import (Place, Point, SourceKey, find_duplicate_candidates,
                                   summarize_place_quality)

records = [
    Place(source_key=SourceKey(source_id='synthetic-a', entity_type='node', entity_id='1'),
          native_names={'name': 'Café Straße'}, categories=('restaurant',),
          point=Point(longitude=11.0, latitude=49.0)),
    Place(source_key=SourceKey(source_id='synthetic-b', entity_type='site', entity_id='2'),
          native_names={'name': 'Cafe Strasse'}, categories=('restaurant',),
          point=Point(longitude=11.0001, latitude=49.0)),
]
if __name__ == '__main__':
    print(summarize_place_quality(records).model_dump_json(indent=2))
    for candidate in find_duplicate_candidates(records):
        print(candidate.model_dump_json(indent=2))
