import anthropic
from .base import BaseAIProvider
from .context import build_system_prompt, build_chat_messages
from ..models import Session, Proposal

_PROPOSE_TOOL = {
    "name": "propose_enumeration_step",
    "description": "Propose the next API call to make during enumeration of the SaaS target",
    "input_schema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            },
            "endpoint": {
                "type": "string",
                "description": "Full URL to call",
            },
            "params": {
                "type": "object",
                "description": "Query parameters to include",
            },
            "body": {
                "type": "object",
                "description": "Request body for POST/PUT/PATCH requests",
            },
            "rationale": {
                "type": "string",
                "description": "Why this step is valuable from an attacker's perspective",
            },
            "is_finding": {
                "type": "boolean",
                "description": "True if the previous result revealed something worth discussing with the tester",
            },
            "finding_title": {
                "type": "string",
                "description": "Short title for the finding (required when is_finding=true)",
            },
            "finding_description": {
                "type": "string",
                "description": "Detailed description of the finding and its impact (required when is_finding=true)",
            },
        },
        "required": ["method", "endpoint", "rationale", "is_finding"],
    },
}


class ClaudeProvider(BaseAIProvider):
    def __init__(self, model: str = "claude-opus-4-7"):
        self.client = anthropic.Anthropic()
        self.model = model

    def propose_next_step(self, session: Session) -> Proposal:
        system = build_system_prompt(session)

        if session.enum_results:
            last = session.enum_results[-1]
            user_content = (
                f"Last result: {last.proposal.method} {last.proposal.endpoint} "
                f"→ HTTP {last.response_status}\n\n"
                f"Response body:\n{last.response_body[:3000]}\n\n"
                f"What should we enumerate next?"
            )
        else:
            user_content = "We've just authenticated. What should we enumerate first?"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            thinking={"type": "enabled", "budget_tokens": 5000},
            system=system,
            tools=[_PROPOSE_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_content}],
        )

        tool_use = next(b for b in response.content if b.type == "tool_use")
        inp = tool_use.input

        return Proposal(
            method=inp["method"],
            endpoint=inp["endpoint"],
            params=inp.get("params") or {},
            body=inp.get("body"),
            rationale=inp["rationale"],
            is_finding=inp["is_finding"],
            finding_title=inp.get("finding_title", ""),
            finding_description=inp.get("finding_description", ""),
        )

    def chat(self, message: str, session: Session) -> str:
        system = build_system_prompt(session)
        session.conversation.append({"role": "user", "content": message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system,
            messages=build_chat_messages(session),
        )

        reply = response.content[0].text
        session.conversation.append({"role": "assistant", "content": reply})
        return reply
