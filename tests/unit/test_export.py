"""Rights filtering, injection-safe CSV and consistent localization."""
import csv
import io
import json
from importlib import resources

from geo_intelligence_core.models.analysis import Metric
from geo_intelligence_core.models.common import Result, Status
from geo_intelligence_core.models.evidence import Permission
from geo_intelligence_core.evidence import snapshot
from geo_intelligence_core.export import export_result
from test_evidence import analysis, evidence


def test_rights():
    permitted = evidence('public')
    restricted = evidence('secret', export=Permission.denied)
    unknown = evidence('unknown', export=Permission.unknown)
    source = analysis(items={'public': Metric(value=5, unit='items', nature='measured', evidence_ids=('public',)),
                             'private': Metric(value=987654, unit='items', nature='measured', evidence_ids=('secret',)),
                             'uncleared': Metric(value=876543, unit='items', nature='measured', evidence_ids=('unknown',))},
                      ev=permitted)
    topic = source.topic_results['places'].model_copy(update={'evidence': (permitted, restricted, unknown)})
    source = source.model_copy(update={'topic_results': {'places': topic}})
    snap = snapshot(source, 'planning').data
    assert set(snap.retained_evidence_ids) == {'public', 'secret', 'unknown'}
    for fmt in ('json', 'csv', 'geojson'):
        output = export_result(snap, fmt, 'en', 'planning')
        assert output.status == Status.partial
        assert '987654' not in output.data and '876543' not in output.data
        assert 'secret' not in output.data and 'uncleared' not in output.data
        assert 'redactions' in output.data
    assert '987654' not in json.loads(export_result(snap, 'json', 'en', 'planning').data)['summary']


def test_export_does_not_leak_scope_token_or_wrong_purpose():
    snap = snapshot(analysis(), 'planning').data
    for fmt in ('json', 'csv', 'geojson'):
        output = export_result(snap, fmt, 'en', 'planning')
        assert 'case-A' not in output.data
    assert export_result(snap, 'json', 'en', 'marketing').status == Status.invalid_input


def test_csv_formula():
    source = analysis(items={'formula': {'name': '=HYPERLINK("https://example.test")',
                                         'other': '+SUM(1,1)', 'third': '-1+2', 'fourth': '@cmd',
                                         'control': '\t=SUM(1,1)', 'evidence_ids': ['e1']}})
    result = export_result(snapshot(source, 'planning').data, 'csv', 'en', 'planning')
    cells = [cell for row in csv.reader(io.StringIO(result.data)) for cell in row]
    assert all(not cell or cell[0] not in '=+-@\t\r\n\x00' for cell in cells)
    assert any("'=HYPERLINK" in cell for cell in cells)


def test_locales():
    package = resources.files('geo_intelligence_core').joinpath('data/locales')
    bundles = [json.loads(package.joinpath(f'{lang}.json').read_text()) for lang in ('de', 'zh-CN', 'en')]
    assert set(bundles[0]) == set(bundles[1]) == set(bundles[2])
    source = analysis(items={'name': {'native_names': {'de': 'Bäckerei Süd'}, 'value': 123.5,
                                      'evidence_ids': ['e1']}})
    snap = snapshot(source, 'planning').data
    outputs = [json.loads(export_result(snap, 'json', lang, 'planning').data) for lang in ('de', 'zh-CN', 'en')]
    for output in outputs:
        assert 'Bäckerei Süd' in json.dumps(output, ensure_ascii=False)
        assert '123.5' in json.dumps(output)
        assert 'e1' in json.dumps(output)
    assert len({output['summary'] for output in outputs}) == 3


def test_purpose_bound_even_if_snapshot_has_no_retained_sources():
    source = analysis(ev=evidence(retain=Permission.denied))
    snap = snapshot(source, 'planning').data
    assert export_result(snap, 'json', 'en', 'other-purpose').status == Status.invalid_input


def test_derived_value_requires_every_contributing_source():
    open_source = evidence('open')
    closed_source = evidence('closed', export=Permission.unknown)
    source = analysis(items={'derived': Metric(value=111222, unit='items', nature='derived', evidence_ids=('open', 'closed'))},
                      ev=open_source)
    topic = source.topic_results['places'].model_copy(update={'evidence': (open_source, closed_source)})
    snap = snapshot(source.model_copy(update={'topic_results': {'places': topic}}), 'planning').data
    for fmt in ('json', 'csv', 'geojson'):
        assert '111222' not in export_result(snap, fmt, 'en', 'planning').data


def test_private_correction_history_is_removed_when_export_denied():
    from geo_intelligence_core.evidence import apply_correction
    from test_evidence import correction
    source = analysis(ev=evidence(export=Permission.denied))
    corrected = apply_correction(source, correction('correct',
        {'value': 765432, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']}), 'case-A').data
    snap = snapshot(corrected, 'planning').data
    assert snap.analysis.originals['places/count']['value'] == 4
    assert snap.analysis.corrections
    exported = export_result(snap, 'json', 'en', 'planning')
    assert exported.status == Status.partial
    assert '765432' not in exported.data
    assert 'originals' in exported.data
    assert 'case-A' not in exported.data


def test_allowed_correction_history_survives_export_without_scope_token():
    from geo_intelligence_core.evidence import apply_correction
    from test_evidence import correction
    corrected = apply_correction(analysis(), correction('correct',
        {'value': 765432, 'unit': 'items', 'nature': 'measured', 'evidence_ids': ['e1']}), 'case-A').data
    snap = snapshot(corrected, 'planning').data
    exported = export_result(snap, 'json', 'en', 'planning')
    assert exported.status == Status.ok
    assert '765432' in exported.data
    assert json.loads(exported.data)['analysis']['corrections']
    assert 'case-A' not in exported.data


def test_csv_formula_with_unicode_control_prefixes():
    source = analysis(items={'formula': {'bom': '\ufeff=SUM(1,1)', 'delete': '\x7f=SUM(1,1)',
                                         'next_line': '\u0085@cmd', 'evidence_ids': ['e1']}})
    output = export_result(snapshot(source, 'planning').data, 'csv', 'en', 'planning').data
    cells = [cell for row in csv.reader(io.StringIO(output)) for cell in row]
    for control in ('\ufeff', '\x7f', '\u0085'):
        assert any(cell.startswith("'" + control) for cell in cells)


def test_export_filters_nested_restricted_correction_payload():
    from test_evidence import Correction, NOW
    permitted = evidence('e1')
    denied = evidence('closed', export=Permission.denied)
    source = analysis(ev=permitted)
    topic = source.topic_results['places'].model_copy(update={'evidence': (permitted, denied)})
    forged = Correction(target_ref='places/count', action='correct',
                        replacement={'public': {'text': 'ordinary', 'evidence_ids': ['e1']},
                                     'private': {'text': 'SENSITIVE-LEAK', 'evidence_ids': ['closed']}},
                        evidence_ids=('e1',), reason='verified', scope_token='case-A', at=NOW.isoformat())
    snap = snapshot(source.model_copy(update={'topic_results': {'places': topic}, 'corrections': (forged,)}), 'planning').data
    assert 'SENSITIVE-LEAK' in snap.model_dump_json()
    for fmt in ('json', 'csv', 'geojson'):
        output = export_result(snap, fmt, 'en', 'planning')
        assert 'SENSITIVE-LEAK' not in output.data
        assert output.status == Status.partial
