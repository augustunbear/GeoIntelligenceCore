"""Conservative optional adapter, not a second OSM grammar implementation."""
from datetime import datetime, timezone as datetime_timezone
from importlib import import_module, metadata
from typing import Literal
from zoneinfo import ZoneInfo

from .models.common import FrozenModel, Issue, Result, Status
from .models.requests import RequestContext


class OpeningHoursEvaluation(FrozenModel):
    """A schedule-derived state, never a measured visit or freshness assertion."""
    hours_raw: str | None
    state: Literal['open', 'closed', 'unknown']
    evaluated_at: datetime | None
    timezone: str | None
    parser: str | None = None
    parser_version: str | None = None


def evaluate_opening_hours(hours_raw: str | None, *, at: datetime,
                           timezone: str) -> Result[OpeningHoursEvaluation]:
    """Evaluate an explicit instant in the supplied IANA place timezone.

    Holiday, solar and open-ended schedules are deliberately unsupported here.
    All uncertainty returns unknown, including an absent optional dependency.
    Importing the core does not load the parser, infer location or call a service.
    """
    context = RequestContext(request_id='opening-hours-evaluation',
                             method_version='opening-hours-evaluation-v1')
    raw = hours_raw if isinstance(hours_raw, str) else None
    zone_name = timezone if isinstance(timezone, str) else None
    instant = None
    code = 'opening_hours_context_invalid'
    state = 'unknown'
    parser_name = parser_version = None
    try:
        if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
            raise ValueError('offset-aware instant required')
        # UTC roundtrip also resolves ZoneInfo fold before handing time to Rust.
        instant = at.astimezone(datetime_timezone.utc)
        zone = ZoneInfo(timezone)
        local = instant.astimezone(zone)
        if not 1900 <= local.year <= 9998:
            raise ValueError('outside supported date range')
        code = 'opening_hours_schedule_unsupported'
        if not raw or len(raw) > 4096:
            raise ValueError('missing or oversized schedule')
        # Deliberately over-reject, including occurrences inside comments. Do not
        # rely on word boundaries: valid selectors can be adjacent to times.
        lowered = raw.lower()
        if any(token in lowered for token in ('ph', 'sh', 'sunrise', 'sunset', 'dawn', 'dusk', 'easter', '+', '"')):
            raise ValueError('context-dependent schedule')
        code = 'opening_hours_parser_unavailable'
        if metadata.version('opening-hours-py') != '2.1.5':
            raise ValueError('unverified parser version')
        parser = import_module('opening_hours')
        code = 'opening_hours_evaluation_unknown'
        parser_name, parser_version = 'opening-hours-py', '2.1.5'
        schedule = parser.OpeningHours(raw, timezone=zone,
                                      auto_country=False, auto_timezone=False)
        parsed_state, _comment = schedule.state(local)
        state = {parser.State.OPEN: 'open', parser.State.CLOSED: 'closed'}.get(parsed_state, 'unknown')
    except Exception:
        # An optional native parser failure must not turn uncertainty into closed.
        state = 'unknown'
    known = state != 'unknown'
    return Result[OpeningHoursEvaluation](status=Status.ok if known else Status.unknown,
        data=OpeningHoursEvaluation(hours_raw=raw, state=state,
                                    evaluated_at=instant, timezone=zone_name,
                                    parser=parser_name, parser_version=parser_version),
        issues=() if known else (Issue(code=code, message_key='opening_hours.unknown'),),
        context=context)
