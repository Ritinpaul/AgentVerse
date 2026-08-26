"""
Nuuvixx AgentsEcosystem — Unified CLI

The single entry point for the entire Nuuvixx platform.

Commands:
  nuuvixx deploy agent.yaml    — Publish to AgentStore + spawn on AgentOS
  nuuvixx run nuuvixx/slug     — Fetch lockfile, trust gate, execute, meter
  nuuvixx verify builder/name  — Trigger ASI01-ASI10 security scan
  nuuvixx revenue <builder-id> — Show builder revenue dashboard
  nuuvixx hire --cap <cap>     — Discover and hire an A2A agent
  nuuvixx procurement list     — List pending enterprise approvals
  nuuvixx logs <agent-id>      — Stream AgentOS execution logs
  nuuvixx terminate <agent-id> — Terminate a running agent
  nuuvixx status               — Show health of all ecosystem services
"""

import typer
import httpx
import os
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv
from pathlib import Path

# ── Load ecosystem .env ────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

from commands import deploy, run as run_cmd

app = typer.Typer(
    name="nuuvixx",
    help=(
        "Nuuvixx AgentsEcosystem CLI — Build, publish, and run intelligent agents.\n\n"
        "Connects: AgentStore | AgentOS | AgentGovernOS | AgentStudio"
    ),
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()

# ── Environment ────────────────────────────────────────────────────────────────
AGENTSTORE_URL    = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
AGENTGOVERN_URL   = os.getenv("AGENTGOVERN_URL", "http://127.0.0.1:8025")
NUUVIXX_API_KEY   = os.getenv("NUUVIXX_API_KEY", "")

def _headers() -> dict:
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


# ── Sub-command typers from commands/ ──────────────────────────────────────────
app.add_typer(deploy.app, name="deploy", help="[Bridge 3] Publish to AgentStore + spawn on AgentOS.")
app.add_typer(run_cmd.app, name="run",   help="[Bridge 2] Fetch lockfile, trust gate, execute, and meter.")


# ── verify ─────────────────────────────────────────────────────────────────────
@app.command("verify")
def verify_agent(
    slug: str = typer.Argument(..., help="Agent slug: 'builder/agent-name'"),
):
    """
    [Bridge 2] Trigger an on-demand ASI01-ASI10 security scan for an agent.

    Example: nuuvixx verify nuuvixx/support-agent
    """
    parts = slug.split("/", 1)
    if len(parts) != 2:
        console.print("[red]✗ Invalid slug format. Use: builder/agent-name[/red]")
        raise typer.Exit(1)
    builder, name = parts

    console.print(f"\n[cyan]Triggering ASI security scan for[/cyan] [bold]{slug}[/bold]...")
    try:
        r = httpx.post(
            f"{AGENTSTORE_URL}/api/v1/verification/agents/{builder}/{name}/scan/trigger",
            headers=_headers(), timeout=10.0
        )
        r.raise_for_status()
        result = r.json()
        scan_id = result.get("scan_id") or result.get("id") or "scan-started"
        console.print(f"[green]✓ Scan triggered[/green] — ID: [bold]{scan_id}[/bold]")
        console.print(
            f"  View results: [cyan]{AGENTSTORE_URL}/api/v1/verification/agents/{builder}/{name}/report[/cyan]"
        )
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ Scan trigger failed {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]✗ Cannot reach AgentStore: {e}[/red]")
        raise typer.Exit(1)


# ── revenue ────────────────────────────────────────────────────────────────────
@app.command("revenue")
def show_revenue(
    builder_id: str = typer.Argument(
        ..., help="Builder ID (your AgentStore username)"
    ),
):
    """
    [Bridge 2] Show revenue dashboard for a builder.

    Example: nuuvixx revenue nuuvixx
    """
    console.print(f"\n[cyan]Revenue dashboard for[/cyan] [bold]{builder_id}[/bold]...\n")
    try:
        r = httpx.get(
            f"{AGENTSTORE_URL}/api/v1/billing/builders/{builder_id}/revenue",
            headers=_headers(), timeout=10.0
        )
        r.raise_for_status()
        data = r.json()

        table = Table(title=f"💰 Revenue — {builder_id}", border_style="cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold green")

        for key, val in data.items():
            if key in ("period", "currency"):
                continue
            label = key.replace("_", " ").title()
            if isinstance(val, float):
                table.add_row(label, f"${val:.4f} {data.get('currency', 'USD')}")
            else:
                table.add_row(label, str(val))

        console.print(table)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ Revenue fetch failed {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]✗ Cannot reach AgentStore: {e}[/red]")
        raise typer.Exit(1)


# ── hire ───────────────────────────────────────────────────────────────────────
@app.command("hire")
def hire_agent(
    capability: str = typer.Option(..., "--capability", "--cap", "-c", help="A2A capability to hire for"),
    buyer_slug: str = typer.Option(
        ..., "--buyer", "-b",
        help="Your agent's slug (buyer): 'builder/agent-name'"
    ),
    min_trust: int = typer.Option(70, "--min-trust", "-t", help="Minimum trust score for seller"),
):
    """
    [Bridge 6] Discover and hire an A2A agent for a capability.

    Example: nuuvixx hire --cap "search:flights" --buyer nuuvixx/orchestrator
    """
    console.print(f"\n[cyan]Discovering agents for capability[/cyan] [bold]{capability}[/bold]...\n")
    try:
        # Step 1: Discover
        discover_r = httpx.get(
            f"{AGENTSTORE_URL}/api/v1/a2a/directory",
            headers=_headers(),
            params={"capability": capability, "min_trust_score": min_trust},
            timeout=10.0
        )
        discover_r.raise_for_status()
        sellers = discover_r.json()
        if isinstance(sellers, dict):
            sellers = sellers.get("agents", sellers.get("results", []))

        if not sellers:
            console.print(f"[red]✗ No agents found for capability '{capability}'[/red]")
            raise typer.Exit(1)

        best = max(sellers, key=lambda s: s.get("trust_score", 0))
        seller_slug = best["agent_slug"]
        console.print(f"  Selected: [bold]{seller_slug}[/bold] (trust={best.get('trust_score', '?')})")

        # Step 2: Negotiate
        negotiate_r = httpx.post(
            f"{AGENTSTORE_URL}/api/v1/a2a/contracts/negotiate",
            json={"buyer_slug": buyer_slug, "seller_slug": seller_slug, "capability": capability},
            headers=_headers(), timeout=10.0
        )
        negotiate_r.raise_for_status()
        contract = negotiate_r.json()

        console.print(Panel(
            f"[green]✓ Contract Negotiated[/green]\n\n"
            f"  Contract ID: [bold]{contract.get('contract_id', 'N/A')}[/bold]\n"
            f"  Buyer:  {buyer_slug}\n"
            f"  Seller: {seller_slug}\n"
            f"  Price:  ${contract.get('price_per_call_usd', 0):.4f}/call\n"
            f"  Status: {contract.get('status', 'negotiated')}",
            title="A2A Contract",
            border_style="green"
        ))
        console.print(
            f"\n  To settle: [cyan]nuuvixx settle --contract {contract.get('contract_id')} --buyer {buyer_slug}[/cyan]\n"
        )
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ A2A hire failed {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]✗ Cannot reach AgentStore: {e}[/red]")
        raise typer.Exit(1)


# ── procurement ────────────────────────────────────────────────────────────────
@app.command("procurement")
def procurement(
    action: str = typer.Argument("list", help="Action: list | approve | reject"),
    request_id: str = typer.Option(None, "--id", help="Procurement request ID"),
    org_id: str = typer.Option(None, "--org", help="Filter by org ID"),
):
    """
    [Bridge 4] Manage enterprise procurement requests.

    Example: nuuvixx procurement list
    Example: nuuvixx procurement approve --id req-abc123
    """
    if action == "list":
        console.print("\n[cyan]Enterprise Procurement Requests[/cyan]\n")
        params = {}
        if org_id:
            params["org_id"] = org_id
        try:
            r = httpx.get(
                f"{AGENTSTORE_URL}/api/v1/procurement/requests",
                headers=_headers(), params=params, timeout=10.0
            )
            r.raise_for_status()
            requests_data = r.json()
            if isinstance(requests_data, dict):
                requests_data = requests_data.get("requests", [])

            if not requests_data:
                console.print("[dim]No pending procurement requests.[/dim]")
                return

            table = Table(border_style="yellow")
            table.add_column("ID", style="dim", no_wrap=True)
            table.add_column("Agent", style="bold")
            table.add_column("Org")
            table.add_column("Status")
            table.add_column("Tier")

            for req in requests_data:
                status_color = "yellow" if req.get("status") == "pending" else "green"
                table.add_row(
                    str(req.get("id", ""))[:12] + "...",
                    req.get("agent_slug", req.get("listing_id", "?")),
                    req.get("org_id", "?"),
                    f"[{status_color}]{req.get('status', '?')}[/{status_color}]",
                    req.get("tier", "?"),
                )
            console.print(table)
        except httpx.RequestError as e:
            console.print(f"[red]✗ Cannot reach AgentStore: {e}[/red]")
            raise typer.Exit(1)

    elif action in ("approve", "reject"):
        if not request_id:
            console.print(f"[red]✗ --id is required for '{action}'[/red]")
            raise typer.Exit(1)
        try:
            r = httpx.post(
                f"{AGENTSTORE_URL}/api/v1/procurement/requests/{request_id}/{action}",
                headers=_headers(), timeout=10.0
            )
            r.raise_for_status()
            console.print(f"[green]✓ Request {request_id} {action}d.[/green]")
        except httpx.HTTPStatusError as e:
            console.print(f"[red]✗ {action} failed: {e.response.text}[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[red]✗ Unknown action '{action}'. Use: list | approve | reject[/red]")
        raise typer.Exit(1)


# ── logs ───────────────────────────────────────────────────────────────────────
@app.command("logs")
def show_logs(
    agent_id: str = typer.Argument(..., help="AgentOS agent ID"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of log lines to show"),
):
    """
    [AgentOS] Stream execution logs for a running agent.

    Example: nuuvixx logs agent-abc123 --lines 100
    """
    console.print(f"\n[cyan]Logs for agent[/cyan] [bold]{agent_id}[/bold] (last {lines} lines)\n")
    try:
        r = httpx.get(
            f"{CONTROL_PLANE_URL}/agents/{agent_id}/logs",
            params={"lines": lines},
            timeout=10.0
        )
        if r.status_code == 404:
            console.print(f"[red]✗ Agent '{agent_id}' not found on AgentOS Control Plane.[/red]")
            raise typer.Exit(1)
        r.raise_for_status()
        logs = r.json()
        log_lines = logs if isinstance(logs, list) else logs.get("logs", [str(logs)])
        for line in log_lines:
            console.print(f"[dim]{line}[/dim]")
    except httpx.RequestError as e:
        console.print(f"[red]✗ Cannot reach AgentOS Control Plane at {CONTROL_PLANE_URL}: {e}[/red]")
        raise typer.Exit(1)


# ── terminate ──────────────────────────────────────────────────────────────────
@app.command("terminate")
def terminate_agent(
    agent_id: str = typer.Argument(..., help="AgentOS agent ID to terminate"),
):
    """
    [AgentOS] Terminate a running agent.

    Example: nuuvixx terminate agent-abc123
    """
    console.print(f"\n[yellow]Terminating agent[/yellow] [bold]{agent_id}[/bold]...")
    try:
        r = httpx.post(
            f"{CONTROL_PLANE_URL}/agents/{agent_id}/terminate",
            timeout=10.0
        )
        r.raise_for_status()
        console.print(f"[green]✓ Agent {agent_id} terminated.[/green]")
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ Terminate failed {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]✗ Cannot reach AgentOS: {e}[/red]")
        raise typer.Exit(1)


# ── status ─────────────────────────────────────────────────────────────────────
@app.command("status")
def show_status():
    """
    Show health status of all ecosystem services.

    Example: nuuvixx status
    """
    services = [
        ("AgentStore API",     f"{AGENTSTORE_URL}/health"),
        ("AgentOS Control",    f"{CONTROL_PLANE_URL}/health"),
        ("AgentGovernOS",      f"{AGENTGOVERN_URL}/health"),
    ]

    console.print("\n[bold cyan]Nuuvixx Ecosystem — Service Health[/bold cyan]\n")
    table = Table(border_style="cyan")
    table.add_column("Service")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Details")

    for name, url in services:
        try:
            r = httpx.get(url, timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                status_txt = data.get("status", "ok")
                color = "green" if status_txt in ("ok", "operational") else "yellow"
                table.add_row(
                    name, url,
                    f"[{color}]● {status_txt.upper()}[/{color}]",
                    json.dumps({k: v for k, v in data.items() if k != "status"})[:60]
                )
            else:
                table.add_row(name, url, f"[yellow]⚠ HTTP {r.status_code}[/yellow]", "")
        except httpx.RequestError:
            table.add_row(name, url, "[red]OFFLINE[/red]", "Service not reachable")

    console.print(table)
    console.print(
        "\n[dim]Start all services:[/dim] [cyan]powershell .\\start-all.ps1[/cyan] "
        "(from AgentsEcosystem root)\n"
    )


if __name__ == "__main__":
    app()
