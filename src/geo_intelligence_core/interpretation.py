"""Optional factual explanations, separate from geographic facts and evidence.

Structured output and valid citation IDs do not establish semantic truth.
All explanations remain unverified and require consumer-side human review.
"""
from datetime import datetime
from typing import Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from .models.common import FrozenModel
from .models.evidence import Evidence, utc


class ApprovedFact(FrozenModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    kind: Literal['measured', 'derived', 'estimated', 'unverified'] = 'unverified'


class ExplanationRequest(FrozenModel):
    facts: tuple[ApprovedFact, ...] = Field(min_length=1, max_length=100)
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=128)
    language: Literal['de', 'zh-CN', 'en'] = 'de'
    allow_external_processing: StrictBool = False

    @model_validator(mode='after')
    def bind_evidence(self):
        evidence_ids = {e.id for e in self.evidence}
        if (len(evidence_ids) != len(self.evidence) or
                len({f.id for f in self.facts}) != len(self.facts) or
                any(len(set(f.evidence_ids)) != len(f.evidence_ids) or
                    not set(f.evidence_ids).issubset(evidence_ids) for f in self.facts)):
            raise ValueError('facts require unique IDs and existing evidence')
        return self


class CitedStatement(FrozenModel):
    text: str = Field(min_length=1, max_length=2000)
    fact_ids: tuple[str, ...] = Field(min_length=1, max_length=100)


class ExplanationContent(FrozenModel):
    statements: tuple[CitedStatement, ...] = Field(min_length=1, max_length=20)
    limitations: tuple[str, ...] = Field(max_length=20)

    @field_validator('limitations')
    @classmethod
    def bounded_limitations(cls, values):
        if any(not text.strip() or len(text) > 2000 for text in values):
            raise ValueError('invalid limitation')
        return values


class Explanation(ExplanationContent):
    provider_id: str
    model: str
    generated_at: datetime
    input_sha256: str
    prompt_version: str = 'factual-explanation-v1'
    verification: Literal['unverified'] = 'unverified'
    requires_review: Literal[True] = True

    @field_validator('generated_at')
    @classmethod
    def generated_utc(cls, value):
        return utc(value)
