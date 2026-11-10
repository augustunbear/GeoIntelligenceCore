"""Additive history schemas, without changing existing V1 schema files."""
import json
from pathlib import Path

from geo_intelligence_core.models.change import Change, WatchSpec
from geo_intelligence_core.models.common import Result
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.places import Place, SourceKey
from geo_intelligence_core.models.requests import RequestContext


def test_history_schemas_match_models():
    root = Path(__file__).parents[2] / 'schemas' / 'v1'
    for name, model in [('change', Change), ('history-result', Result[tuple[Change, ...]]), ('watch-spec', WatchSpec)]:
        assert json.loads((root / f'{name}.json').read_text()) == model.model_json_schema()


def test_history_result_roundtrips_json_arrays_without_serializer_warnings():
    place = Place(source_key=SourceKey(source_id='synthetic', entity_type='site', entity_id='1'),
                  point=Point(longitude=11, latitude=49), evidence_ids=('e1',))
    change = Change(kind='source_record', change='source_record_missing', entity_ref='places/synthetic:site:1',
                    before=place, after=None, evidence_ids=('e1',))
    result = Result[tuple[Change, ...]](status='ok', data=(change,), context=RequestContext(request_id='history'))
    raw = result.model_dump_json(warnings='error')
    assert isinstance(json.loads(raw)['data'], list)
    assert Result[tuple[Change, ...]].model_validate_json(raw) == result
