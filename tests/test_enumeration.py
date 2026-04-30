import respx
import httpx
import pytest
from saasy.models import Proposal
from saasy import enumeration


@respx.mock
def test_execute_get_captures_response():
    respx.get("https://api.example.com/users").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "email": "a@b.com"}])
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/users",
        rationale="test"
    )
    result = enumeration.execute(proposal, auth_headers={"Authorization": "Token abc"})

    assert result.response_status == 200
    assert '"id"' in result.response_body
    assert result.request_headers["Authorization"] == "Token abc"
    assert result.proposal is proposal
    assert result.timestamp != ""


@respx.mock
def test_execute_merges_proposal_headers():
    respx.get("https://api.example.com/items").mock(
        return_value=httpx.Response(200, json=[])
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/items",
        rationale="test",
        headers={"X-Custom": "value"},
    )
    result = enumeration.execute(proposal, auth_headers={"Authorization": "Token abc"})
    assert result.request_headers["X-Custom"] == "value"
    assert result.request_headers["Authorization"] == "Token abc"


@respx.mock
def test_execute_captures_error_responses():
    respx.get("https://api.example.com/admin").mock(
        return_value=httpx.Response(403, json={"detail": "Forbidden"})
    )
    proposal = Proposal(
        method="GET",
        endpoint="https://api.example.com/admin",
        rationale="test"
    )
    result = enumeration.execute(proposal, auth_headers={})
    assert result.response_status == 403
    assert "Forbidden" in result.response_body
