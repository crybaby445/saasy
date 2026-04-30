from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Proposal:
    method: str
    endpoint: str
    rationale: str
    params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: Optional[dict] = None
    is_finding: bool = False
    finding_title: str = ""
    finding_description: str = ""

@dataclass
class EnumResult:
    proposal: Proposal
    request_headers: dict
    request_body: Optional[dict]
    response_status: int
    response_headers: dict
    response_body: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

@dataclass
class Finding:
    title: str
    description: str
    evidence: Optional["EnumResult"]

@dataclass
class Session:
    target_url: str
    target_name: str
    connector_description: str = ""
    auth_headers: dict = field(default_factory=dict)
    auth_type: str = "API Key"
    enum_results: list = field(default_factory=list)   # list[EnumResult]
    findings: list = field(default_factory=list)        # list[Finding]
    conversation: list = field(default_factory=list)    # list[dict]
