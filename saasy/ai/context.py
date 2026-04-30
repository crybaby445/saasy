from ..models import Session

_SYSTEM_TEMPLATE = """\
You are a senior penetration tester and red team operator evaluating a SaaS \
application from an attacker's perspective.

Target: {connector_description}
Base URL: {target_url}
Authentication: {auth_type}

Your role:
- Analyze API responses to identify attack surface and potential vulnerabilities
- Think like an attacker: IDOR, broken access control, data exposure, business logic flaws
- Propose the next enumeration step using the propose_enumeration_step tool
- When you identify something exploitable, set is_finding=true and describe the impact clearly

Session state:
- Enumeration steps completed: {result_count}
- Findings noted: {finding_count}

{results_summary}"""


def build_system_prompt(session: Session) -> str:
    results_summary = ""
    if session.enum_results:
        lines = []
        for i, r in enumerate(session.enum_results, 1):
            lines.append(
                f"{i}. {r.proposal.method} {r.proposal.endpoint} → HTTP {r.response_status}\n"
                f"   Response (first 800 chars): {r.response_body[:800]}"
            )
        results_summary = "Enumeration history:\n\n" + "\n\n".join(lines)

    return _SYSTEM_TEMPLATE.format(
        connector_description=session.connector_description,
        target_url=session.target_url,
        auth_type=session.auth_type,
        result_count=len(session.enum_results),
        finding_count=len(session.findings),
        results_summary=results_summary,
    )


def build_chat_messages(session: Session) -> list[dict]:
    return list(session.conversation)
