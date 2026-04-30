import click
import yaml
from pathlib import Path
from .models import Session
from .auth.basic import APIKeyAuth, BasicAuth
from .connectors.ona import OnaConnector
from .connectors.generic import GenericConnector
from .ai.claude import ClaudeProvider
from . import session as session_module

_CONFIG_PATH = Path.home() / ".saasy" / "credentials.yaml"


def _load_config(target: str) -> dict:
    if _CONFIG_PATH.exists():
        data = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        return data.get(target, {})
    return {}


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--target", required=True, type=click.Choice(["ona", "generic"]),
              help="SaaS connector to use")
@click.option("--url", required=True, help="Target base URL (e.g. https://api.ona.io)")
@click.option("--api-key", default=None, help="API key / PAT for authentication")
@click.option("--user", default=None, help="Username for user+pass authentication")
@click.option("--pass", "password", default=None, help="Password for user+pass authentication")
@click.option("--spec", default=None, help="Path to OpenAPI spec file (generic target only)")
@click.option("--model", default="claude-opus-4-7", help="Claude model to use")
def start(target: str, url: str, api_key: str | None, user: str | None,
          password: str | None, spec: str | None, model: str) -> None:
    """Start an interactive red team session against a SaaS target."""
    config = _load_config(target)
    api_key = api_key or config.get("api_key")
    user = user or config.get("username")
    password = password or config.get("password")

    if api_key:
        auth = APIKeyAuth(api_key=api_key)
        auth_type = "API Key"
    elif user and password:
        login_url = f"{url.rstrip('/')}/api/v1/profiles/"
        auth = BasicAuth(login_url=login_url, username=user, password=password)
        click.echo("Authenticating...")
        auth.authenticate()
        auth_type = "Username/Password"
    else:
        raise click.UsageError("Provide --api-key or both --user and --pass")

    if target == "ona":
        connector = OnaConnector(base_url=url)
    else:
        connector = GenericConnector(base_url=url, spec_path=spec)

    ai = ClaudeProvider(model=model)

    sess = Session(
        target_url=url,
        target_name=target,
        connector_description=connector.describe(),
        auth_headers=auth.get_headers(),
        auth_type=auth_type,
    )

    session_module.run(sess, connector, ai)


def main() -> None:
    cli()
