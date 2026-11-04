"""Opt-in Overpass place discovery through the P04 bounded HTTP gateway."""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.resources import files
import json
import re

from geo_intelligence_core.geometry import _coordinates, _deps
from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.evidence import Evidence, Quality, Rights
from geo_intelligence_core.models.location import Address, Point
from geo_intelligence_core.models.places import Place, PlaceQuery, PlaceSet, SourceKey
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.places import normalize_places


def _mapping():
    return json.loads(files("geo_intelligence_core").joinpath("data/mappings/osm-v1.json").read_text())


def _selectors(category_ids):
    tags = _mapping()["tags"]
    selectors = set()
    for category in category_ids:
        for key, values in tags.items():
            for value, mapped in values.items():
                if mapped == category:
                    selectors.add((key, value))
    return sorted(selectors)


def _query(selectors, bbox, timeout, limit, maxsize):
    south, west, north, east = bbox
    coordinate = ",".join(f"{x:.7f}" for x in (south, west, north, east))
    def escape(value):
        return re.escape(value).replace('\\_', '_')
    clauses = []
    for kind in ("node", "way", "relation"):
        for key, value in selectors:
            predicate = f'["{escape(key)}"]' if value == "*" else f'["{escape(key)}"="{escape(value)}"]'
            clauses.append(f"{kind}{predicate}({coordinate});")
    return f'[out:json][timeout:{timeout}][maxsize:{maxsize}];(' + ''.join(clauses) + f');out body center qt {limit};'


def _place(element, mapping, evidence_id):
    typ, ident = element["type"], element["id"]
    if typ not in ("node", "way", "relation") or isinstance(ident, bool) or not isinstance(ident, int) or ident < 0:
        raise ValueError("invalid OSM identity")
    tags = element.get("tags") or {}
    if not isinstance(tags, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in tags.items()):
        raise ValueError("invalid tags")
    center = element if typ == "node" else element.get("center", {})
    point = Point(latitude=center["lat"], longitude=center["lon"])
    categories = sorted({mapped for key, values in mapping["tags"].items()
                         if (value := tags.get(key)) and (mapped := values.get(value, values.get("*")))})
    names = {key: value for key, value in tags.items() if key == "name" or key.startswith("name:")}
    contacts = {key: value for key, value in tags.items() if key in ("website", "contact:website", "phone", "contact:phone", "email", "contact:email")}
    address_keys = {"addr:country": "country_code", "addr:postcode": "postcode", "addr:city": "locality",
                    "addr:street": "street", "addr:housenumber": "house_number"}
    address = {field: tags[key] for key, field in address_keys.items() if key in tags}
    geometry = None
    if typ != "node" and isinstance(element.get("geometry"), (list, tuple)):
        coords = [[p["lon"], p["lat"]] for p in element["geometry"]]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            geometry = {"type": "Polygon", "coordinates": [coords]}
        elif len(coords) >= 2:
            geometry = {"type": "LineString", "coordinates": coords}
    return Place(source_key=SourceKey(source_id="osm", entity_type=typ, entity_id=str(ident)),
                 native_names=names, point=point, point_role="observed" if typ == "node" else "representative",
                 geometry=geometry, address=Address(**address) if address else None,
                 categories=tuple(categories), raw_tags=tags, hours_raw=tags.get("opening_hours"),
                 contacts=contacts, evidence_ids=(evidence_id,))


class OverpassPlaceProvider:
    def __init__(self, gateway, *, provider_id="overpass", clock=lambda: datetime.now(timezone.utc)):
        self.gateway, self.provider_id, self.clock = gateway, provider_id, clock

    async def search(self, request: PlaceQuery, context: RequestContext) -> Result[PlaceSet]:
        def fail(status, code):
            return Result[PlaceSet](status=status, data=None,
                                    issues=(Issue(code=code, message_key=f"overpass.{code}"),), context=context)
        try:
            request = PlaceQuery.model_validate(request)
            policy = self.gateway.policy
            cfg = self.gateway.providers.get(self.provider_id)
            if cfg is None or not cfg.endpoint:
                return fail(Status.unconfigured, "unconfigured")
            if cfg.capability_flags.get("places") is False or "places" not in policy.allowed_capabilities:
                return fail(Status.disabled, "disabled")
            if not all((policy.max_area_m2, policy.max_geometry_vertices, policy.max_items,
                        policy.max_response_bytes, policy.deadline_s)):
                return fail(Status.unconfigured, "missing_hard_limit")
            if request.mapping_version != "osm-v1" or request.boundary_rule != request.region.boundary_rule:
                return fail(Status.invalid_input, "mapping_or_boundary")
            selectors = _selectors(request.category_ids)
            known = set(json.loads(files("geo_intelligence_core").joinpath("data/categories/v1.json").read_text())["categories"])
            if not request.category_ids or not set(request.category_ids).issubset(known) or not selectors or len(selectors) > 50:
                return fail(Status.invalid_input, "unknown_category")
            geod, _, _, shape, orient, _ = _deps()
            if _coordinates(request.region.geometry) > policy.max_geometry_vertices:
                return fail(Status.invalid_input, "vertex_limit")
            polygon = shape(request.region.geometry)
            if not polygon.is_valid or polygon.is_empty:
                return fail(Status.invalid_input, "invalid_region")
            if abs(geod.geometry_area_perimeter(orient(polygon))[0]) > policy.max_area_m2:
                return fail(Status.invalid_input, "area_limit")
            west, south, east, north = polygon.bounds
            if not (-180 <= west < east <= 180 and -80 <= south < north <= 80 and east - west < 180):
                return fail(Status.unsupported, "outside_local_extent")
            timeout = max(1, min(25, int(policy.deadline_s)))
            query = _query(selectors, (south, west, north, east), timeout, policy.max_items,
                           policy.max_response_bytes)
            if len(query) > 8192:
                return fail(Status.invalid_input, "query_limit")
        except ImportError:
            return fail(Status.unavailable, "geometry_extra_missing")
        except (ValueError, TypeError, KeyError, IndexError):
            return fail(Status.invalid_input, "invalid_region")
        response = await self.gateway.request(self.provider_id, "GET", "/api/interpreter", {"data": query}, context)
        if response.status != Status.ok or response.data is None:
            return Result[PlaceSet](status=response.status, data=None, issues=response.issues,
                                    evidence=response.evidence, context=context)
        payload = response.data
        raw = payload.get("elements")
        if not isinstance(raw, (list, tuple)):
            return fail(Status.unavailable, "invalid_response")
        remark = payload.get("remark")
        if remark is not None and not isinstance(remark, str):
            return fail(Status.unavailable, "invalid_response")
        evidence = Evidence(id=f"osm-overpass:{context.request_id}", source_id="osm", source_type="provider",
                            source_ref=cfg.endpoint, retrieved_at=self.clock(), method_version="osm-v1",
                            rights=Rights(attribution="© OpenStreetMap contributors", license_url="https://www.openstreetmap.org/copyright",
                                          source_url=cfg.endpoint),
                            quality=Quality(coverage="unknown", verification="unverified"))
        records = []
        invalid = False
        mapping = _mapping()
        for element in raw[:policy.max_items]:
            try:
                records.append(_place(element, mapping, evidence.id))
            except (TypeError, KeyError, ValueError, IndexError):
                invalid = True
        normalized = normalize_places(records, request, context=context)
        if normalized.status not in (Status.ok, Status.no_results):
            return normalized
        issues = list(normalized.issues)
        if remark:
            issues.append(Issue(code="upstream_remark", message_key="overpass.upstream_remark"))
        if invalid or len(raw) >= policy.max_items:
            issues.append(Issue(code="records_truncated_or_invalid", message_key="overpass.records_truncated_or_invalid"))
        if issues and not normalized.data.places:
            return Result[PlaceSet](status=Status.unavailable, data=None, issues=tuple(issues), evidence=(evidence,), context=context)
        status = Status.partial if issues else normalized.status
        return Result[PlaceSet](status=status, data=normalized.data, issues=tuple(issues),
                                evidence=(evidence,), context=context)
