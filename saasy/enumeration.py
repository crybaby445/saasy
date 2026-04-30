import httpx
from .models import Proposal, EnumResult


def execute(proposal: Proposal, auth_headers: dict) -> EnumResult:
    headers = {**auth_headers, **proposal.headers}
    with httpx.Client(timeout=30.0) as client:
        response = client.request(
            method=proposal.method,
            url=proposal.endpoint,
            params=proposal.params or None,
            headers=headers,
            json=proposal.body,
        )
    return EnumResult(
        proposal=proposal,
        request_headers=headers,
        request_body=proposal.body,
        response_status=response.status_code,
        response_headers=dict(response.headers),
        response_body=response.text,
    )
