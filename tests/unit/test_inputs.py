"""Offline and synthetic E03 input contracts."""
from datetime import datetime, timezone

import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.evidence import Evidence, Quality, Rights, Permission
from geo_intelligence_core.inputs.map_links import parse_map_link
from geo_intelligence_core.inputs.regions import import_region


def test_explicit_openstreetmap_marker_is_lat_lon():
    result = parse_map_link('https://www.openstreetmap.org/?mlat=49.2&mlon=11.5#map=12/49.2/11.5')
    assert result.status == Status.ok
    assert (result.data.longitude, result.data.latitude) == (11.5, 49.2)


@pytest.mark.parametrize('url,status', [
    ('https://www.openstreetmap.org/?mlat=49&mlat=50&mlon=11', Status.invalid_input),
    ('https://www.openstreetmap.org/?mlat=91&mlon=11', Status.invalid_input),
    ('https://www.openstreetmap.org/?mlat=nan&mlon=11', Status.invalid_input),
    ('https://www.openstreetmap.org/?mlat=49&mlon=11#map=10/50/11', Status.invalid_input),
    ('https://www.openstreetmap.org.evil.test/?mlat=49&mlon=11', Status.unsupported),
    ('http://www.openstreetmap.org/?mlat=49&mlon=11', Status.unsupported),
    ('https://osm.org/go/123', Status.unsupported),
    ('https://127.0.0.1/?mlat=49&mlon=11', Status.unsupported),
    ('https://www.openstreetmap.org/?mlat=49&mlon=11&next=https://evil.test', Status.invalid_input),
])
def test_bad_or_unsupported_links(url, status):
    result = parse_map_link(url)
    assert result.status == status
    assert result.data is None


def evidence(*, allowed=True, period='2023'):
    return Evidence(id='ev1', source_id='synthetic', source_type='local_file', source_ref='synthetic-boundary-v1',
                    retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc), reference_period=period,
                    method_version='file-v1', rights=Rights(use=Permission.allowed if allowed else Permission.unknown,
                                                            permitted_purpose='analysis'), quality=Quality(precision='1:10000'))


def document():
    return {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[11, 49], [11.01, 49], [11.01, 49.01], [11, 49.01], [11, 49]]]},
            'properties': {'id': 'synthetic-area', 'version': '2023', 'source_ref': 'synthetic-boundary-v1',
                           'reference_period': '2023', 'crs': 'EPSG:4326', 'scale_denominator': 10000}}


def test_import_region_preserves_provenance_and_boundary_warning():
    result = import_region(document(), evidence())
    assert result.status == Status.ok
    assert result.data.method == 'administrative_import'
    assert result.data.source_ref == 'synthetic-boundary-v1'
    assert result.evidence[0].id == 'ev1'
    assert result.context.effective_conditions['scale_denominator'] == '10000'
    assert result.context.effective_conditions['crs'] == 'EPSG:4326'
    assert result.context.effective_conditions['reference_period'] == '2023'
    assert any(issue.code == 'boundary_precision' for issue in result.issues)


@pytest.mark.parametrize('mutation', ['missing_source', 'wrong_source', 'missing_period', 'wrong_crs', 'missing_scale', 'self_intersection', 'conflicting_id'])
def test_import_rejects_bad_metadata_or_geometry(mutation):
    doc = document()
    if mutation == 'missing_source': doc['properties'].pop('source_ref')
    if mutation == 'wrong_source': doc['properties']['source_ref'] = 'other'
    if mutation == 'missing_period': doc['properties'].pop('reference_period')
    if mutation == 'wrong_crs': doc['properties']['crs'] = 'EPSG:3857'
    if mutation == 'missing_scale': doc['properties'].pop('scale_denominator')
    if mutation == 'conflicting_id': doc['id'] = 'other'
    if mutation == 'self_intersection': doc['geometry']['coordinates'] = [[[11,49],[11.01,49.01],[11.01,49],[11,49.01],[11,49]]]
    assert import_region(doc, evidence()).status == Status.invalid_input


def test_import_requires_explicit_use_rights():
    result = import_region(document(), evidence(allowed=False))
    assert result.status == Status.disabled
    assert result.data is None


def test_import_rejects_mismatched_caller_purpose():
    result = import_region(document(), evidence(), purpose='redistribution')
    assert result.status == Status.disabled
    assert result.data is None


def test_missing_optional_geometry_returns_unavailable(monkeypatch):
    from geo_intelligence_core.inputs import regions
    from geo_intelligence_core.geometry import _GeometryProblem
    def missing():
        raise _GeometryProblem(Status.unavailable, 'geometry_extra_missing')
    monkeypatch.setattr(regions, '_deps', missing)
    result = import_region(document(), evidence())
    assert result.status == Status.unavailable
    assert result.data is None


def test_top_level_offline_input_contract():
    import geo_intelligence_core as core
    assert core.parse_map_link is parse_map_link
    assert core.import_region is import_region


def test_import_rejects_nonlocal_world_spanning_ring():
    doc = document()
    doc['geometry']['coordinates'] = [[[-180,-79],[0,-79],[180,-79],[180,79],[0,79],[-180,79],[-180,-79]]]
    result = import_region(doc, evidence())
    assert result.status in (Status.invalid_input, Status.unsupported)
    assert result.data is None


@pytest.mark.parametrize('url', [
    'https://@www.openstreetmap.org/?mlat=49&mlon=11',
    'https://:@www.openstreetmap.org/?mlat=49&mlon=11',
])
def test_empty_userinfo_is_not_a_supported_map_link(url):
    assert parse_map_link(url).status == Status.unsupported


def test_import_rejects_geometry_level_crs_override():
    doc = document()
    doc['geometry']['crs'] = {'type': 'name', 'properties': {'name': 'EPSG:3857'}}
    assert import_region(doc, evidence()).status == Status.invalid_input


def test_vertex_limit_precedes_geometry_dependency(monkeypatch):
    from geo_intelligence_core.inputs import regions
    doc = document()
    ring = [[11 + i * 0.000001, 49] for i in range(5001)]
    ring.append(ring[0])
    doc['geometry']['coordinates'] = [ring]
    def no_geometry_dependency():
        raise AssertionError('dependency should not be loaded for oversized input')
    monkeypatch.setattr(regions, '_deps', no_geometry_dependency)
    assert import_region(doc, evidence()).status == Status.invalid_input


@pytest.mark.parametrize('placement', ['foreign_member', 'coordinates'])
def test_import_rejects_unknown_nested_geometry_without_recursing(placement):
    doc = document()
    nested = 0
    for _ in range(600):
        nested = [nested]
    if placement == 'foreign_member':
        doc['geometry']['unused'] = nested
    else:
        doc['geometry']['coordinates'] = nested
    result = import_region(doc, evidence())
    assert result.status == Status.invalid_input
    assert result.data is None
