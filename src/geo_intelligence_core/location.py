"""Explicit, offline confirmation of one selected location."""
from uuid import uuid4

from pydantic import ValidationError

from .models.common import Issue, Result, Status
from .models.location import Location
from .models.requests import ConfirmRequest, RequestContext


def confirm_location(request: ConfirmRequest, previous: Location | None = None) -> Result[Location]:
    """Confirm a manually supplied point or one explicitly selected candidate.

    Validation errors become invalid_input. Existing locations retain identity and
    gain a new version; the caller owns authorization for that identity.
    """
    request_id = str(uuid4())
    try:
        request = ConfirmRequest.model_validate(request)
        if previous is not None:
            previous = Location.model_validate(previous)
        request_id = request.request_id or request_id
        if previous is not None and request.location_id not in (None, previous.id):
            raise ValueError("location_id does not match previous location")
        identity = previous.id if previous else (request.location_id or str(uuid4()))
        location = Location(
            id=identity,
            version=previous.version + 1 if previous else 1,
            point=request.candidate.point if request.candidate else request.point,
            address=request.address or (request.candidate.address if request.candidate else None),
            entrances=request.entrances,
            confirmation=request.confirmation,
        )
    except (ValidationError, ValueError) as exc:
        issues = [Issue(code="invalid_confirmation", message_key="location.invalid_confirmation")]
        return Result[Location](status=Status.invalid_input, data=None, issues=issues, context=RequestContext(request_id=request_id))
    return Result[Location](status=Status.ok, data=location, evidence=request.evidence,
                            context=RequestContext(request_id=request_id, location_versions={identity: location.version}))
