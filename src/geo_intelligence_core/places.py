"""Offline, source-key-preserving place normalization."""
from __future__ import annotations

import json
from uuid import uuid4

from .geometry import point_in_region
from .models.common import Issue, Result, Status
from .models.places import CompanySite, Place, PlaceQuery, PlaceSet
from .models.requests import RequestContext


def normalize_places(records: list[Place], query: PlaceQuery, *,
                     context: RequestContext | None = None) -> Result[PlaceSet]:
    context = context or RequestContext(request_id=str(uuid4()), method_version="places-v1")
    def fail(code: str, status: Status = Status.invalid_input):
        return Result[PlaceSet](status=status, data=None,
                                issues=(Issue(code=code, message_key=f"places.{code}"),), context=context)
    try:
        query = PlaceQuery.model_validate(query)
        if not query.category_ids or query.boundary_rule != query.region.boundary_rule:
            return fail("invalid_query")
        region = query.region
        filtered: dict[tuple[str, str, str], Place] = {}
        for record in records:
            place = Place.model_validate(record)
            if not set(place.categories).intersection(query.category_ids):
                continue
            if query.boundary_rule == "geometry_intersects":
                from .geometry import _deps, _coordinates
                _, _, _, shape, _, _ = _deps()
                _coordinates(region.geometry)
                if not shape(region.geometry).is_valid:
                    return fail("invalid_region")
                inside = shape(region.geometry).intersects(shape(place.geometry)) if place.geometry else point_in_region(place.point, region)
            else:
                inside = point_in_region(place.point, region)
            if not inside:
                continue
            key = (place.source_key.source_id, place.source_key.entity_type, place.source_key.entity_id)
            prior = filtered.get(key)
            if prior is None:
                filtered[key] = place
            else:
                # A repeated source entity is one place; retain all evidence without
                # treating coincident but separately identified businesses as duplicates.
                chosen = min((prior, place), key=lambda item: json.dumps(item.model_dump(mode="json"), sort_keys=True))
                filtered[key] = chosen.model_copy(update={"evidence_ids": tuple(sorted(set((*prior.evidence_ids, *place.evidence_ids))))})
        places = tuple(filtered[key] for key in sorted(filtered))
        candidates = []
        for i, left in enumerate(places):
            for right in places[i + 1:]:
                if left.source_key.source_id == right.source_key.source_id:
                    continue
                if left.point != right.point or not set(left.categories).intersection(right.categories):
                    continue
                left_name = left.native_names.get("name", "").strip().casefold()
                right_name = right.native_names.get("name", "").strip().casefold()
                if left_name and left_name == right_name:
                    label = lambda p: f"{p.source_key.source_id}:{p.source_key.entity_type}/{p.source_key.entity_id}"
                    candidates.append((label(left), label(right)))
        return Result[PlaceSet](status=Status.ok if places else Status.no_results,
                                data=PlaceSet(places=places, retrieved_count=len(records),
                                              unique_count=len(places), coverage="unknown",
                                              duplicate_candidates=tuple(candidates)), context=context)
    except (ValueError, TypeError, KeyError, ImportError) as exc:
        return fail("geometry_unavailable" if isinstance(exc, ImportError) else "invalid_record",
                    Status.unavailable if isinstance(exc, ImportError) else Status.invalid_input)


def company_site(place: Place) -> CompanySite | None:
    """An office POI represents a site, never proof of a legal entity or workforce."""
    if "office" not in place.categories:
        return None
    return CompanySite(place=place, site_role="office", legal_entity_ref=None, workforce=None)
