from saasy.models import Proposal, EnumResult, Finding, Session

def test_proposal_defaults():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    assert p.params == {}
    assert p.headers == {}
    assert p.body is None
    assert p.is_finding is False
    assert p.finding_title == ""
    assert p.finding_description == ""

def test_enum_result_captures_fields():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    r = EnumResult(
        proposal=p,
        request_headers={"Authorization": "Token abc"},
        request_body=None,
        response_status=200,
        response_headers={"content-type": "application/json"},
        response_body='[{"id": 1}]',
    )
    assert r.response_status == 200
    assert r.timestamp != ""

def test_session_defaults():
    s = Session(target_url="https://api.example.com", target_name="example")
    assert s.enum_results == []
    assert s.findings == []
    assert s.conversation == []
    assert s.auth_headers == {}

def test_finding_links_evidence():
    p = Proposal(method="GET", endpoint="https://api.example.com/users", rationale="test")
    r = EnumResult(
        proposal=p, request_headers={}, request_body=None,
        response_status=200, response_headers={}, response_body="[]",
    )
    f = Finding(title="User Enumeration", description="All users exposed", evidence=r)
    assert f.evidence.response_status == 200
