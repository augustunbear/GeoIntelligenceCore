"""Pure configuration resolution and capability preflight. No providers are called."""
import math
from uuid import uuid4
from pydantic import ValidationError
from .models.common import Issue, Result, Status
from .models.configuration import AnalyzeRequest, Profile, Template, EffectiveConfig
from .models.policy import UsagePolicy
from .models.requests import RequestContext
from .ports import ProviderRegistry

_ALLOWED = frozenset({'radius_m', 'language', 'category_ids', 'limit'})
_LANGUAGES = frozenset({'de', 'zh-CN', 'en'})


def _validate_params(values: dict[str, object]) -> None:
    if values.keys() - _ALLOWED:
        raise ValueError('unknown configuration field')
    if 'radius_m' in values and (type(values['radius_m']) not in (int, float) or not math.isfinite(values['radius_m']) or values['radius_m'] <= 0):
        raise ValueError('invalid radius_m')
    if 'language' in values and values['language'] not in _LANGUAGES:
        raise ValueError('invalid language')
    if 'limit' in values and (type(values['limit']) is not int or values['limit'] <= 0):
        raise ValueError('invalid limit')
    if 'category_ids' in values and (not isinstance(values['category_ids'], (tuple, list)) or any(not isinstance(x, str) or not x for x in values['category_ids'])):
        raise ValueError('invalid category_ids')


def resolve_config(request: AnalyzeRequest, profile: Profile | None, template: Template | None,
                   policy: UsagePolicy, *, registry: ProviderRegistry | None = None) -> Result[EffectiveConfig]:
    """Resolve caller overrides and report selected capability readiness without IO."""
    request_id = str(uuid4())
    profile_ref = template_ref = None
    try:
        request = AnalyzeRequest.model_validate(request)
        profile = Profile.model_validate(profile) if profile is not None else None
        template = Template.model_validate(template) if template is not None else None
        policy = UsagePolicy.model_validate(policy)
        request_id = request.request_id or request_id
        profile_ref = f'{profile.id}@{profile.version}' if profile else None
        template_ref = f'{template.id}@{template.version}' if template else None
        if request.profile_ref and request.profile_ref != profile_ref or request.template_ref and request.template_ref != template_ref:
            raise ValueError('version reference mismatch')
        if template and template.profile_ref and template.profile_ref != profile_ref:
            raise ValueError('template profile version mismatch')
        selected = [t.id for t in request.topics]
        if len(selected) != len(set(selected)):
            raise ValueError('duplicate selected topic')
        if template and not set(template.required_topics).issubset(selected):
            raise ValueError('required topic not selected')
        if template and any(not getattr(request, field, None) for field in template.required_inputs):
            raise ValueError('required input missing')
        values: dict[str, object] = {}
        provenance = {}
        for label, params in [('profile', profile.defaults if profile else {}), ('template', template.defaults if template else {}), ('request', request.explicit_parameters)]:
            _validate_params(params)
            values.update(params)
            provenance.update({key: label for key in params})
        if 'radius_m' in values and policy.max_area_m2 is not None and math.pi * values['radius_m'] ** 2 > policy.max_area_m2 + 1e-8:
            raise ValueError('radius exceeds maximum area')
        if 'limit' in values and policy.max_items is not None and values['limit'] > policy.max_items:
            raise ValueError('limit exceeds maximum items')
        required = sorted({t.id for t in request.topics if t.required} | (set(template.required_topics) if template else set()))
        context = RequestContext(request_id=request_id, location_versions={l.id: l.version for l in request.locations},
                                 profile_ref=profile_ref, template_ref=template_ref, scope_token=request.scope_token,
                                 method_version='configuration-v1', effective_conditions={'required_topics': ','.join(required)})
        statuses = {topic: Status.disabled if topic not in policy.allowed_capabilities else
                    Status(registry.status(topic)) if registry else Status.unconfigured for topic in selected}
        failures = {topic: status for topic, status in statuses.items() if status != Status.ok}
        issues = tuple(Issue(code=f'capability_{status}', message_key=f'capability.{status}', safe_params={'topic': topic}) for topic, status in failures.items())
        if failures:
            if any(topic in required for topic in failures):
                status = next(failures[topic] for topic in required if topic in failures)
            elif len(failures) < len(selected):
                status = Status.partial
            elif len(set(failures.values())) == 1:
                status = next(iter(failures.values()))
            else:
                status = Status.unavailable
        else:
            status = Status.ok
        data = EffectiveConfig(values=values, provenance_by_field=provenance, profile_ref=profile_ref, template_ref=template_ref) if status in (Status.ok, Status.partial) else None
        return Result[EffectiveConfig](status=status, data=data, issues=issues, context=context)
    except (ValidationError, ValueError, TypeError) as exc:
        context = RequestContext(request_id=request_id, profile_ref=profile_ref, template_ref=template_ref, method_version='configuration-v1')
        return Result[EffectiveConfig](status=Status.invalid_input, data=None, issues=[Issue(code='invalid_config', message_key='configuration.invalid')], context=context)
