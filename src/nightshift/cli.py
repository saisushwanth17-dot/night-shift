"""Night Shift Command-Line Interface."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from nightshift.agent.diagnose import DiagnosticEngine
from nightshift.config import settings
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import RemediationStatus

# Force safe ASCII rendering on Windows console
console = Console(safe_box=True, highlight=False)


def run_diagnostics(repo_path: str = "demo_repo", test_cmd: str = "pytest test_data_pipeline.py"):
    """Execute diagnostic sweep on target repository."""
    console.print(Panel.fit(
        "[bold cyan]NIGHT SHIFT[/bold cyan] - [white]Autonomous Software Maintenance Agent[/white]\n"
        "[dim]Mode: Controlled Safe Diagnostic Verification[/dim]",
        border_style="cyan"
    ))

    target = Path(repo_path).resolve()
    console.print(f"[bold]Target Repository:[/bold] {target}")
    console.print(f"[bold]Test Command:[/bold] {test_cmd}")
    console.print("[dim]Spawning isolated sandbox...[/dim]\n")

    engine = DiagnosticEngine()
    try:
        report = engine.run_diagnostic(str(target), test_command=test_cmd)
    except Exception as ex:
        console.print(f"[bold red]Diagnostic Error:[/bold red] {ex}")
        sys.exit(1)

    table = Table(title="Diagnostic Findings Summary", show_header=True, header_style="bold magenta", safe_box=True)
    table.add_column("Metric / Signal", style="cyan", width=25)
    table.add_column("Value / Details", style="white")

    table.add_row("Execution Status", "[red]FAILED (Reproduced)[/red]" if not report.tests_passed else "[green]PASSED[/green]")
    table.add_row("Exit Code", str(report.exit_code))
    table.add_row("Sandbox Duration", f"{report.duration_ms:.1f} ms")
    table.add_row("Failing Test", str(report.failing_test_name or "N/A"))
    table.add_row("Exception Signature", str(report.exception_type or "N/A"))
    table.add_row("Suspect File", str(report.suspect_file or "N/A"))
    table.add_row("Suspect Line", str(report.suspect_line_number or "N/A"))
    
    if report.policy_check:
        policy_verdict = f"[{'green' if report.policy_check.allowed else 'red'}]{report.policy_check.level.value}[/] (Risk: {report.policy_check.risk_score})"
        table.add_row("Policy Engine Verdict", policy_verdict)
        table.add_row("Policy Reason", report.policy_check.reason)

    console.print(table)
    console.print("\n[bold green][OK] Diagnostic Complete.[/bold green]\n")


def run_remediation(repo_path: str = "demo_repo", test_cmd: str = "pytest test_data_pipeline.py"):
    """Execute full autonomous remediation loop (Cause -> Change -> Verification)."""
    console.print(Panel.fit(
        "[bold cyan]NIGHT SHIFT[/bold cyan] - [white]Autonomous Software Maintenance Agent[/white]\n"
        "[dim]Mode: Milestone 2 — Autonomous Remediation & Bounded Self-Correction[/dim]",
        border_style="cyan"
    ))

    target = Path(repo_path).resolve()
    console.print(f"[bold]Target Repository:[/bold] {target}")
    console.print(f"[bold]Test Command:[/bold] {test_cmd}")
    console.print("[dim]Starting bounded self-correction loop (max 3 attempts)...[/dim]\n")

    loop = RemediationLoop()
    result = loop.run(str(target), test_command=test_cmd, max_attempts=3)

    # Summary Table
    table = Table(title="Remediation Workflow Result", show_header=True, header_style="bold magenta", safe_box=True)
    table.add_column("Property", style="cyan", width=25)
    table.add_column("Value / Details", style="white")

    status_color = "green" if result.status == RemediationStatus.RESOLVED else "yellow" if result.status == RemediationStatus.ALREADY_PASSING else "red"
    table.add_row("Status", f"[{status_color}]{result.status.value}[/{status_color}]")
    table.add_row("Incident ID", result.incident_id)
    table.add_row("Attempts Taken", str(result.total_attempts))
    table.add_row("Total Duration", f"{result.total_duration_ms:.1f} ms")
    table.add_row("Summary", result.summary)

    if result.final_policy_decision:
        table.add_row(
            "Policy Decision",
            f"{result.final_policy_decision.level.value} (Risk: {result.final_policy_decision.risk_score})",
        )

    console.print(table)

    if result.successful_patch and result.successful_patch.unified_diff:
        console.print("\n[bold cyan]Verified Patch Unified Diff:[/bold cyan]")
        syntax = Syntax(result.successful_patch.unified_diff, "diff", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print(f"[bold green][OK] Patch Verified in Sandbox. Sandbox tests passing cleanly.[/bold green]\n")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "remediate"
    repo_arg = sys.argv[2] if len(sys.argv) > 2 else "demo_repo"

    if mode == "diagnose":
        run_diagnostics(repo_arg)
    else:
        run_remediation(repo_arg)
