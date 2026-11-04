"""Manual location confirmation request and operation context."""
from pydantic import Field, model_validator

from .common import FrozenModel
from .location import Address, Candidate, Confirmation, Entrance, Point
from .evidence import Evidence


class ConfirmRequest(FrozenModel):
    candidate: Candidate | None = None
    point: Point | None = None
    address: Address | None = None
    entrances: list[Entrance] = Field(default_factory=list)
    confirmation: Confirmation
    evidence: list[Evidence] = Field(min_length=1)
    location_id: str | None = None
    request_id: str | None = None

    @model_validator(mode="after")
    def selected_source(self):
        if (self.candidate is None) == (self.point is None):
            raise ValueError("select exactly one candidate or manual point")
        expected = "candidate" if self.candidate else "manual"
        if self.confirmation.method != expected:
            raise ValueError("confirmation method must match selected source")
        if self.location_id == "" or self.request_id == "":
            raise ValueError("IDs must be nonempty")
        ids = [e.id for e in self.evidence]
        if len(set(ids)) != len(ids) or not set(self.confirmation.evidence_ids).issubset(ids):
            raise ValueError("confirmation evidence must be present and unique")
        return self


class RequestContext(FrozenModel):
    request_id: str = Field(min_length=1)
    location_versions: dict[str, int] = Field(default_factory=dict)
    effective_conditions: dict[str, str] = Field(default_factory=dict)
    profile_ref: str | None = None
    template_ref: str | None = None
    method_version: str = "manual-v1"
    scope_token: str | None = None
