import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.configuration import AnalyzeRequest, EffectiveConfig, Profile, Template, TopicSelection
from geo_intelligence_core.models.analysis import Analysis, Metric
from geo_intelligence_core.models.location import Location, Point
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.models.evidence import Rights, Permission


def test_roundtrip_strict_types_and_zero():
    result = Result[Metric](status=Status.ok, data=Metric(value=0, unit='count', nature='measured', evidence_ids=['e1']), context=RequestContext(request_id='r'))
    restored = Result[Metric].model_validate_json(result.model_dump_json())
    assert restored.data.value == 0
    assert '"value":0' in result.model_dump_json()
    assert '"value":null' in Metric(value=None, unit='count', nature='unverified').model_dump_json()
    with pytest.raises(ValidationError):
        Metric(value='0', unit='count', nature='measured')
    with pytest.raises(ValidationError):
        Metric(value=True, unit='count', nature='measured')
    with pytest.raises(ValidationError):
        Profile(id='p', version='1', unknown=1)
    with pytest.raises(ValidationError):
        Profile(id='p', version='1', defaults={'radius_m': float('nan')})


def test_rights_unknown_is_not_permission():
    rights = Rights()
    assert not rights.allows('export', 'commercial')
    assert not Rights(export=Permission.allowed, permitted_purpose='research').allows('export', 'commercial')
    assert Rights(export=Permission.allowed, permitted_purpose='research').allows('export', 'research')


def test_exported_schemas_match_models():
    models = {'location': Location, 'result': Result[Metric], 'analysis': Analysis, 'profile': Profile, 'template': Template}
    for name, model in models.items():
        stored = json.loads((Path(__file__).parents[2] / 'schemas' / 'v1' / f'{name}.json').read_text())
        assert stored == model.model_json_schema()
