from geo_intelligence_core import provenance


def test_fingerprint_tracks_runtime_source_and_resource_changes(tmp_path,monkeypatch):
    monkeypatch.setattr(provenance,'__file__',str(tmp_path/'__init__.py'))
    (tmp_path/'__init__.py').write_text('synthetic source')
    data=tmp_path/'data';data.mkdir();(data/'config.json').write_text('{"version":1}')
    first=provenance.package_fingerprint()
    assert len(first)==64 and provenance.package_fingerprint()==first
    (data/'config.json').write_text('{"version":2}')
    assert provenance.package_fingerprint()!=first
