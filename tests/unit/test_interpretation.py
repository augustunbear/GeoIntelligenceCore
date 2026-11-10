import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json

import httpx
import pytest

from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.evidence import Evidence, Permission, Rights, Quality
from geo_intelligence_core.models.policy import ProviderConfig
from geo_intelligence_core.models.requests import RequestContext
from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.http import HttpGateway
from test_http_policy import FakeTransport, policy

CONTEXT = RequestContext(request_id='ai-synthetic', scope_token='private-scope')


def request(allowed=True, external=True):
    from geo_intelligence_core.interpretation import ApprovedFact, ExplanationRequest
    evidence = Evidence(id='e1', source_id='synthetic', source_type='manual',
                        source_ref='private-reference-not-for-provider', retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                        method_version='test-v1', rights=Rights(use=Permission.allowed,
                            redistribute=Permission.allowed if allowed else Permission.unknown, permitted_purpose='explain'),
                        quality=Quality(coverage='unknown'))
    return ExplanationRequest(facts=(ApprovedFact(id='f1', text='The query returned 2 records.',
                              evidence_ids=('e1',), kind='derived'),), evidence=(evidence,),
                              purpose='explain', allow_external_processing=external)


def explainer(payload=None, *, enabled=True, status=200, **kwargs):
    from geo_intelligence_core.providers.gemini import GeminiExplainer
    payload = payload if payload is not None else {'statements': [{'text': 'The supplied query returned two records.', 'fact_ids': ['f1']}],
                                                  'limitations': ['Coverage is unknown.']}
    seen = []
    def reply(r):
        seen.append(r)
        return httpx.Response(status, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(payload)}]}}]})
    transport = FakeTransport([reply])
    g = HttpGateway({'ai': ProviderConfig(id='ai', endpoint='https://api.example.com', capability_flags={'explain': True})},
                    policy(size=40000).model_copy(update={'allowed_capabilities': ('explain',)}),
                    InMemoryBudget(2, Decimal(0)), transport=transport, resolver=lambda _: ['93.184.215.14'],
                    headers={'x-goog-api-key': 'synthetic-header'}, cost_per_call=Decimal(0))
    return GeminiExplainer(g, provider_id='ai', model='test-model', enabled=enabled, **kwargs), seen, transport


def test_disabled_and_unapproved_disclosure_make_no_requests():
    exp, seen, _ = explainer(enabled=False)
    assert asyncio.run(exp.explain(request(), CONTEXT)).status == Status.disabled and not seen
    for req in (request(allowed=False), request(external=False)):
        exp, seen, _ = explainer()
        assert asyncio.run(exp.explain(req, CONTEXT)).status == Status.unconfigured and not seen


def test_valid_cited_explanation_minimizes_input_and_preserves_uncertainty():
    exp, seen, _ = explainer()
    result = asyncio.run(exp.explain(request(), CONTEXT))
    assert result.status == Status.ok and result.data.requires_review is True
    assert result.data.verification == 'unverified' and result.data.input_sha256
    assert result.data.statements[0].fact_ids == ('f1',)
    wire = seen[0].content.decode()
    assert all(value not in wire for value in ('private-scope', 'private-reference-not-for-provider', 'synthetic-header'))
    body = json.loads(wire)
    assert body['generationConfig']['responseMimeType'] == 'application/json'
    assert body['generationConfig']['maxOutputTokens'] == 2048
    assert 'derived' in wire and 'unknown' in wire
    assert seen[0].headers['x-goog-api-key'] == 'synthetic-header'
    assert result.evidence == request().evidence


@pytest.mark.parametrize('payload', [
    {'statements': [{'text': 'Invented', 'fact_ids': ['invented']}], 'limitations': []},
    {'statements': [{'text': 'Uncited', 'fact_ids': []}], 'limitations': []},
    {'statements': [], 'limitations': [], 'recommendations': ['Invest now']},
    {'statements': [{'text': 'X', 'fact_ids': ['f1'], 'evidence': 'invented'}], 'limitations': []},
])
def test_invalid_schema_and_unknown_citations_fail_closed(payload):
    exp, _, _ = explainer(payload)
    result = asyncio.run(exp.explain(request(), CONTEXT))
    assert result.status == Status.unavailable and result.data is None
    assert result.issues[0].code == 'invalid_explanation'


def test_provider_failure_is_separate_from_facts():
    req = request()
    before = req.model_dump_json()
    exp, _, transport = explainer(status=500)
    result = asyncio.run(exp.explain(req, CONTEXT))
    assert result.status == Status.unavailable and result.data is None and transport.calls == 1
    assert req.model_dump_json() == before


def test_input_binding_rejects_missing_evidence_and_duplicate_fact_ids():
    from geo_intelligence_core.interpretation import ApprovedFact
    from pydantic import ValidationError
    req = request()
    with pytest.raises(ValidationError):
        req.model_copy(update={'facts': (ApprovedFact(id='bad', text='x', evidence_ids=('unknown',)),)})
    with pytest.raises(ValidationError):
        req.model_copy(update={'facts': req.facts * 2})
    from geo_intelligence_core.providers.gemini import GeminiExplainer
    with pytest.raises(ValueError):
        GeminiExplainer(None, model='../other')


@pytest.mark.parametrize('envelope', [
    {'candidates': [None]}, {'candidates': [1]}, {'candidates': {}},
    {'candidates': [{'finishReason': 'STOP', 'content': None}]},
    {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [None]}}]},
])
def test_malformed_provider_envelopes_return_sanitized_failure(envelope):
    exp, _, transport = explainer()
    transport.replies = [httpx.Response(200, json=envelope)]
    result = asyncio.run(exp.explain(request(), CONTEXT))
    assert result.status == Status.unavailable and result.issues[0].code == 'invalid_explanation'
