import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from geo_intelligence_core.location import confirm_location
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.location import Candidate, Entrance, Point
from geo_intelligence_core.models.requests import ConfirmRequest


def test_manual_confirmation_without_industry(manual_request):
    first = confirm_location(manual_request)
    assert first.status == Status.ok
    assert first.data.version == 1
    assert first.data.point == Point(longitude=11, latitude=49)
    assert first.data.confirmation.evidence_ids == ("manual-1",)
    second = confirm_location(manual_request.model_copy(update={"entrances": [Entrance(id="main", point=Point(longitude=11.001, latitude=49), role="main")]}), previous=first.data)
    assert second.status == Status.ok
    assert second.data.version == 2 and second.data.id == first.data.id
    assert first.data.entrances == ()


def test_ambiguous_candidate_not_confirmed(manual_request):
    candidate = Candidate(id="candidate-1", point=manual_request.point, source_ref="synthetic")
    result = confirm_location({"candidates": [candidate, candidate], "confirmation": manual_request.confirmation})
    assert result.status == Status.invalid_input and result.data is None
    assert result.issues
    result = confirm_location({**manual_request.model_dump(), "point": None, "candidate": None})
    assert result.status == Status.invalid_input and result.data is None


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 181, True, "11"])
def test_bad_coordinates(value):
    with pytest.raises(ValidationError):
        Point(longitude=value, latitude=49)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 91, False, "49"])
def test_bad_latitude(value):
    with pytest.raises(ValidationError):
        Point(longitude=11, latitude=value)


def test_candidate_requires_explicit_selection(manual_request):
    candidate = Candidate(id="c1", point=Point(longitude=12, latitude=50), source_ref="synthetic")
    request = manual_request.model_copy(update={"point": None, "candidate": candidate, "confirmation": manual_request.confirmation.model_copy(update={"method": "candidate"})})
    result = confirm_location(request)
    assert result.status == Status.ok and result.data.point == candidate.point
    assert result.data.point != manual_request.point


def test_invalid_confirmation_evidence(manual_request):
    request = {**manual_request.model_dump(), "evidence": []}
    result = confirm_location(request)
    assert result.status == Status.invalid_input and result.data is None


def test_previous_conflict(manual_request):
    first = confirm_location(manual_request).data
    result = confirm_location(manual_request.model_copy(update={"location_id": "different"}), previous=first)
    assert result.status == Status.invalid_input
