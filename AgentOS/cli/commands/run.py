"""
AgentOS CLI — run command.

Bridge 2 (AgentOS CLI → AgentStore):
  1. Fetch execution manifest + lockfile from AgentStore (GET /api/v1/cli/run/{slug})
  2. Trust gate — block execution if score < 70
  3. Spawn agent in AgentOS Control Plane with lockfile
  4. Meter the execution back to AgentStore billing

Usage:
  nuuvixx run nuuvixx/support-agent
  nuuvixx run nuuvixx/support-agent --trust-threshold 80
"""

import typer
import httpx
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv
from pathlib import Path

# ── Load ecosystem .env ────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parents[4] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

app = typer.Typer(help="Run a Nuuvixx agent from the AgentStore marketplace.")
console = Console()

AGENTSTORE_URL   = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
NUUVIXX_API_KEY  = os.getenv("NUUVIXX_API_KEY", "")
NUUVIXX_ORG_ID   = os.getenv("NUUVIXX_ORG_ID", "default")
NUUVIXX_USER_ID  = os.getenv("NUUVIXX_USER_ID", "cli-user")

def _svc_headers() -> dict:
    """Service-to-service headers for AgentStore API calls."""
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


@app.command("start")
def run_agent(
    slug: str = typer.Argument(..., help="Agent slug in 'builder/agent-name' format"),
    trust_threshold: int = typer.Option(
        70, "--trust-threshold", "-t",
        help="Minimum trust score required to execute (0–100). Default: 70"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Fetch manifest and check trust score without actually running."
    ),
):
    """
    Run an agent from the AgentStore marketplace.

    Fetches the agent's execution manifest, validates its trust score,
    spawns it on the AgentOS Control Plane, and records the execution
    in AgentStore billing.
    """
    console.print(f"\n[bold cyan]nuuvixx run[/bold cyan] [white]{slug}[/white]\n")

    # ── Step 1: Fetch execution manifest from AgentStore ──────────────────────
    console.print("[dim]→ Fetching execution manifest from AgentStore...[/dim]")
    try:
        r = httpx.get(
            f"{AGENTSTORE_URL}/api/v1/cli/run/{slug}",
            headers=_svc_headers(),
            timeout=10.0
        )
        r.raise_for_status()
        manifest = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(
                f"[red]✗ Agent '[bold]{slug}[/bold]' not found in AgentStore.[/red]\n"
                f"  Tip: Run [cyan]nuuvixx list[/cyan] to see available agents."
            )
        else:
            console.print(f"[red]✗ AgentStore error {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(
            f"[red]✗ Cannot reach AgentStore at {AGENTSTORE_URL}[/red]\n"
            f"  Error: {e}\n"
            f"  Is AgentStore running? Try: [cyan]uvicorn main:app --port 8005[/cyan]"
        )
        raise typer.Exit(1)

    # ── Step 2: Display manifest info ─────────────────────────────────────────
    trust_score    = manifest.get("trust_score", 0)
    listing_id     = manifest.get("listing_id", slug)
    agent_command  = manifest.get("command", "")
    lockfile       = manifest.get("lockfile", {})
    scan_results   = manifest.get("scan_results", {})

    score_color = "green" if trust_score >= 80 else "yellow" if trust_score >= 60 else "red"
    score_icon  = "●" if trust_score >= 80 else "◑" if trust_score >= 60 else "○"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[dim]Agent[/dim]",      f"[bold]{slug}[/bold]")
    table.add_row("[dim]Trust Score[/dim]", f"[{score_color}]{score_icon} {trust_score}/100[/{score_color}]")
    table.add_row("[dim]Command[/dim]",    f"[dim]{agent_command}[/dim]")
    table.add_row("[dim]Lockfile[/dim]",   f"[dim]{len(lockfile)} locked dependencies[/dim]")
    console.print(Panel(table, title="Agent Manifest", border_style="cyan"))

    # ── Step 3: Trust Gate ────────────────────────────────────────────────────
    if trust_score < trust_threshold:
        console.print(
            f"\n[bold red]✗ Trust Gate: BLOCKED[/bold red]\n"
            f"  Agent trust score [red]{trust_score}[/red] is below threshold [yellow]{trust_threshold}[/yellow].\n"
            f"  Resolve security findings to improve score:\n"
        )
        for rule, result in (scan_results or {}).items():
            icon = "[green]✓[/green]" if result == "pass" else "[red]✗[/red]"
            console.print(f"    {icon} {rule}: {result}")
        console.print(
            f"\n  To override (not recommended): [cyan]nuuvixx run {slug} --trust-threshold {trust_score}[/cyan]\n"
        )
        raise typer.Exit(1)

    console.print(f"[green]✓ Trust gate passed ({trust_score}/{trust_threshold} minimum)[/green]")

    if dry_run:
        console.print("[yellow]--dry-run mode: stopping before execution.[/yellow]")
        return

    # ── Step 4: Spawn on AgentOS Control Plane ────────────────────────────────
    console.print("[dim]→ Spawning agent on AgentOS Control Plane...[/dim]")
    start_ts = time.time()
    try:
        spawn_r = httpx.post(
            f"{CONTROL_PLANE_URL}/agents/spawn",
            json={
                "name": slug.replace("/", "-"),
                "description": f"Spawned via CLI: {slug}",
                "entrypoint": agent_command,
                "env_vars": {
                    "NUUVIXX_AGENT_SLUG": slug,
                    "NUUVIXX_LISTING_ID": str(listing_id),
                    "NUUVIXX_ORG_ID": NUUVIXX_ORG_ID,
                },
                "listing_id": str(listing_id),
                "lockfile": lockfile,
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0
        )
        spawn_r.raise_for_status()
        run_result = spawn_r.json()
        agent_os_id = run_result.get("id", "unknown")
        console.print(f"[green]✓ Agent spawned on AgentOS[/green] — ID: [bold]{agent_os_id}[/bold]")
    except Exception as e:
        console.print(f"[yellow]⚠ Control Plane spawn failed: {e}[/yellow]")
        console.print("[dim]  (Execution metering will still be recorded)[/dim]")
        agent_os_id = "spawn-failed"

    duration_ms = int((time.time() - start_ts) * 1000)

    # ── Step 5: Meter execution back to AgentStore ────────────────────────────
    console.print("[dim]→ Recording execution in AgentStore billing...[/dim]")
    try:
        meter_r = httpx.post(
            f"{AGENTSTORE_URL}/api/v1/billing/meter",
            json={
                "listing_id": str(listing_id),
                "org_id": NUUVIXX_ORG_ID,
                "caller_id": NUUVIXX_USER_ID,
                "duration_ms": duration_ms,
                "tokens_used": 0,  # Updated by execution plane when available
                "agent_os_id": agent_os_id,
            },
            headers=_svc_headers(),
            timeout=5.0
        )
        if meter_r.status_code in (200, 201):
            console.print("[green]✓ Execution metered in AgentStore billing[/green]")
        else:
            console.print(f"[yellow]⚠ Billing meter returned {meter_r.status_code}[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ Billing meter skipped: {e}[/yellow]")

    console.print(
        f"\n[bold green]✓ Agent {slug} is running![/bold green]\n"
        f"  AgentOS ID: [cyan]{agent_os_id}[/cyan]\n"
        f"  Logs: [cyan]nuuvixx logs {agent_os_id}[/cyan]\n"
    )
