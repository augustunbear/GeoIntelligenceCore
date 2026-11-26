"""Bounded, provider-neutral orchestration of selected factual topics."""
import asyncio
import json
from decimal import Decimal
from importlib import resources
from .configuration import resolve_config
from .models.analysis import Analysis
from .models.common import Issue, Result, Status
from .models.configuration import AnalyzeRequest, Profile, Template
from .models.places import PlaceQuery, PlaceSet
from .models.spatial import CircleRequest, GeometryLimits
from .models.policy import UsagePolicy
from .models.requests import RequestContext, _serving_provenance
from .ports import Budget, ProviderRegistry

_PLACE_TOPICS = frozenset({'places', 'transport_places', 'company_sites'})
_SUPPORTED = _PLACE_TOPICS | {'population_reference', 'routes'}


def _resource(kind, ref, model):
    if ref is None:
        return None
    name, separator, version = ref.rpartition('@')
    if not separator or not name or not version or '/' in name or '/' in version:
        raise ValueError('invalid resource reference')
    file = resources.files('geo_intelligence_core').joinpath('data', kind, f'{name}-v{version}.json')
    result = model.model_validate(json.loads(file.read_text(encoding='utf-8')))
    if result.id != name or result.version != version:
        raise ValueError('resource version mismatch')
    return result


def load_profile(ref: str) -> Profile:
    """Load an exact, packaged profile version."""
    return _resource('profiles', ref, Profile)


def load_template(ref: str) -> Template:
    """Load an exact, packaged template version."""
    return _resource('templates', ref, Template)


def _error(status, context, code):
    return Result[Analysis](status=status, data=None, context=context,
                            issues=[Issue(code=code, message_key=f'analysis.{code}')])


async def analyze(request: AnalyzeRequest, registry: ProviderRegistry, policy: UsagePolicy,
                  budget: Budget, *, profile: Profile | None = None, template: Template | None = None) -> Result[Analysis]:
    """Execute only selected topics. Required capability failures block all calls."""
    try:
        request = AnalyzeRequest.model_validate(request)
        profile = profile or _resource('profiles', request.profile_ref, Profile)
        template = template or _resource('templates', request.template_ref, Template)
        if profile is None and template and template.profile_ref:
            profile = _resource('profiles', template.profile_ref, Profile)
    except (ValueError, OSError, TypeError) as exc:
        context = RequestContext(request_id=getattr(request, 'request_id', None) or 'invalid-request', method_version='analysis-v1')
        return _error(Status.invalid_input, context, 'invalid_resource')
    preflight = resolve_config(request, profile, template, policy, registry=registry)
    context = preflight.context.model_copy(update={'method_version': 'analysis-v1'})
    if preflight.status not in (Status.ok, Status.partial):
        return Result[Analysis](status=preflight.status, data=None, context=context, issues=preflight.issues)
    topics = tuple(topic.id for topic in request.topics)
    required = {t.id for t in request.topics if t.required} | (set(template.required_topics) if template else set())
    template_id = template.id if template else None
    if template_id not in (None, 'surroundings', 'venue-discovery', 'location-comparison'):
        return _error(Status.invalid_input, context, 'unknown_template')
    if not topics or any(t not in _SUPPORTED for t in topics):
        return _error(Status.invalid_input, context, 'unknown_or_empty_topics')
    if template_id == 'location-comparison':
        if len(request.locations) < 2:
            return _error(Status.invalid_input, context, 'locations_required')
        return await _analyze_comparison(request, registry, policy, budget, profile, context)
    if template_id == 'surroundings' and len(request.locations) != 1:
        return _error(Status.invalid_input, context, 'one_location_required')
    if template_id == 'venue-discovery' and not (request.locations or request.regions):
        return _error(Status.invalid_input, context, 'location_or_region_required')
    values = preflight.data.values
    if template and any(t not in set(template.required_topics) | set(template.optional_topics) for t in topics):
        return _error(Status.invalid_input, context, 'topic_outside_template')
    regions = request.regions
    if any(t in _PLACE_TOPICS for t in topics) and not regions:
        if len(request.locations) != 1 or 'radius_m' not in request.explicit_parameters:
            return _error(Status.invalid_input, context, 'explicit_region_required')
        if policy.max_area_m2 is None or policy.max_geometry_vertices is None:
            return _error(Status.unconfigured, context, 'geometry_limits_required')
        from .geometry import circle
        generated = circle(CircleRequest(center=request.locations[0].point,
                                         radius_m=float(values['radius_m'])),
                           limits=GeometryLimits(max_area_m2=policy.max_area_m2,
                                                 max_vertices=policy.max_geometry_vertices))
        if generated.status != Status.ok:
            return _error(generated.status, context, 'circle_failed')
        regions = (generated.data,)
    if any(t in _PLACE_TOPICS for t in topics) and not values.get('category_ids'):
        return _error(Status.invalid_input, context, 'categories_required')
    if len(regions) > 1 and any(t in _PLACE_TOPICS for t in topics):
        return _error(Status.invalid_input, context, 'ambiguous_region')
    if len(request.locations) > 1 and template_id != 'location-comparison':
        return _error(Status.invalid_input, context, 'ambiguous_location')

    effective = dict(context.effective_conditions)
    effective.update({f'config.{k}': str(v) for k, v in values.items()})
    if regions:
        effective.update({'region_id': regions[0].id, 'region_version': regions[0].version,
                          'region_method': regions[0].method, 'boundary_rule': regions[0].boundary_rule})
    if request.time:
        effective['time_kind'] = request.time.kind
        effective['time_label'] = request.time.label or ''
    context = context.model_copy(update={'effective_conditions': effective})
    results: dict[str, Result[object]] = {}
    used_calls = 0
    for topic in topics:
        if topic not in policy.allowed_capabilities:
            results[topic] = _topic_failure(Status.disabled, context, topic)
            continue
        port = registry.get(topic)
        if port is None:
            results[topic] = _topic_failure(Status.unconfigured, context, topic)
            continue
        if topic not in _PLACE_TOPICS:
            results[topic] = _topic_failure(Status.unsupported, context, topic)
            continue
        if used_calls >= policy.max_calls_per_run:
            results[topic] = _topic_failure(Status.unavailable, context, topic, 'call_limit')
            continue
        if not await budget.reserve(topic, 1, Decimal(0)):
            results[topic] = _topic_failure(Status.unavailable, context, topic, 'budget_rejected')
            continue
        used_calls += 1
        query = PlaceQuery(region=regions[0], category_ids=tuple(values['category_ids']),
                           mapping_version='osm-v1',
                           boundary_rule=regions[0].boundary_rule)
        try:
            response = await asyncio.wait_for(port.search(query, context), timeout=policy.deadline_s)
            response = Result[PlaceSet].model_validate(response)
            await budget.record(topic, Decimal(0))
            issues = list(response.issues)
            if request.time:
                issues.append(Issue(code='static_places_time_unverified', message_key='analysis.static_places_time_unverified'))
            # Keep the adapter's serving-instance provenance on this topic, without
            # allowing a port to replace the caller's request identity or scope.
            topic_context = context.model_copy(update={'effective_conditions': {
                **context.effective_conditions, **_serving_provenance(response.context)}})
            results[topic] = Result[object](status=response.status, data=response.data, context=topic_context,
                                            evidence=response.evidence, issues=issues)
        except Exception:
            # Provider failures are per-topic; never convert an absent record to an empty PlaceSet.
            results[topic] = _topic_failure(Status.unavailable, context, topic, 'provider_failure')
    statuses = {t: r.status for t, r in results.items()}
    if any(statuses[t] not in (Status.ok, Status.no_results) for t in required):
        overall = next(statuses[t] for t in topics if t in required and statuses[t] not in (Status.ok, Status.no_results))
    elif all(s in (Status.ok, Status.no_results) for s in statuses.values()):
        overall = Status.ok
    elif any(s in (Status.ok, Status.no_results) for s in statuses.values()):
        overall = Status.partial
    elif len(set(statuses.values())) == 1:
        overall = next(iter(statuses.values()))
    else:
        overall = Status.partial
    analysis = Analysis(request_context=context, selected_topics=topics, topic_results=results)
    issues = tuple(issue for r in results.values() for issue in r.issues)
    return Result[Analysis](status=overall, data=analysis, context=context, issues=issues)


def _topic_failure(status, context, topic, code=None):
    code = code or f'capability_{status}'
    return Result[object](status=status, data=None, context=context,
                          issues=[Issue(code=code, message_key=f'analysis.{code}', safe_params={'topic': topic})])


async def _analyze_comparison(request, registry, policy, budget, profile, context):
    """Run one independent factual analysis per location, then compare the same selected metrics."""
    from .comparison import compare
    count = len(request.locations)
    if len(request.regions) not in (0, count) or (not request.regions and 'radius_m' not in request.explicit_parameters):
        return _error(Status.invalid_input, context, 'explicit_region_per_location_required')
    if not any(t.id in _PLACE_TOPICS for t in request.topics):
        return _error(Status.unsupported, context, 'comparison_topic_unsupported')
    class SharedRunBudget:
        def __init__(self):
            self.used_calls = 0

        async def reserve(self, provider_id, calls, estimated_cost):
            if self.used_calls + calls > policy.max_calls_per_run:
                return False
            accepted = await budget.reserve(provider_id, calls, estimated_cost)
            if accepted:
                self.used_calls += calls
            return accepted

        async def record(self, provider_id, actual_cost):
            await budget.record(provider_id, actual_cost)

    shared_budget = SharedRunBudget()
    results = []
    analyses = []
    for index, location in enumerate(request.locations):
        child = request.model_copy(update={
            'locations': (location,), 'regions': (request.regions[index],) if request.regions else (),
            'template_ref': None, 'request_id': f'{context.request_id}:{index + 1}',
        })
        result = await analyze(child, registry, policy, shared_budget, profile=profile)
        results.append(result)
        if result.data is not None:
            analyses.append(result.data)
        else:
            analyses.append(Analysis(request_context=result.context, selected_topics=tuple(t.id for t in request.topics)))
    metric_ids = [f'{t.id}.unique_count' for t in request.topics if t.id in _PLACE_TOPICS]
    compared = compare(analyses, metric_ids)
    if compared.data is None:
        return _error(compared.status, context, 'comparison_failed')
    per_location = {f'{loc.id}@{loc.version}': result.status for loc, result in zip(request.locations, results)}
    topics = {f'{loc.id}@{loc.version}/{topic}': topic_result
              for loc, result in zip(request.locations, results) if result.data is not None
              for topic, topic_result in result.data.topic_results.items()}
    analysis = Analysis(request_context=compared.context, selected_topics=tuple(t.id for t in request.topics),
                        comparison=compared.data, location_statuses=per_location, topic_results=topics)
    statuses = {r.status for r in results}
    status = Status.ok if statuses == {Status.ok} and compared.status == Status.ok else Status.partial
    return Result[Analysis](status=status, data=analysis, context=compared.context,
                            issues=tuple(issue for r in results for issue in r.issues) + compared.issues)
