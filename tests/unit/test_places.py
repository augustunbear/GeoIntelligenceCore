import pytest
from geo_intelligence_core.models.location import Point
from geo_intelligence_core.models.spatial import Region
from geo_intelligence_core.models.places import Place, PlaceQuery, SourceKey
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.places import company_site, normalize_places


def query(rule="point_covers", categories=("food_service", "office")):
    return PlaceQuery(region=Region(id="synthetic", version="v1", method="synthetic", source_ref="synthetic",
                                   geometry={"type": "Polygon", "coordinates": [[(0, 0), (.01, 0), (.01, .01), (0, .01), (0, 0)]]},
                                   boundary_rule=rule), category_ids=categories, mapping_version="osm-v1", boundary_rule=rule)


def place(source, kind, ident, name, point=(.005, .005), category="food_service", evidence=("a",)):
    return Place(source_key=SourceKey(source_id=source, entity_type=kind, entity_id=str(ident)),
                 native_names={"name": name}, point=Point(longitude=point[0], latitude=point[1]),
                 categories=(category,), evidence_ids=evidence)


def test_typed_ids_and_repeated_source_evidence():
    a = place("osm", "node", 7, "A")
    repeated = a.model_copy(update={"evidence_ids": ("b",)})
    way = place("osm", "way", 7, "A")
    found = normalize_places([a, repeated, way], query())
    assert found.status == Status.ok
    assert found.data.retrieved_count == 3 and found.data.unique_count == 2
    assert next(p for p in found.data.places if p.source_key.entity_type == "node").evidence_ids == ("a", "b")


def test_same_address_and_cross_source_remain_distinct():
    records = [place("osm", "node", 1, "A"), place("osm", "node", 2, "B")]
    assert normalize_places(records, query()).data.unique_count == 2
    records.append(place("directory", "record", 3, "A"))
    found = normalize_places(records, query()).data
    assert found.unique_count == 3
    assert found.duplicate_candidates == (("directory:record/3", "osm:node/1"),)


def test_boundary_rule_and_category_filter():
    edge = place("osm", "node", 1, "A", point=(0, .005))
    outside = place("osm", "node", 2, "B", point=(.02, .02))
    assert normalize_places([edge, outside], query()).data.unique_count == 1
    assert normalize_places([edge, outside], query("point_within")).status == Status.no_results


def test_company_site_never_infers_legal_identity_or_workforce():
    office = place("osm", "way", 7, "Acme", category="office")
    site = company_site(office)
    assert site.site_role == "office" and site.legal_entity_ref is None and site.workforce is None
    assert company_site(place("osm", "node", 1, "A")) is None
