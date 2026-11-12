"""Explicit time inputs must not become implicit Unix timestamps."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from geo_intelligence_core.models.configuration import TimeCondition


@pytest.mark.parametrize("value", [1700000000, 1700000000.0, "1700000000"])
def test_time_condition_rejects_numeric_instant(value):
    with pytest.raises(ValidationError):
        TimeCondition(kind="depart_at", instant=value, timezone="Europe/Berlin")


@pytest.mark.parametrize("bound", ["start", "end"])
@pytest.mark.parametrize("value", [1700000000, "1700000000"])
def test_time_condition_rejects_numeric_interval_bound(bound, value):
    interval = {"start": "2000-11-12T12:00:00+00:00",
                "end": "2026-11-13T12:00:00+00:00"}
    interval[bound] = value
    with pytest.raises(ValidationError):
        TimeCondition(kind="interval", timezone="Europe/Berlin", **interval)


def test_time_condition_keeps_explicit_offset_and_utc_datetime():
    condition = TimeCondition(kind="depart_at", instant="2026-11-12T12:30:00+01:00",
                              timezone="Europe/Berlin")
    assert condition.instant == datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)


def test_time_condition_keeps_lowercase_utc_designator():
    condition = TimeCondition(kind="depart_at", instant="2026-11-12T11:30:00z",
                              timezone="Europe/Berlin")
    assert condition.instant == datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)


def test_time_condition_keeps_aware_datetime():
    instant = datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)
    assert TimeCondition(kind="arrive_by", instant=instant,
                         timezone="Europe/Berlin").instant == instant


def test_time_condition_extreme_offset_is_validation_error():
    underflow = datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14)))
    with pytest.raises(ValidationError):
        TimeCondition(kind="depart_at", instant=underflow, timezone="Europe/Berlin")
