import pytest

from geo_intelligence_core.models.location import Address, Point
from geo_intelligence_core.models.places import Place, SourceKey


def place(source='a', ident='1', name='Café Straße', lon=11.0, lat=49.0, address=True):
    return Place(source_key=SourceKey(source_id=source, entity_type='node', entity_id=ident),
                 native_names={'name': name}, point=Point(longitude=lon, latitude=lat),
                 categories=('restaurant',), address=Address(street='Teststraße', house_number='1') if address else None)


def test_unicode_matching_preserves_originals_and_local_address_semantics():
    from geo_intelligence_core.place_quality import normalize_comparison_text
    assert normalize_comparison_text(' Café STRAẞE! ') == 'cafe strasse'
    assert normalize_comparison_text('茶 餐厅') == '茶 餐厅'
    assert normalize_comparison_text('Jl. No 5') == 'jl no 5'
    assert normalize_comparison_text('') is None
    p = place()
    normalize_comparison_text(p.native_names['name'])
    assert p.native_names['name'] == 'Café Straße'


def test_candidates_are_explainable_cross_source_and_not_merged():
    from geo_intelligence_core.place_quality import find_duplicate_candidates
    records = [place(), place('b', name='Cafe Strasse', lon=11.0001), place('a', '2'),
               place('c', name='Different Shop')]
    found = find_duplicate_candidates(records)
    pairs = {(c.left.source_id, c.left.entity_id, c.right.source_id, c.right.entity_id) for c in found}
    assert ('a', '1', 'b', '1') in pairs
    assert all(c.left.source_id != c.right.source_id for c in found)
    assert all('c' not in (c.left.source_id, c.right.source_id) for c in found)
    candidate = next(c for c in found if c.left.entity_id == '1')
    assert candidate.distance_m < 25 and 'exact_normalized_name' in candidate.reasons
    assert candidate.method_version == 'candidate-match-v1'
    assert len(records) == 4 and records[0].native_names['name'] == 'Café Straße'


def test_missing_names_and_far_apart_same_names_are_not_matches():
    from geo_intelligence_core.place_quality import find_duplicate_candidates
    assert find_duplicate_candidates([place(name=''), place('b', name='')]) == ()
    assert find_duplicate_candidates([place(), place('b', lon=12)]) == ()


def test_quality_has_explicit_denominators_unknown_empty_and_no_coverage_claim():
    from geo_intelligence_core.place_quality import summarize_place_quality
    empty = summarize_place_quality([])
    assert empty.record_completeness_percent is None and empty.field_completeness_percent is None
    p = place()
    report = summarize_place_quality([p, p, place('b', name='', address=False)])
    assert report.total_records == 3 and report.duplicate_source_identities == 1
    assert report.with_name == 2 and report.with_address == 2
    assert report.complete_records == 2 and report.record_completeness_percent == 66.67
    assert report.coverage == 'unknown'
    whitespace = place().model_copy(update={'address': Address(street=' ')})
    assert summarize_place_quality([whitespace]).with_address == 0


def test_matching_has_validated_work_limits_and_stable_order():
    from geo_intelligence_core.place_quality import find_duplicate_candidates
    records = [place('b'), place('a'), place('c')]
    assert find_duplicate_candidates(records) == find_duplicate_candidates(list(reversed(records)))
    for kwargs in ({'max_records': 2}, {'threshold': float('nan')}, {'threshold': 1.1}):
        with pytest.raises(ValueError):
            find_duplicate_candidates(records, **kwargs)


def test_incomplete_repeated_identity_cannot_suppress_matching_observation():
    from geo_intelligence_core.place_quality import find_duplicate_candidates
    assert find_duplicate_candidates([place(), place('b')]) == find_duplicate_candidates([place(name=''), place('b'), place()])
