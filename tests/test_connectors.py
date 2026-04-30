import json
import pytest
from pathlib import Path
from saasy.connectors.ona import OnaConnector
from saasy.connectors.generic import GenericConnector

def test_ona_connector_describe():
    conn = OnaConnector(base_url="https://api.ona.io")
    assert "Ona" in conn.describe()

def test_ona_connector_seeds_proposals():
    conn = OnaConnector(base_url="https://api.ona.io")
    proposals = conn.seed_proposals()
    assert len(proposals) >= 3
    endpoints = [p.endpoint for p in proposals]
    assert any("/api/v1/user" in e for e in endpoints)
    assert any("/api/v1/orgs" in e for e in endpoints)
    assert any("/api/v1/projects" in e for e in endpoints)
    for p in proposals:
        assert p.method == "GET"
        assert p.rationale != ""

def test_generic_connector_no_spec():
    conn = GenericConnector(base_url="https://api.example.com")
    assert "api.example.com" in conn.describe()
    assert conn.seed_proposals() == []

def test_generic_connector_seeds_from_openapi_spec(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {}, "post": {}},
            "/projects": {"get": {}},
            "/admin/settings": {"get": {}},
        }
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))

    conn = GenericConnector(base_url="https://api.example.com", spec_path=str(spec_file))
    proposals = conn.seed_proposals()
    assert len(proposals) <= 3
    assert all(p.method == "GET" for p in proposals)
    assert all(p.endpoint.startswith("https://api.example.com") for p in proposals)
