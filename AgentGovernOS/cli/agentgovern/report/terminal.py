"""
Rich Terminal Output Renderer — produces beautiful, informative CLI output.

Uses the `rich` library for tables, progress bars, panels, and colored text.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich import print as rprint

if TYPE_CHECKING:
    from agentgovern.scanner.manifest import AgentDefinition, ManifestParseResult
    from agentgovern.scanner.dependency import DependencyScanResult
    from agentgovern.scanner.codeprint import CodeprintScanResult
    from agentgovern.scanner.authority import AuthorityAnalysisResult
    from agentgovern.policy.engine import PolicyCheckResult

console = Console

SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
}

RISK_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "green",
}


def print_banner -> None:
    """Print the AgentGovern banner."""
    banner = Text
    banner.append("  AgentGovern", style="bold green")
    banner.append(" OS", style="bold white")
    banner.append(" — AI Agent Governance Scanner\n", style="dim white")
    banner.append("  The open-source governance scanner for AI agents\n", style="dim")
    console.print(Panel(banner, border_style="green", padding=(0, 2)))


def print_scan_summary(
    project: str,
    manifest_results: list["ManifestParseResult"],
    dep_result: "DependencyScanResult",
    codeprint_result: "CodeprintScanResult",
) -> None:
    """Print a summary of what was discovered during scanning."""
    total_agents = sum(len(m.agents) for m in manifest_results)
    console.print(f"\n[bold white]Project:[/bold white] [green]{project}[/green]")
    console.print(f"[dim]Manifests:[/dim] {len(manifest_results)}  |  "
                  f"[dim]Agents Defined:[/dim] [bold]{total_agents}[/bold]  |  "
                  f"[dim]Frameworks Detected:[/dim] {', '.join(dep_result.frameworks) or 'none'}  |  "
                  f"[dim]Files Scanned:[/dim] {codeprint_result.scanned_files}")


def print_agents_table(
    agents: list["AgentDefinition"],
    risk_scores: dict[str, str],
) -> None:
    """Print a Rich table of all discovered agents."""
    if not agents:
        console.print("\n[yellow]⚠  No agents found in manifest.[/yellow]")
        return

    table = Table(
        title="\n🤖 Detected Agents",
        box=box.ROUNDED,
        border_style="dim white",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Code", style="bold white", min_width=14)
    table.add_column("Name", style="white")
    table.add_column("Framework", style="cyan")
    table.add_column("Tier", justify="center")
    table.add_column("Authority Limit", justify="right", style="green")
    table.add_column("Risk", justify="center")

    for agent in agents:
        risk = risk_scores.get(agent.code, "LOW")
        risk_color = RISK_COLORS.get(risk, "white")
        tier_display = agent.tier or "[dim]unset[/dim]"
        authority_display = (
            f"{agent.authority_limit:,.2f} {agent.currency}"
            if agent.authority_limit is not None
            else "[dim]unset[/dim]"
        )
        table.add_row(
            agent.code,
            agent.name,
            agent.framework,
            tier_display,
            authority_display,
            f"[{risk_color}]{risk}[/{risk_color}]",
        )

    console.print(table)


def print_violations_table(policy_result: "PolicyCheckResult") -> None:
    """Print a Rich table of all policy violations."""
    if not policy_result.violations:
        console.print("\n[bold green]✅ No policy violations found![/bold green]")
        return

    table = Table(
        title="\n⚠  Policy Violations",
        box=box.ROUNDED,
        border_style="dim yellow",
        show_header=True,
        header_style="bold yellow",
    )
    table.add_column("Rule ID", style="dim white", min_width=10)
    table.add_column("Severity", justify="center", min_width=10)
    table.add_column("Agent", min_width=16)
    table.add_column("Message")
    table.add_column("Suggestion", style="dim")

    for v in policy_result.violations:
        sev_color = SEVERITY_COLORS.get(v.severity, "white")
        table.add_row(
            v.rule_id,
            f"[{sev_color}]{v.severity}[/{sev_color}]",
            v.agent_code or "[dim]project[/dim]",
            v.message[:80] + ("…" if len(v.message) > 80 else ""),
            v.suggestion[:60] + ("…" if len(v.suggestion) > 60 else ""),
        )

    console.print(table)


def print_secrets_warning(codeprint_result: "CodeprintScanResult") -> None:
    """Print warnings about hardcoded secrets."""
    if not codeprint_result.secret_detections:
        return
    console.print("\n[bold red]🔑 Hardcoded Secrets Detected[/bold red]")
    for s in codeprint_result.secret_detections:
        console.print(f"  [red]•[/red] {s.secret_type} at [dim]{s.file}[/dim]:[bold]{s.line}[/bold]  {s.snippet}")


def print_frameworks_detected(dep_result: "DependencyScanResult") -> None:
    """Print detected frameworks from dependency files."""
    if not dep_result.detected:
        return
    console.print("\n[bold cyan]📦 AI Frameworks Detected[/bold cyan]")
    for det in dep_result.detected:
        badge = "[bold green]HIGH[/bold green]" if det.high_confidence else "[cyan]detected[/cyan]"
        console.print(f"  [cyan]•[/cyan] {det.framework} ({det.package}) via [dim]{det.source_file}[/dim] {badge}")


def print_final_result(abom: dict[str, Any], fail_on: str = "none") -> int:
    """
    Print the final PASS/FAIL panel and return an exit code.
    Exit code 0 = pass, 1 = fail.
    """
    summary = abom.get("summary", {})
    critical = summary.get("critical", 0)
    high = summary.get("high", 0)
    medium = summary.get("medium", 0)
    low = summary.get("low", 0)
    secrets = summary.get("hardcoded_secrets", 0)
    passed = summary.get("overall_pass", True)

    console.print
    console.print(
        f"[dim]Summary:[/dim] "
        f"[bold red]{critical} CRITICAL[/bold red]  "
        f"[red]{high} HIGH[/red]  "
        f"[yellow]{medium} MEDIUM[/yellow]  "
        f"[cyan]{low} LOW[/cyan]  "
        f"[dim]|[/dim]  "
        f"[bold red]{secrets} secrets[/bold red]"
    )

    # Determine exit code based on fail_on threshold
    should_fail = False
    fail_levels = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 999}
    threshold = fail_levels.get(fail_on.lower, 999)

    if threshold <= 0 and critical > 0:
        should_fail = True
    elif threshold <= 1 and high > 0:
        should_fail = True
    elif threshold <= 2 and medium > 0:
        should_fail = True
    elif threshold <= 3 and low > 0:
        should_fail = True

    if secrets > 0:
        should_fail = True  # Secrets always fail

    if should_fail:
        console.print(Panel(
            "[bold red]✗  GOVERNANCE CHECK FAILED[/bold red]\n"
            "[dim]Resolve the violations above and re-run agentgovern scan.[/dim]",
            border_style="red",
        ))
        return 1
    else:
        console.print(Panel(
            "[bold green]✓  GOVERNANCE CHECK PASSED[/bold green]\n"
            "[dim]Your AI agent fleet meets the governance requirements.[/dim]",
            border_style="green",
        ))
        return 0


def make_progress -> Progress:
    """Return a configured Rich Progress bar for scanning."""
    return Progress(
        SpinnerColumn,
        TextColumn("[bold green]{task.description}"),
        BarColumn(bar_width=30, style="green", complete_style="bold green"),
        TextColumn("[dim]{task.percentage:>3.0f}%[/dim]"),
        TimeElapsedColumn,
        console=console,
        transient=False,
    )
