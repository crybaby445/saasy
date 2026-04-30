from unittest.mock import MagicMock, patch, call
from saasy.models import Session, Proposal, EnumResult, Finding
from saasy.connectors.ona import OnaConnector
from saasy import session as session_module

def make_session() -> Session:
    return Session(
        target_url="https://api.ona.io",
        target_name="ona",
        connector_description="Ona",
        auth_headers={"Authorization": "Token abc"},
    )

def make_enum_result(proposal: Proposal, status: int = 200) -> EnumResult:
    return EnumResult(
        proposal=proposal,
        request_headers={},
        request_body=None,
        response_status=status,
        response_headers={},
        response_body='{"username": "admin"}',
    )

def test_run_approves_and_executes_seeded_proposal():
    sess = make_session()
    connector = OnaConnector(base_url="https://api.ona.io")
    ai = MagicMock()
    first_proposal = connector.seed_proposals()[0]

    with (
        patch("saasy.session.enumeration.execute", return_value=make_enum_result(first_proposal)) as mock_exec,
        patch("saasy.session.Prompt.ask", side_effect=["y", "quit"]),
        patch("saasy.session.console"),
    ):
        ai.propose_next_step.return_value = Proposal(
            method="GET", endpoint="https://api.ona.io/api/v1/orgs",
            rationale="next step", is_finding=False,
        )
        session_module.run(sess, connector, ai)

    mock_exec.assert_called_once()
    assert len(sess.enum_results) == 1

def test_run_skips_proposal_on_n():
    sess = make_session()
    connector = OnaConnector(base_url="https://api.ona.io")
    ai = MagicMock()

    with (
        patch("saasy.session.enumeration.execute") as mock_exec,
        patch("saasy.session.Prompt.ask", side_effect=["n", "quit"]),
        patch("saasy.session.console"),
    ):
        session_module.run(sess, connector, ai)

    mock_exec.assert_not_called()

def test_finding_triggers_chat_mode():
    sess = make_session()
    connector = MagicMock()
    connector.seed_proposals.return_value = []
    ai = MagicMock()

    finding_proposal = Proposal(
        method="GET", endpoint="https://api.ona.io/api/v1/users",
        rationale="check", is_finding=True,
        finding_title="User Enumeration", finding_description="All users exposed",
    )
    ai.propose_next_step.return_value = finding_proposal
    ai.chat.return_value = "This is a serious finding."

    with (
        patch("saasy.session.Prompt.ask", side_effect=["what does this mean?", "next", "quit"]),
        patch("saasy.session.console"),
    ):
        session_module.run(sess, connector, ai)

    ai.chat.assert_called_once_with("what does this mean?", sess)
    assert len(sess.findings) == 1
    assert sess.findings[0].title == "User Enumeration"
