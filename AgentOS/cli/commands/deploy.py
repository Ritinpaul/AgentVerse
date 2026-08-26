"""
AgentOS CLI — deploy command.

Bridge 3 (AgentOS CLI → AgentStore → AgentOS Control Plane):
  Step 0 (NEW): Publish agent.yaml to AgentStore — get trust score & listing ID
  Step 1 (existing): Spawn the agent on the AgentOS Control Plane

Usage:
  nuuvixx deploy agent.yaml
  nuuvixx deploy ./my-agent/agent.yaml --skip-store-publish
"""

import typer
import yaml
import httpx
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path
from dotenv import load_dotenv

# ── Load ecosystem .env ────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parents[4] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

app = typer.Typer(help="Deploy an agent from a manifest file.")
console = Console()

AGENTSTORE_URL    = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
AGENTSTORE_FRONTEND_URL = os.getenv("AGENTSTORE_FRONTEND_URL", "http://127.0.0.1:8050")
NUUVIXX_API_KEY   = os.getenv("NUUVIXX_API_KEY", "")

def _svc_headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


@app.command("manifest")
def deploy_manifest(
    manifest_path: str = typer.Argument(
        "agent.yaml",
        help="Path to the agent manifest file (default: agent.yaml)"
    ),
    skip_store_publish: bool = typer.Option(
        False, "--skip-store-publish",
        help="Skip AgentStore listing step (useful for private/local-only agents)."
    ),
    trust_threshold: int = typer.Option(
        0, "--trust-threshold", "-t",
        help="Minimum trust score required after scan. 0 = no gate. Default: 0"
    ),
):
    """
    Deploy an agent from a manifest file.

    Publishes the agent to the AgentStore marketplace (unless --skip-store-publish),
    then spawns it on the AgentOS Control Plane.
    """
    console.print(f"\n[bold cyan]nuuvixx deploy[/bold cyan] [white]{manifest_path}[/white]\n")

    # ── Validate manifest exists ───────────────────────────────────────────────
    if not os.path.exists(manifest_path):
        console.print(f"[red]✗ Manifest file not found: {manifest_path}[/red]")
        raise typer.Exit(1)

    with open(manifest_path, "r") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            console.print(f"[red]✗ Error parsing YAML: {e}[/red]")
            raise typer.Exit(1)

    agent_section = data.get("agent") or data.get("metadata") or data
    agent_name = (
        agent_section.get("name")
        or (data.get("metadata") or {}).get("name")
        or Path(manifest_path).stem
    )
    console.print(f"  Agent: [bold]{agent_name}[/bold]")

    listing_id = None
    trust_score = 100  # Default when skipping store publish

    # ── Step 0 (NEW): Publish to AgentStore ───────────────────────────────────
    if not skip_store_publish:
        console.print("[dim]→ Step 0: Publishing to AgentStore...[/dim]")
        try:
            store_r = httpx.post(
                f"{AGENTSTORE_URL}/api/v1/registry/agents",
                json=data,
                headers=_svc_headers(),
                timeout=15.0
            )
            store_r.raise_for_status()
            listing = store_r.json()
            listing_id  = listing.get("id") or listing.get("listing_id")
            trust_score = listing.get("trust_score", 0)
            slug        = listing.get("slug", agent_name)
            builder     = listing.get("builder", "unknown")

            score_color = "green" if trust_score >= 80 else "yellow" if trust_score >= 60 else "red"
            console.print(
                f"  [green]✓ Listed on AgentStore[/green] — "
                f"Trust Score: [{score_color}]{trust_score}/100[/{score_color}]"
            )
            console.print(
                f"  Marketplace: [cyan]{AGENTSTORE_FRONTEND_URL}/agents/{builder}/{slug}[/cyan]"
            )

            # Trust gate after publish
            if trust_threshold > 0 and trust_score < trust_threshold:
                console.print(
                    f"\n[bold red]✗ Trust Gate: BLOCKED[/bold red]\n"
                    f"  Score {trust_score} < threshold {trust_threshold}. Deployment aborted.\n"
                    f"  Review ASI scan results at: [cyan]{AGENTSTORE_URL}/docs#/verification[/cyan]\n"
                )
                raise typer.Exit(1)

        except httpx.HTTPStatusError as e:
            console.print(
                f"[yellow]⚠ AgentStore publish returned {e.response.status_code}: "
                f"{e.response.text[:200]}[/yellow]"
            )
            console.print("[dim]  Continuing to deploy on AgentOS without store listing...[/dim]")
        except httpx.RequestError as e:
            console.print(
                f"[yellow]⚠ Cannot reach AgentStore at {AGENTSTORE_URL}: {e}[/yellow]\n"
                f"  Continuing to deploy on AgentOS without store listing..."
            )
    else:
        console.print("[yellow]  (AgentStore publish skipped via --skip-store-publish)[/yellow]")

    # ── Step 1: Spawn on AgentOS Control Plane ────────────────────────────────
    console.print("[dim]→ Step 1: Spawning on AgentOS Control Plane...[/dim]")

    # Build a clean payload that works with control-plane's AgentCreate schema
    entrypoint = (
        agent_section.get("entrypoint")
        or (data.get("spec") or {}).get("entrypoint")
        or "main.py"
    )
    description = (
        agent_section.get("description")
        or (data.get("metadata") or {}).get("description", "")
    )
    env_vars = (
        agent_section.get("env")
        or (data.get("spec") or {}).get("env_vars")
        or {}
    )

    # Inject Nuuvixx-specific env vars
    env_vars.update({
        "NUUVIXX_LISTING_ID": str(listing_id) if listing_id else "",
        "NUUVIXX_TRUST_SCORE": str(trust_score),
    })

    payload = {
        "name": agent_name,
        "description": description,
        "entrypoint": entrypoint,
        "env_vars": env_vars,
    }

    try:
        resp = httpx.post(
            f"{CONTROL_PLANE_URL}/agents/spawn",
            json=payload,
            timeout=15.0
        )
        resp.raise_for_status()
        result = resp.json()
        agent_os_id = result.get("id", "unknown")

        console.print(f"  [green]✓ Running on AgentOS[/green] — Agent ID: [bold]{agent_os_id}[/bold]")

        # ── Summary ───────────────────────────────────────────────────────────
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[dim]Agent[/dim]",       f"[bold]{agent_name}[/bold]")
        table.add_row("[dim]AgentOS ID[/dim]",  f"[cyan]{agent_os_id}[/cyan]")
        if listing_id:
            table.add_row("[dim]Listing ID[/dim]", str(listing_id))
        table.add_row("[dim]Trust Score[/dim]", f"{trust_score}/100")
        table.add_row("[dim]Status[/dim]",      "[green]RUNNING[/green]")
        console.print(Panel(table, title="✅ Deployment Successful", border_style="green"))

        console.print(
            f"\n  [dim]Manage:[/dim]  nuuvixx logs {agent_os_id}\n"
            f"  [dim]Stop:[/dim]    nuuvixx terminate {agent_os_id}\n"
        )

    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ AgentOS spawn failed {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(
            f"[red]✗ Cannot reach AgentOS Control Plane at {CONTROL_PLANE_URL}[/red]\n"
            f"  Error: {e}\n"
            f"  Is the control plane running? Try: [cyan]cd AgentOS && docker-compose up control-plane[/cyan]"
        )
        raise typer.Exit(1)
