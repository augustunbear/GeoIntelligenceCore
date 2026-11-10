"""Additive COMPANY schema and immutable result roundtrip."""
import json
from pathlib import Path

from geo_intelligence_core.inputs.company import import_company
from geo_intelligence_core.models.common import Result
from geo_intelligence_core.models.company import ImportedCompanySite


def test_company_result_schema_matches_and_roundtrips(synthetic_evidence):
    contract = Result[tuple[ImportedCompanySite, ...]]
    schema = Path(__file__).resolve().parents[2] / 'schemas/v1/company-import-result.json'
    assert json.loads(schema.read_text()) == contract.model_json_schema()
    ev = synthetic_evidence.model_copy(update={'rights': synthetic_evidence.rights.model_copy(
        update={'use': 'allowed', 'permitted_purpose': 'synthetic'})})
    result = import_company([dict(id='site', source_id=ev.source_id, source_ref=ev.source_ref,
        site_role='unknown', point={'longitude': 11, 'latitude': 49})], ev, purpose='synthetic')
    restored = contract.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.data[0].workforce is None
