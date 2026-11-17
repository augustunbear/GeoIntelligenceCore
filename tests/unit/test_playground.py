"""Playground contract and smoke checks."""
import json
from geo_intelligence_core.playground import catalog, execute, Handler

def test_catalog_and_examples():
    ops = catalog()
    assert ops["parse_map_link"]["available"]
    assert ops["parse_map_link"]["example"]["url"].startswith("https://")
    assert "distance_m" in ops
    assert "analyze" in ops and not ops["analyze"]["available"]

def test_offline_execution():
    r = execute("parse_map_link", catalog()["parse_map_link"]["example"])
    assert r["status"] == "ok"
    assert execute("normalize_comparison_text", {"value": "Café Müller"}) == "cafe muller"

def test_unknown_and_unsupported():
    import pytest
    with pytest.raises(ValueError):
        execute("__dict__", {})
    with pytest.raises(ValueError):
        execute("analyze", {})
