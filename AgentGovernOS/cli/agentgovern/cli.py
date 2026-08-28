"""
AgentGovern CLI — main Typer application.

Entry point: `agentgovern` command installed via pip.

Commands:
  scan          — Scan a project for AI agents and check governance policies
  agents list   — List registered agents from the server
  agents show   — Show details of one agent
  agents register — Register agents from agentgovern.yaml
  policy list   — List available policy bundles
  policy check  — Run policy checks without a full scan
  audit tail    — Stream recent audit logs from the server
  init          — Initialize agentgovern.yaml in a project
  version       — Print version info
"""

from __future__ import annotations

import json
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentgovern import __version__

# ── Lazy imports (to keep startup fast) ───────────────────────────────────

app = typer.Typer(
    name="agentgovern",
    help="🛡️  AgentGovern OS — The open-source AI Agent Governance Scanner",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

agents_app = typer.Typer(help="Manage AI agents via the Governance API server", no_args_is_help=True)
policy_app = typer.Typer(help="Work with governance policy bundles", no_args_is_help=True)
audit_app = typer.Typer(help="Access the immutable audit ledger", no_args_is_help=True)

app.add_typer(agents_app, name="agents")
app.add_typer(policy_app, name="policy")
app.add_typer(audit_app, name="audit")

console = Console

DEFAULT_SERVER = "http://localhost:8000"


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    sarif = "sarif"
    html = "html"


class FailOn(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ════════════════════════════════════════════════════════════════════════════
# WATCH MODE HELPER
# ════════════════════════════════════════════════════════════════════════════

def _run_watch_mode(
    path: Path,
    output: Optional[Path],
    format: OutputFormat,
    policy_bundle: str,
    fail_on: FailOn,
    ci: bool,
    server: Optional[str],
    offline: bool,
    no_codeprint: bool,
    watch_interval: int,
) -> None:
    """
    Run continuous scan mode with file watching.

    Monitors the project directory for changes and automatically re-runs scans.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print(
            "[red]Error:[/red] Watch mode requires the 'watchdog' package.\n"
            "[dim]Install it with:[/dim] pip install watchdog"
        )
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold green]🔄 Watch Mode Enabled[/bold green]\n"
        f"[dim]Monitoring:[/dim] {path}\n"
        f"[dim]Interval:[/dim] {watch_interval}s\n"
        f"[dim]Press Ctrl+C to stop[/dim]",
        border_style="green",
    ))

    last_scan_time = 0.0
    scan_counter = 0

    def run_single_scan:
        """Execute a single scan iteration."""
        nonlocal scan_counter
        scan_counter += 1

        if not ci:
            console.print(f"\n[dim]{'─' * 60}[/dim]")
            console.print(f"[bold cyan]Scan #{scan_counter}[/bold cyan] — {time.strftime('%H:%M:%S')}")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

        # Re-import to pick up any code changes
        from agentgovern.scanner.manifest import discover_manifests, parse_manifest
        from agentgovern.scanner.dependency import scan_dependencies
        from agentgovern.scanner.codeprint import scan_codeprint, CodeprintScanResult
        from agentgovern.scanner.authority import analyse_authority
        from agentgovern.policy.engine import run_policy_checks
        from agentgovern.report.abom import build_abom, save_abom
        from agentgovern.report import terminal as term

        root = path.resolve
        t_start = time.monotonic

        # Run scan phases
        try:
            manifest_paths = discover_manifests(root)
            manifest_results = [parse_manifest(p) for p in manifest_paths]
            dep_result = scan_dependencies(root)

            if no_codeprint:
                codeprint_result = CodeprintScanResult
            else:
                codeprint_result = scan_codeprint(root)

            all_agents = [a for mr in manifest_results for a in mr.agents]
            authority_result = analyse_authority(all_agents)
            policy_result = run_policy_checks(all_agents, codeprint_result, policy_bundle)

            project_name = manifest_results[0].project if manifest_results else root.name
            abom = build_abom(
                project=project_name,
                manifest_results=manifest_results,
                dependency_result=dep_result,
                codeprint_result=codeprint_result,
                authority_result=authority_result,
                policy_result=policy_result,
                scan_duration_s=time.monotonic - t_start,
            )

            # Output results based on format
            if format == OutputFormat.json:
                if output:
                    save_abom(abom, output)
                    if not ci:
                        console.print(f"[green]✓[/green] ABOM updated in [bold]{output}[/bold]")
                else:
                    print(json.dumps(abom, indent=2, default=str))

            elif format == OutputFormat.sarif:
                from agentgovern.report.sarif import build_sarif, save_sarif
                sarif = build_sarif(policy_result, codeprint_result)
                if output:
                    save_sarif(sarif, output)
                    if not ci:
                        console.print(f"[green]✓[/green] SARIF updated in [bold]{output}[/bold]")
                else:
                    print(json.dumps(sarif, indent=2))

            elif format == OutputFormat.html:
                from agentgovern.report.html import build_html_report, save_html_report
                html = build_html_report(abom, policy_result, codeprint_result)
                if output:
                    save_html_report(html, output)
                    if not ci:
                        console.print(f"[green]✓[/green] HTML report updated in [bold]{output}[/bold]")
                else:
                    print(html)

            else:  # table format
                if not ci:
                    term.print_scan_summary(project_name, manifest_results, dep_result, codeprint_result)
                    term.print_agents_table(all_agents, authority_result.risk_scores)
                    term.print_violations_table(policy_result)
                    term.print_secrets_warning(codeprint_result)
                    term.print_final_result(abom, fail_on.value)

            if not ci:
                console.print(f"\n[dim]✓ Scan completed in {time.monotonic - t_start:.2f}s[/dim]")
                console.print(f"[dim]Waiting for changes...[/dim]")

        except Exception as e:
            console.print(f"[red]Scan error:[/red] {e}")
            if not ci:
                import traceback
                console.print(f"[dim]{traceback.format_exc}[/dim]")

    class ScanEventHandler(FileSystemEventHandler):
        """Handle file system events and trigger scans."""

        def on_any_event(self, event):
            nonlocal last_scan_time

            # Ignore directory events and hidden files
            if event.is_directory or event.src_path.endswith(('.pyc', '.git', '__pycache__')):
                return

            # Debounce: only scan if enough time has passed
            current_time = time.monotonic
            if current_time - last_scan_time >= watch_interval:
                last_scan_time = current_time
                run_single_scan

    # Run initial scan
    run_single_scan

    # Set up file watcher
    event_handler = ScanEventHandler
    observer = Observer
    observer.schedule(event_handler, str(path.resolve), recursive=True)
    observer.start

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow]  Watch mode stopped by user")
        observer.stop
    observer.join


# ════════════════════════════════════════════════════════════════════════════
# SCAN COMMAND
# ════════════════════════════════════════════════════════════════════════════

@app.command
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the project directory to scan. Defaults to current directory.",
        show_default=True,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Save the ABOM (Agent Bill of Materials) to this JSON file.",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f",
        help="Output format: [table|json|sarif|html]",
    ),
    policy_bundle: str = typer.Option(
        "default", "--policy-bundle", "-p",
        help="Policy bundle to use. Run `agentgovern policy list` to see options.",
    ),
    fail_on: FailOn = typer.Option(
        FailOn.high, "--fail-on",
        help="Exit with code 1 if violations of this severity or above are found.",
    ),
    ci: bool = typer.Option(
        False, "--ci",
        help="CI mode: minimal output, exit codes are the only signal.",
    ),
    server: Optional[str] = typer.Option(
        None, "--server", "-s",
        help="Upload ABOM to this Governance API server after scanning.",
        envvar="AGENTGOVERN_SERVER",
    ),
    offline: bool = typer.Option(
        False, "--offline",
        help="Force offline mode — do not attempt server sync.",
    ),
    no_codeprint: bool = typer.Option(
        False, "--no-codeprint",
        help="Skip source code scanning (faster, but less thorough).",
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w",
        help="Continuous scan mode — re-scan on file changes.",
    ),
    watch_interval: int = typer.Option(
        2, "--watch-interval",
        help="Watch mode polling interval in seconds (default: 2).",
    ),
) -> None:
    """
    🔍 Scan a project for AI agents and check governance policies.

    Detects agents from manifests, dependencies, and source code.
    Generates an ABOM (Agent Bill of Materials) and reports violations.

    Examples:
        agentgovern scan
        agentgovern scan ./my-project --policy-bundle enterprise
        agentgovern scan --fail-on critical --format sarif --output results.sarif
        agentgovern scan --server http://localhost:8000
        agentgovern scan --watch --format html --output report.html
    """
    # If watch mode is enabled, delegate to watch function
    if watch:
        _run_watch_mode(
            path=path,
            output=output,
            format=format,
            policy_bundle=policy_bundle,
            fail_on=fail_on,
            ci=ci,
            server=server,
            offline=offline,
            no_codeprint=no_codeprint,
            watch_interval=watch_interval,
        )
        return

    from agentgovern.scanner.manifest import discover_manifests, parse_manifest
    from agentgovern.scanner.dependency import scan_dependencies
    from agentgovern.scanner.codeprint import scan_codeprint, CodeprintScanResult
    from agentgovern.scanner.authority import analyse_authority
    from agentgovern.policy.engine import run_policy_checks
    from agentgovern.report.abom import build_abom, save_abom
    from agentgovern.report.sarif import build_sarif, save_sarif
    from agentgovern.report import terminal as term

    root = path.resolve
    if not root.exists:
        console.print(f"[red]Error:[/red] Path does not exist: {root}")
        raise typer.Exit(1)
    if not root.is_dir:
        console.print(f"[red]Error:[/red] Path is not a directory: {root}")
        raise typer.Exit(1)

    if not ci:
        term.print_banner
        console.print(f"\n[dim]Scanning:[/dim] [bold white]{root}[/bold white]")
        console.print(f"[dim]Policy bundle:[/dim] [green]{policy_bundle}[/green]  |  "
                      f"[dim]Fail on:[/dim] [yellow]{fail_on.value}[/yellow]\n")

    t_start = time.monotonic

    with term.make_progress as progress:
        # Discover & parse manifests
        task1 = progress.add_task("Scanning agentgovern.yaml manifests...", total=3)
        manifest_paths = discover_manifests(root)
        manifest_results = [parse_manifest(p) for p in manifest_paths]
        progress.update(task1, advance=1)

        # Scan dependencies
        progress.update(task1, description="Scanning dependency files...")
        dep_result = scan_dependencies(root)
        progress.update(task1, advance=1)

        # Source code scan
        progress.update(task1, description="Scanning source code patterns...")
        if no_codeprint:
            from agentgovern.scanner.codeprint import CodeprintScanResult
            codeprint_result = CodeprintScanResult
        else:
            codeprint_result = scan_codeprint(root)
        progress.update(task1, advance=1)

    # Collect all agents
    all_agents = [a for mr in manifest_results for a in mr.agents]

    # Authority analysis
    authority_result = analyse_authority(all_agents)

    # Policy checks
    policy_result = run_policy_checks(all_agents, codeprint_result, policy_bundle)

    # Build ABOM
    project_name = manifest_results[0].project if manifest_results else root.name
    abom = build_abom(
        project=project_name,
        manifest_results=manifest_results,
        dependency_result=dep_result,
        codeprint_result=codeprint_result,
        authority_result=authority_result,
        policy_result=policy_result,
        scan_duration_s=time.monotonic - t_start,
    )

    # ── Output ─────────────────────────────────────────────────────────────
    if format == OutputFormat.json:
        if output:
            save_abom(abom, output)
            if not ci:
                console.print(f"[green]✓[/green] ABOM saved to [bold]{output}[/bold]")
        else:
            print(json.dumps(abom, indent=2, default=str))
        exit_code = 0 if abom["summary"]["overall_pass"] else 1
        raise typer.Exit(exit_code)

    elif format == OutputFormat.sarif:
        from agentgovern.report.sarif import build_sarif, save_sarif
        sarif = build_sarif(policy_result, codeprint_result)
        if output:
            save_sarif(sarif, output)
            if not ci:
                console.print(f"[green]✓[/green] SARIF saved to [bold]{output}[/bold]")
        else:
            print(json.dumps(sarif, indent=2))
        exit_code = 0 if abom["summary"]["overall_pass"] else 1
        raise typer.Exit(exit_code)

    elif format == OutputFormat.html:
        from agentgovern.report.html import build_html_report, save_html_report
        html = build_html_report(abom, policy_result, codeprint_result)
        if output:
            save_html_report(html, output)
            if not ci:
                console.print(f"[green]✓[/green] HTML report saved to [bold]{output}[/bold]")
        else:
            print(html)
        exit_code = 0 if abom["summary"]["overall_pass"] else 1
        raise typer.Exit(exit_code)

    else:  # table (default)
        if not ci:
            term.print_scan_summary(project_name, manifest_results, dep_result, codeprint_result)
            term.print_frameworks_detected(dep_result)
            term.print_agents_table(all_agents, authority_result.risk_scores)
            term.print_violations_table(policy_result)
            term.print_secrets_warning(codeprint_result)

        if output:
            save_abom(abom, output)
            if not ci:
                console.print(f"\n[dim]ABOM saved to:[/dim] [bold]{output}[/bold]")

        exit_code = term.print_final_result(abom, fail_on.value)

    # ── Server sync ────────────────────────────────────────────────────────
    if server and not offline:
        from agentgovern.client.api import GovernanceAPIClient
        client = GovernanceAPIClient(server)
        if not ci:
            console.print(f"\n[dim]Syncing ABOM to server:[/dim] {server}")
        try:
            if client.health:
                client.upload_abom(abom)
                if not ci:
                    console.print("[green]✓[/green] ABOM synced to governance server.")
            else:
                if not ci:
                    console.print(f"[yellow]⚠[/yellow]  Server unreachable at {server}. Skipping sync.")
        except Exception as e:
            if not ci:
                console.print(f"[yellow]⚠[/yellow]  Server sync failed: {e}")

    raise typer.Exit(exit_code)


# ════════════════════════════════════════════════════════════════════════════
# AGENTS COMMANDS
# ════════════════════════════════════════════════════════════════════════════

@agents_app.command("list")
def agents_list(
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AGENTGOVERN_SERVER"),
) -> None:
    """📋 List all registered agents from the Governance API server."""
    from agentgovern.client.api import GovernanceAPIClient
    client = GovernanceAPIClient(server)
    try:
        agents = client.list_agents
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not agents:
        console.print("[yellow]No agents registered on the server.[/yellow]")
        return

    table = Table(title="Registered Agents", box=box.ROUNDED, border_style="green")
    table.add_column("Code", style="bold white")
    table.add_column("Name")
    table.add_column("Framework", style="cyan")
    table.add_column("Tier", justify="center")
    table.add_column("Authority", justify="right", style="green")
    table.add_column("Status", justify="center")

    for a in agents:
        status = a.get("status", "active")
        status_color = "green" if status == "active" else "yellow"
        authority = a.get("authority_limit")
        authority_str = f"{authority:,.2f}" if authority is not None else "—"
        table.add_row(
            a.get("agent_code", ""),
            a.get("agent_name", ""),
            a.get("framework", "—"),
            a.get("tier", "—"),
            authority_str,
            f"[{status_color}]{status}[/{status_color}]",
        )
    console.print(table)


@agents_app.command("show")
def agents_show(
    code: str = typer.Argument(..., help="Agent code, e.g. FI-ANALYST-001"),
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AGENTGOVERN_SERVER"),
) -> None:
    """🔍 Show full details of a single registered agent."""
    from agentgovern.client.api import GovernanceAPIClient
    client = GovernanceAPIClient(server)
    try:
        agent = client.get_agent(code)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold white]{agent.get('agent_name', code)}[/bold white]\n"
        f"[dim]Code:[/dim] {agent.get('agent_code', '')}\n"
        f"[dim]Framework:[/dim] {agent.get('framework', '—')}\n"
        f"[dim]Tier:[/dim] {agent.get('tier', '—')}\n"
        f"[dim]Authority Limit:[/dim] {agent.get('authority_limit', '—')}\n"
        f"[dim]Status:[/dim] {agent.get('status', '—')}",
        title=f"[green]Agent Details[/green]",
        border_style="green",
    ))
    console.print_json(json.dumps(agent, default=str))


@agents_app.command("register")
def agents_register(
    manifest: Path = typer.Argument(
        Path("agentgovern.yaml"),
        help="Path to agentgovern.yaml to register agents from.",
    ),
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AGENTGOVERN_SERVER"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be registered without doing it."),
) -> None:
    """📝 Register agents defined in agentgovern.yaml on the server."""
    from agentgovern.scanner.manifest import parse_manifest
    from agentgovern.client.api import GovernanceAPIClient

    result = parse_manifest(manifest)
    if not result.agents:
        console.print("[yellow]No agents found in manifest.[/yellow]")
        return

    console.print(f"Found [bold]{len(result.agents)}[/bold] agent(s) in {manifest}\n")

    if dry_run:
        console.print("[dim]Dry run — no changes will be made.[/dim]")
        for agent in result.agents:
            console.print(f"  • [cyan]{agent.code}[/cyan] — {agent.name} ({agent.framework})")
        return

    client = GovernanceAPIClient(server)
    success, failed = 0, 0

    for agent in result.agents:
        payload = {
            "agent_code": agent.code,
            "agent_name": agent.name,
            "framework": agent.framework,
            "tier": agent.tier,
            "authority_limit": agent.authority_limit,
            "currency": agent.currency,
            "allowed_actions": agent.allowed_actions,
            "denied_actions": agent.denied_actions,
            "platform_bindings": agent.platform_bindings,
        }
        try:
            client.register_agent(payload)
            console.print(f"  [green]✓[/green] Registered [bold]{agent.code}[/bold] — {agent.name}")
            success += 1
        except ConnectionError as e:
            console.print(f"  [red]✗[/red] {agent.code}: {e}")
            failed += 1
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] {agent.code}: {e}")
            failed += 1

    console.print(f"\n[green]{success} registered[/green], [red]{failed} failed[/red]")


# ════════════════════════════════════════════════════════════════════════════
# POLICY COMMANDS
# ════════════════════════════════════════════════════════════════════════════

@policy_app.command("list")
def policy_list -> None:
    """📦 List all available policy bundles."""
    from agentgovern.policy.engine import list_bundles
    import json as _json
    from pathlib import Path
    
    BUNDLES_DIR = Path(__file__).parent / "policy" / "bundles"
    bundles = list_bundles

    table = Table(title="Available Policy Bundles", box=box.ROUNDED, border_style="green")
    table.add_column("Name", style="bold green")
    table.add_column("Rules", justify="right")
    table.add_column("Description")

    for name in bundles:
        p = BUNDLES_DIR / f"{name}.json"
        try:
            data = _json.loads(p.read_text)
            desc = data.get("description", "")
            count = len(data.get("rules", []))
        except Exception:
            desc, count = "", 0
        table.add_row(name, str(count), desc[:70] + ("…" if len(desc) > 70 else ""))

    console.print(table)
    console.print(f"\n[dim]Usage:[/dim]  agentgovern scan --policy-bundle [green]<name>[/green]")


@policy_app.command("check")
def policy_check(
    path: Path = typer.Argument(Path("."), help="Project directory to check."),
    bundle: str = typer.Option("default", "--bundle", "-b"),
) -> None:
    """✅ Run policy checks against a project (without full codeprint scan)."""
    from agentgovern.scanner.manifest import discover_manifests, parse_manifest
    from agentgovern.scanner.codeprint import CodeprintScanResult
    from agentgovern.policy.engine import run_policy_checks
    from agentgovern.report import terminal as term

    root = path.resolve
    manifests = [parse_manifest(p) for p in discover_manifests(root)]
    all_agents = [a for m in manifests for a in m.agents]
    empty_codeprint = CodeprintScanResult
    result = run_policy_checks(all_agents, empty_codeprint, bundle)
    term.print_violations_table(result)
    exit_code = 0 if result.passed else 1
    raise typer.Exit(exit_code)


@policy_app.command("validate")
def policy_validate(
    bundle_file: Path = typer.Argument(..., help="Path to a custom policy bundle JSON file."),
) -> None:
    """🔎 Validate a custom policy bundle JSON file."""
    import json as _json
    try:
        data = _json.loads(bundle_file.read_text)
        rules = data.get("rules", [])
        console.print(f"[green]✓[/green] Valid bundle: [bold]{data.get('name', '?')}[/bold]  |  {len(rules)} rules")
        for r in rules:
            console.print(f"  • [dim]{r.get('id')}[/dim] — {r.get('name')} [{r.get('severity')}]")
    except Exception as e:
        console.print(f"[red]✗ Invalid bundle:[/red] {e}")
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════
# AUDIT COMMANDS
# ════════════════════════════════════════════════════════════════════════════

@audit_app.command("tail")
def audit_tail(
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AGENTGOVERN_SERVER"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of recent entries to show."),
    agent: Optional[str] = typer.Option(None, "--agent", help="Filter by agent code."),
) -> None:
    """📜 Show recent audit log entries from the Governance API server."""
    from agentgovern.client.api import GovernanceAPIClient

    VERDICT_COLORS = {"APPROVED": "green", "BLOCKED": "red", "ESCALATED": "yellow", "UNKNOWN": "dim"}

    client = GovernanceAPIClient(server)
    try:
        logs = client.fetch_audit_logs(limit=limit, agent_code=agent)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not logs:
        console.print("[yellow]No audit log entries found.[/yellow]")
        return

    table = Table(
        title="Recent Audit Ledger",
        box=box.ROUNDED,
        border_style="dim white",
        header_style="bold cyan",
    )
    table.add_column("Timestamp", style="dim", min_width=20)
    table.add_column("Agent", style="white")
    table.add_column("Action", style="cyan")
    table.add_column("Verdict", justify="center")
    table.add_column("Value", justify="right")
    table.add_column("Risk", justify="center")

    for entry in logs:
        verdict = entry.get("verdict", "UNKNOWN")
        vc = VERDICT_COLORS.get(verdict, "dim")
        risk = entry.get("risk_score", "")
        risk_c = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green", "CRITICAL": "bold red"}.get(risk, "dim")
        table.add_row(
            str(entry.get("created_at", ""))[:19].replace("T", " "),
            entry.get("agent_code", ""),
            (entry.get("action_requested") or "")[:40],
            f"[{vc}]{verdict}[/{vc}]",
            str(entry.get("amount_requested", "")),
            f"[{risk_c}]{risk}[/{risk_c}]" if risk else "",
        )

    console.print(table)


@audit_app.command("export")
def audit_export(
    output: Path = typer.Argument(..., help="Output file path."),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json|sarif"),
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AGENTGOVERN_SERVER"),
    limit: int = typer.Option(1000, "--limit", "-n"),
) -> None:
    """💾 Export audit logs to a file."""
    from agentgovern.client.api import GovernanceAPIClient
    import json as _json

    client = GovernanceAPIClient(server)
    try:
        logs = client.fetch_audit_logs(limit=limit)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    output.write_text(_json.dumps(logs, indent=2, default=str), encoding="utf-8")
    console.print(f"[green]✓[/green] Exported {len(logs)} audit entries to [bold]{output}[/bold]")


# ════════════════════════════════════════════════════════════════════════════
# INIT COMMAND
# ════════════════════════════════════════════════════════════════════════════

@app.command
def init(
    path: Path = typer.Argument(Path("."), help="Directory to initialize."),
    force: bool = typer.Option(False, "--force", help="Overwrite if agentgovern.yaml already exists."),
) -> None:
    """
    🚀 Initialize an agentgovern.yaml manifest in your project.

    Automatically detects installed AI frameworks and scaffolds a starter manifest.
    """
    from agentgovern.scanner.dependency import scan_dependencies

    root = path.resolve
    manifest_path = root / "agentgovern.yaml"

    if manifest_path.exists and not force:
        console.print(f"[yellow]⚠[/yellow]  agentgovern.yaml already exists at {manifest_path}")
        console.print("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(0)

    # Detect frameworks
    dep_result = scan_dependencies(root)
    detected_frameworks = list(dep_result.frameworks)

    project_name = typer.prompt("Project name", default=root.name)
    framework = typer.prompt(
        "Primary agent framework",
        default=detected_frameworks[0] if detected_frameworks else "crewai",
    )
    agent_code = typer.prompt("Agent code (e.g. ANALYST-001)", default="AGENT-001")
    agent_name = typer.prompt("Agent name (e.g. Finance Analyst Agent)", default="My AI Agent")
    tier = typer.prompt("Tier [T0/T1/T2/T3/T4]", default="T3")
    authority = typer.prompt("Authority limit (e.g. 10000.00)", default="10000.00")

    content = f"""version: "1.0"
project: "{project_name}"
governance:
  policy_bundle: "default"
  compliance: []

agents:
  - code: "{agent_code}"
    name: "{agent_name}"
    framework: "{framework}"
    tier: "{tier}"
    authority_limit: {authority}
    currency: "USD"
    allowed_actions:
      - read_data
      - write_report
    denied_actions:
      - delete_records
      - wire_transfer
    platform_bindings: []
    risk_tolerance: "medium"
"""

    manifest_path.write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓[/green] Created [bold]{manifest_path}[/bold]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Edit [bold]agentgovern.yaml[/bold] to add your agents")
    console.print("  2. Run [bold green]agentgovern scan[/bold green] to check governance policies")
    console.print(f"  3. Run [bold green]agentgovern agents register[/bold green] to sync with the server")


# ════════════════════════════════════════════════════════════════════════════
# VERSION COMMAND
# ════════════════════════════════════════════════════════════════════════════

@app.command
def version -> None:
    """🔖 Print the AgentGovern CLI version."""
    console.print(Panel(
        f"[bold green]AgentGovern OS CLI[/bold green]  v[bold]{__version__}[/bold]\n"
        f"[dim]Apache 2.0 — https://github.com/Ritinpaul/AgentGovern-OS[/dim]",
        border_style="green",
        padding=(0, 2),
    ))


# ════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app
