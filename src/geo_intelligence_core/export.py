"""Deterministic, localized exports with per-source permission checks."""
import csv
import io
import json
import unicodedata
from importlib import resources
from typing import Literal

from .evidence import _issue, _retained_context, _sanitize
from .models.analysis import Snapshot
from .models.common import Result, Status


def _safe_cell(value: object) -> str:
    text = str(value)
    if text and (text[0] in '=+-@' or unicodedata.category(text[0])[0] == 'C' or text[0].isspace()):
        return "'" + text
    return text


def _leaves(path, value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(f'{path}/{key}', child)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _leaves(f'{path}/{i}', child)
    else:
        yield path, value


def _rows(topics):
    for topic, result in topics.items():
        data = result.data
        if data is None:
            continue
        for key, value in data.items() if isinstance(data, dict) else [('data', data)]:
            yield topic, key, value


def export_result(snapshot: Snapshot, format: Literal['json', 'geojson', 'csv'],
                  language: Literal['de', 'zh-CN', 'en'], purpose: str) -> Result[str]:
    context = _retained_context(snapshot.analysis.request_context)
    if purpose == '' or purpose != snapshot.purpose or format not in ('json', 'geojson', 'csv') or language not in ('de', 'zh-CN', 'en'):
        return Result[str](status=Status.invalid_input, data=None, issues=(_issue('invalid_export'),), context=context)
    # The retained view records its purpose through the exact source rights. Recheck it
    # during every export, including when snapshots are loaded long after creation.
    all_evidence = [e for topic in snapshot.analysis.topic_results.values() for e in topic.evidence]
    if any(not e.rights.allows('retain', purpose) for e in all_evidence):
        return Result[str](status=Status.invalid_input, data=None, issues=(_issue('purpose_mismatch'),), context=context)
    analysis, _, omissions = _sanitize(snapshot.analysis, purpose, 'export')
    redactions = tuple(sorted(set((*snapshot.redactions, *omissions))))
    messages = json.loads(resources.files('geo_intelligence_core').joinpath(f'data/locales/{language}.json').read_text(encoding='utf-8'))
    source_ids = sorted({e.id for topic in analysis.topic_results.values() for e in topic.evidence})
    summary = messages['summary'].format(count=len(analysis.selected_topics), redactions=len(redactions),
                                          sources=', '.join(source_ids))
    if format == 'json':
        payload = {'schema_version': snapshot.schema_version, 'summary': summary,
                   'analysis': analysis.model_dump(mode='json'), 'redactions': redactions}
        output = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    elif format == 'geojson':
        features = []
        for topic, path, value in _rows(analysis.topic_results):
            candidates = value.get('places', []) if isinstance(value, dict) and 'places' in value else [value]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                geometry = item.get('geometry')
                if geometry is None and isinstance(item.get('point'), dict):
                    p = item['point']
                    geometry = {'type': 'Point', 'coordinates': [p['longitude'], p['latitude']]}
                if geometry:
                    properties = {k: v for k, v in item.items() if k not in ('geometry', 'point')}
                    properties.update({'topic': topic, 'path': path})
                    features.append({'type': 'Feature', 'geometry': geometry, 'properties': properties})
        output = json.dumps({'type': 'FeatureCollection', 'features': features, 'summary': summary,
                             'redactions': redactions}, sort_keys=True, ensure_ascii=False)
    else:
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow([messages['topic'], messages['path'], messages['value'], messages['evidence']])
        for topic, path, value in _rows(analysis.topic_results):
            for leaf_path, leaf in _leaves(path, value):
                serialized = leaf if isinstance(leaf, str) else json.dumps(leaf, sort_keys=True, ensure_ascii=False)
                writer.writerow([_safe_cell(topic), _safe_cell(leaf_path), _safe_cell(serialized),
                                 _safe_cell(','.join(source_ids))])
        writer.writerow([_safe_cell(messages['redactions']), '', _safe_cell(json.dumps(redactions, ensure_ascii=False)), ''])
        writer.writerow([_safe_cell(summary), '', '', ''])
        output = stream.getvalue()
    return Result[str](status=Status.partial if redactions else Status.ok, data=output,
                       issues=(_issue('redacted'),) if redactions else (), context=context)
