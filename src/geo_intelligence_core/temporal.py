"""Offline observation normalization; no opening-hours or attendance inference."""
from pydantic import ValidationError

from .models.common import Issue, Result, Status
from .models.observation import Observation
from .models.requests import RequestContext


_METHOD = 'observation-normalization-v1'


def normalize_observation(observation: Observation) -> Result[Observation]:
    """Validate a supplied observation without altering count, unit or rights.

    Mapping inputs follow the same validation as direct model construction.
    Missing counts return unknown with their scope, reason and evidence intact.
    This pure local transformation grants no use, retention or export rights.
    It performs no deduplication, duration scaling, or comparison.
    """
    context = RequestContext(request_id='observation-normalization', method_version=_METHOD)
    try:
        # Revalidate instances too: model_construct is not a validation boundary.
        values = observation.model_dump(warnings=False) if isinstance(observation, Observation) else observation
        normalized = Observation.model_validate(values)
    except (ValidationError, ValueError, TypeError, OverflowError, RecursionError):
        return Result[Observation](status=Status.invalid_input, data=None,
            issues=(Issue(code='invalid_observation', message_key='observation.invalid'),),
            context=context)
    context = context.model_copy(update={'request_id': normalized.id})
    missing = normalized.count is None
    return Result[Observation](status=Status.unknown if missing else Status.ok,
        data=normalized, evidence=normalized.evidence,
        issues=(Issue(code='observation_count_missing', message_key='observation.count_missing'),) if missing else (),
        context=context)
