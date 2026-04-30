from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from .models import Session, Finding
from .connectors.base import BaseConnector
from .ai.base import BaseAIProvider
from . import enumeration

console = Console()


def run(sess: Session, connector: BaseConnector, ai: BaseAIProvider) -> None:
    console.print(Panel.fit(
        f"[bold green]saasy[/bold green] — {connector.describe()}\n"
        f"Target: {sess.target_url}",
        title="Session Started",
    ))

    pending = list(connector.seed_proposals())

    while True:
        if pending:
            proposal = pending.pop(0)
        else:
            console.print("\n[dim]Consulting AI for next step...[/dim]")
            proposal = ai.propose_next_step(sess)

        if proposal.is_finding and proposal.finding_title:
            finding = Finding(
                title=proposal.finding_title,
                description=proposal.finding_description,
                evidence=sess.enum_results[-1] if sess.enum_results else None,
            )
            sess.findings.append(finding)
            console.print(Panel(
                f"[bold]{finding.description}[/bold]",
                title=f"[red]Finding: {finding.title}[/red]",
                border_style="red",
            ))
            if _chat_loop(sess, ai):
                console.print("[yellow]Session ended.[/yellow]")
                break
            # After chat, ask the user whether to continue or quit the session
            choice = Prompt.ask("Continue?", choices=["y", "quit"], default="y")
            if choice == "quit":
                console.print("[yellow]Session ended.[/yellow]")
                break
            continue

        console.print(Panel(
            f"[bold]{proposal.method}[/bold] {proposal.endpoint}\n\n"
            f"[dim]Rationale:[/dim] {proposal.rationale}",
            title="AI Proposal",
        ))

        choice = Prompt.ask("Approve?", choices=["y", "n", "m", "quit"], default="y")

        if choice == "quit":
            console.print("[yellow]Session ended.[/yellow]")
            break
        elif choice == "n":
            continue
        elif choice == "m":
            proposal.endpoint = Prompt.ask("Endpoint", default=proposal.endpoint)
            proposal.method = Prompt.ask("Method", default=proposal.method)

        console.print("[dim]Executing...[/dim]")
        result = enumeration.execute(proposal, sess.auth_headers)
        sess.enum_results.append(result)

        status_color = "green" if result.response_status < 400 else "red"
        console.print(
            f"[{status_color}]HTTP {result.response_status}[/{status_color}] — "
            f"{len(result.response_body)} bytes"
        )


def _chat_loop(sess: Session, ai: BaseAIProvider) -> bool:
    """Run interactive chat about a finding. Returns True if the user wants to quit the session."""
    console.print(
        "\n[bold]Chat mode[/bold] — discuss this finding. "
        "Type [bold]'next'[/bold] to continue enumeration.\n"
    )
    while True:
        message = Prompt.ask("[cyan]You[/cyan]")
        if message.lower() in ("quit", "exit"):
            return True
        if message.lower() in ("next", "continue"):
            return False
        reply = ai.chat(message, sess)
        console.print(f"\n[green]AI:[/green] {reply}\n")
