"""Night Shift Command-Line Interface."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nightshift.agent.diagnose import DiagnosticEngine
from nightshift.config import settings

# Force safe ASCII rendering on Windows console
console = Console(safe_box=True, highlight=False)


def run_diagnostics(repo_path: str = "demo_repo", test_cmd: str = "pytest test_data_pipeline.py"):
    """Execute diagnostic sweep on target repository."""
    console.print(Panel.fit(
        "[bold cyan]NIGHT SHIFT[/bold cyan] - [white]Autonomous Software Maintenance Agent[/white]\n"
        "[dim]Running Milestone 1: Controlled Safe Diagnostic Verification[/dim]",
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
    console.print("\n[bold green][OK] Milestone 1 Verification Complete: Failure safely captured, parsed, and classified.[/bold green]\n")


if __name__ == "__main__":
    repo_arg = sys.argv[1] if len(sys.argv) > 1 else "demo_repo"
    run_diagnostics(repo_arg)
