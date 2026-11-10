"""Comparison-only normalization and descriptive quality, adapted from MarketLens.

See data/licenses/MarketLens-MIT.txt. Matching scores are heuristics, not
probabilities. No function changes a source record or merges fuzzy matches.
"""
from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
import math
import unicodedata

from .models.common import FrozenModel
from .models.places import Place, SourceKey


def normalize_comparison_text(value: str | None) -> str | None:
    if value is None:
        return None
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    letters = ''.join(c if c.isalnum() else ' ' for c in decomposed
                      if not unicodedata.combining(c))
    return ' '.join(letters.split()) or None


def _identity(place):
    key = place.source_key
    return key.source_id, key.entity_type, key.entity_id


def _name(place):
    return normalize_comparison_text(place.native_names.get('name'))


def _address(place):
    if place.address is None:
        return None
    address = place.address
    parts = tuple(normalize_comparison_text(getattr(address, field)) for field in
                  ('country_code', 'postcode', 'locality', 'street', 'house_number'))
    return parts if any(parts) else None


def _representative_rank(place):
    # Prefer usable matching fields over an empty repeated observation. This
    # chooses one observation for candidate generation, never a merged record.
    return (-int(bool(_name(place))), -int(_address(place) is not None),
            -int(bool(place.categories)), -len(place.contacts), place.model_dump_json())


class DuplicateCandidate(FrozenModel):
    left: SourceKey
    right: SourceKey
    score: float
    name_similarity: float
    distance_m: float
    reasons: tuple[str, ...]
    method_version: str = 'candidate-match-v1'


def find_duplicate_candidates(records: Sequence[Place], *, threshold: float = .75,
                              max_records: int = 1000) -> tuple[DuplicateCandidate, ...]:
    """Bounded O(n²) cross-source candidate search; requires geometry extra.

    The provisional threshold must be validated for a deployment's languages
    and sources. A candidate is never permission to combine licensed datasets.
    """
    if (isinstance(max_records, bool) or not isinstance(max_records, int) or
            not 1 <= max_records <= 1000 or len(records) > max_records or
            isinstance(threshold, bool) or not math.isfinite(threshold) or not 0 < threshold <= 1):
        raise ValueError('invalid matching limits')
    from .geometry import distance_m
    unique = {}
    for record in records:
        place = Place.model_validate(record)
        prior = unique.get(_identity(place))
        if prior is None or _representative_rank(place) < _representative_rank(prior):
            unique[_identity(place)] = place
    candidates = []
    for left, right in combinations([unique[k] for k in sorted(unique)], 2):
        if left.source_key.source_id == right.source_key.source_id:
            continue
        lname, rname = _name(left), _name(right)
        if not lname or not rname:
            continue
        ltokens, rtokens = set(lname.split()), set(rname.split())
        similarity = len(ltokens & rtokens) / len(ltokens | rtokens)
        if not similarity:
            continue
        distance = distance_m(left.point, right.point)
        if distance > 250:
            continue
        reasons = []
        score = similarity * .55
        if lname == rname:
            reasons.append('exact_normalized_name')
        elif similarity >= .5:
            reasons.append('similar_normalized_name')
        if distance <= 25:
            score += .25
            reasons.append('within_25m')
        elif distance <= 100:
            score += .20
            reasons.append('within_100m')
        else:
            score += .10
            reasons.append('within_250m')
        if set(left.categories) & set(right.categories):
            score += .15
            reasons.append('shared_category')
        if _address(left) is not None and _address(left) == _address(right):
            score += .10
            reasons.append('same_normalized_address')
        if score >= threshold:
            candidates.append(DuplicateCandidate(left=left.source_key, right=right.source_key,
                                                score=round(min(1, score), 4), name_similarity=round(similarity, 4),
                                                distance_m=round(distance, 2), reasons=tuple(reasons)))
    return tuple(sorted(candidates, key=lambda c: (-c.score, c.left.source_id, c.left.entity_type,
                                                  c.left.entity_id, c.right.source_id,
                                                  c.right.entity_type, c.right.entity_id)))


class PlaceQualitySummary(FrozenModel):
    total_records: int
    duplicate_source_identities: int
    with_name: int
    with_category: int
    with_address: int
    with_coordinates: int
    with_phone: int
    with_website: int
    complete_records: int
    field_completeness_percent: float | None
    record_completeness_percent: float | None
    coverage: str = 'unknown'
    method_version: str = 'field-completeness-v1'


def summarize_place_quality(records: Sequence[Place]) -> PlaceQualitySummary:
    """Six-field completeness of received records, never real-world coverage.

    Completeness requires name, category, any structured address and coordinates.
    Percentages use all received records, including repeated source identities.
    """
    counts = [0] * 6
    complete = 0
    identities = set()
    for record in records:
        p = Place.model_validate(record)
        present = [bool(_name(p)), any(c.strip() for c in p.categories), _address(p) is not None, True,
                   any(v.strip() for k, v in p.contacts.items() if k in ('phone', 'contact:phone')),
                   any(v.strip() for k, v in p.contacts.items() if k in ('website', 'contact:website'))]
        counts = [a + int(b) for a, b in zip(counts, present)]
        complete += all(present[:4])
        identities.add(_identity(p))
    total = len(records)
    return PlaceQualitySummary(total_records=total, duplicate_source_identities=total-len(identities),
                               **dict(zip(('with_name', 'with_category', 'with_address', 'with_coordinates',
                                           'with_phone', 'with_website'), counts)),
                               complete_records=complete,
                               field_completeness_percent=round(sum(counts) / (total * 6) * 100, 2) if total else None,
                               record_completeness_percent=round(complete / total * 100, 2) if total else None)
