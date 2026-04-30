from saasy.models import Session, Proposal, EnumResult
from saasy.ai.context import build_system_prompt, build_chat_messages


def make_session(**kwargs) -> Session:
    return Session(
        target_url="https://api.ona.io",
        target_name="ona",
        connector_description="Ona — ODK-based data collection SaaS",
        auth_type="API Key",
        **kwargs,
    )


def test_system_prompt_includes_target_info():
    session = make_session()
    prompt = build_system_prompt(session)
    assert "https://api.ona.io" in prompt
    assert "Ona" in prompt
    assert "API Key" in prompt


def test_system_prompt_includes_enum_history():
    p = Proposal(method="GET", endpoint="https://api.ona.io/api/v1/user", rationale="test")
    r = EnumResult(
        proposal=p, request_headers={}, request_body=None,
        response_status=200, response_headers={}, response_body='{"username": "admin"}',
    )
    session = make_session(enum_results=[r])
    prompt = build_system_prompt(session)
    assert "/api/v1/user" in prompt
    assert "200" in prompt


def test_system_prompt_empty_history():
    session = make_session()
    prompt = build_system_prompt(session)
    assert "0" in prompt  # result count


def test_build_chat_messages_returns_conversation():
    session = make_session(conversation=[
        {"role": "user", "content": "what does this mean?"},
        {"role": "assistant", "content": "it means the API is wide open"},
    ])
    messages = build_chat_messages(session)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
