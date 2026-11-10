"""Offline, provenance-checked local GeoJSON administrative boundary import."""
from uuid import uuid4

from ..geometry import _GeometryProblem, _checked, _coordinates, _deps
from ..models.common import Issue, Result, Status
from ..models.evidence import Evidence
from ..models.requests import RequestContext
from ..models.spatial import GeometryLimits, Region

# Conservative fixed ceiling; no unbounded GEOS processing through this entry point.
_LIMITS = GeometryLimits(max_area_m2=1e12, max_vertices=5000)


def _result(status, region=None, evidence=None, code=None, warning=False, conditions=None):
    issues = (Issue(code=code, message_key=f"region_import.{code}"),) if code else ()
    if warning:
        issues += (Issue(code="boundary_precision", message_key="region_import.boundary_precision"),)
    return Result[Region](status=status, data=region, issues=issues,
                          evidence=(evidence,) if evidence is not None else (),
                          context=RequestContext(request_id=str(uuid4()), method_version="region-import-v1",
                                                 effective_conditions=conditions or {}))


def import_region(document: dict, evidence: Evidence, *, purpose: str = "analysis") -> Result[Region]:
    """Import one EPSG:4326 GeoJSON Feature, not a URL or a FeatureCollection.

    Only use is granted by this operation. Retain, cache, display and export
    remain subject to the evidence's separate rights gates.
    """
    try:
        evidence = Evidence.model_validate(evidence)
    except (ValueError, TypeError):
        return _result(Status.invalid_input, code="invalid_evidence")
    if not evidence.rights.allows("use", purpose):
        return _result(Status.disabled, evidence=evidence, code="use_rights_required")
    try:
        if not isinstance(document, dict) or document.get("type") != "Feature" or document.get("crs") is not None:
            raise ValueError("feature_required")
        props = document.get("properties")
        if not isinstance(props, dict):
            raise ValueError("metadata_required")
        for key in ("id", "version", "source_ref", "reference_period", "crs"):
            if not isinstance(props.get(key), str) or not props[key].strip():
                raise ValueError("metadata_required")
        if ("id" in document and document["id"] != props["id"]):
            raise ValueError("ambiguous_feature_id")
        if props["source_ref"] != evidence.source_ref or props["reference_period"] != evidence.reference_period:
            raise ValueError("provenance_mismatch")
        if props["crs"] != "EPSG:4326":
            raise ValueError("unsupported_crs")
        scale = props.get("scale_denominator")
        if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not 0 < scale <= 1e9:
            raise ValueError("scale_required")
        geometry = document.get("geometry")
        # Reject unrecognized nested data before Region recursively freezes it.
        # A GeoJSON geometry for this importer has exactly these two fields.
        if not isinstance(geometry, dict) or set(geometry) != {"type", "coordinates"}:
            raise ValueError("geometry_fields_invalid")
        vertex_count = _coordinates(geometry)
        if vertex_count > _LIMITS.max_vertices:
            raise _GeometryProblem(Status.invalid_input, "vertex_limit")
        region = Region(id=props["id"], version=props["version"], geometry=geometry,
                        method="administrative_import", source_ref=evidence.source_ref)
        # Geodesic signed areas can cancel for world-spanning rings. Restrict
        # imports to local extents before using area as a resource bound.
        polygons = (region.geometry["coordinates"],) if region.geometry["type"] == "Polygon" else region.geometry["coordinates"]
        points = [point for polygon in polygons for ring in polygon for point in ring]
        longitudes = [point[0] for point in points]
        latitudes = [point[1] for point in points]
        if max(longitudes) - min(longitudes) > 20 or max(latitudes) - min(latitudes) > 20:
            raise _GeometryProblem(Status.unsupported, "outside_local_extent")
        geod, _, _, shape, orient_polygons, _ = _deps()
        _checked(region, _LIMITS, geod, shape, orient_polygons)
        return _result(Status.ok, region=region, evidence=evidence, warning=True, conditions={
            "crs": props["crs"], "reference_period": props["reference_period"],
            "scale_denominator": str(scale),
        })
    except _GeometryProblem as exc:
        return _result(exc.status, evidence=evidence, code=exc.code)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        return _result(Status.invalid_input, evidence=evidence, code="invalid_region")
