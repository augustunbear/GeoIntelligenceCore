"""Factual location comparisons with explicit, conservative comparability."""
from .models.analysis import Analysis, Comparison, ComparisonRow, Metric, MetricConditions
from .models.common import Issue, Result, Status
from .models.places import PlaceSet
from .models.requests import RequestContext


def _context(analyses):
    first = analyses[0].request_context if analyses else RequestContext(request_id='comparison', method_version='comparison-v1')
    return first.model_copy(update={'request_id': f'{first.request_id}:comparison', 'method_version': 'comparison-v1',
                                    'location_versions': {k: v for a in analyses for k, v in a.request_context.location_versions.items()}})


def _identity(analysis):
    versions = analysis.request_context.location_versions
    if len(versions) != 1:
        return None
    key, version = next(iter(versions.items()))
    return f'{key}@{version}'


def _cell(analysis: Analysis, metric_id: str):
    metric = analysis.metrics.get(metric_id)
    conditions = analysis.metric_conditions.get(metric_id)
    if metric is not None:
        return metric, conditions, ()
    topic, dot, field = metric_id.partition('.')
    if dot and field == 'unique_count' and topic in ('places', 'transport_places', 'company_sites'):
        result = analysis.topic_results.get(topic)
        if result is None or result.status not in (Status.ok, Status.no_results) or not isinstance(result.data, PlaceSet):
            return None, None, ('missing_result',)
        data = result.data
        effective = analysis.request_context.effective_conditions
        periods = {ev.reference_period for ev in result.evidence}
        reference_period = next(iter(periods)) if len(periods) == 1 else None
        conditions = MetricConditions(category_mapping_version=effective.get('mapping_version', 'osm-v1'),
            category_selection=effective.get('config.category_ids'), source_coverage=data.coverage,
            reference_period=effective.get('reference_period') or reference_period, scope_type=effective.get('region_method'),
            scope_threshold=effective.get('config.radius_m'), scope_version=effective.get('region_version'),
            boundary_rule=effective.get('boundary_rule'), method=effective.get('query_method', 'place-search-v1'),
            time_condition=effective.get('time_kind', '') + ':' + effective.get('time_label', ''))
        metric = Metric(value=data.unique_count, unit='places', nature='derived',
                        evidence_ids=tuple(sorted({eid for place in data.places for eid in place.evidence_ids} | {ev.id for ev in result.evidence})))
        return metric, conditions, ()
    return None, None, ('missing_metric',)


def compare(analyses: list[Analysis], metric_ids: list[str]) -> Result[Comparison]:
    """Compare against the first location, never ranking or imputing missing cells."""
    context = _context(analyses)
    ids = [_identity(a) for a in analyses]
    if len(analyses) < 2 or not metric_ids or len(set(metric_ids)) != len(metric_ids) or any(not x for x in metric_ids) or None in ids or len(set(ids)) != len(ids):
        return Result[Comparison](status=Status.invalid_input, data=None, context=context,
            issues=[Issue(code='invalid_comparison', message_key='comparison.invalid')])
    rows = []
    union_counts = {}
    union_issues = {}
    for metric_id in metric_ids:
        cells = [_cell(analysis, metric_id) for analysis in analyses]
        reference_metric, reference_conditions, reference_issues = cells[0]
        for index, (metric, conditions, cell_issues) in enumerate(cells):
            problems = list(cell_issues)
            if metric is None or metric.value is None:
                problems.append('missing_value')
            if conditions is None or not conditions.complete:
                problems.append('unknown_conditions')
            if index and (reference_metric is None or reference_metric.value is None or reference_conditions is None or not reference_conditions.complete):
                problems.append('reference_incomplete')
            if index and conditions is not None and reference_conditions is not None:
                for field in MetricConditions.model_fields:
                    if getattr(conditions, field) != getattr(reference_conditions, field):
                        problems.append(f'{field}_mismatch')
            if index and metric is not None and reference_metric is not None:
                if metric.unit != reference_metric.unit:
                    problems.append('unit_mismatch')
                if metric.nature != reference_metric.nature:
                    problems.append('nature_mismatch')
            problems = tuple(dict.fromkeys(problems))
            difference = metric.value - reference_metric.value if index and not problems else None
            rows.append(ComparisonRow(location_version=ids[index], metric_id=metric_id,
                value=metric.value if metric else None, difference=difference, unit=metric.unit if metric else (reference_metric.unit if reference_metric else ''),
                evidence_ids=metric.evidence_ids if metric else (), comparability_issues=problems))
        topic, dot, field = metric_id.partition('.')
        if dot and field == 'unique_count' and topic in ('places', 'transport_places', 'company_sites'):
            relevant = [a.topic_results.get(topic) for a in analyses]
            if all(r is not None and r.status in (Status.ok, Status.no_results) and isinstance(r.data, PlaceSet) for r in relevant) and all(not row.comparability_issues for row in rows[-len(analyses):]):
                union_counts[metric_id] = len({(p.source_key.source_id, p.source_key.entity_type, p.source_key.entity_id)
                    for r in relevant for p in r.data.places})
            else:
                union_counts[metric_id] = None
                union_issues[metric_id] = ('incomplete_or_incomparable',)
    comparison = Comparison(rows=tuple(rows), union_counts=union_counts, union_issues=union_issues)
    status = Status.partial if any(r.comparability_issues for r in rows) else Status.ok
    return Result[Comparison](status=status, data=comparison, context=context)
