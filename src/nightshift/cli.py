"""Night Shift Command-Line Interface."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from nightshift.agent.diagnose import DiagnosticEngine
from nightshift.config import settings
from nightshift.memory.store import EngineeringMemoryStore
from nightshift.pipeline import NightShiftPipeline
from nightshift.remediation.models import RemediationStatus
from nightshift.reporting.briefing import MorningBriefingGenerator

# Force safe ASCII rendering on Windows console
console = Console(safe_box=True, highlight=False)


def run_diagnostics(repo_path: str = "nightshift-demo", test_cmd: str = "pytest test_data_pipeline.py"):
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
        policy_verdict = f"[{'green' if report.policy_check.allowed else 'red'}]{report.policy_check.level.value}[/]"
        table.add_row("Policy Engine Verdict", policy_verdict)
        table.add_row("Policy Reason", report.policy_check.reason)

    console.print(table)
    console.print("\n[bold green][OK] Diagnostic Complete.[/bold green]\n")


def run_pipeline(repo_path: str = "nightshift-demo", test_cmd: str = "pytest test_data_pipeline.py", create_pr: bool = False):
    """Execute end-to-end recovery pipeline with optional GitHub PR creation."""
    console.print(Panel.fit(
        "[bold cyan]NIGHT SHIFT[/bold cyan] - [white]Autonomous Software Maintenance Agent[/white]\n"
        f"[dim]Mode: End-to-End Recovery Pipeline (Create PR: {create_pr})[/dim]",
        border_style="cyan"
    ))

    target = Path(repo_path).resolve()
    console.print(f"[bold]Target Repository:[/bold] {target}")
    console.print(f"[bold]Test Command:[/bold] {test_cmd}")
    console.print("[dim]Executing sandbox remediation and policy verification...[/dim]\n")

    pipeline = NightShiftPipeline()
    outcome = pipeline.execute_recovery(
        repo_path=str(target),
        test_command=test_cmd,
        create_pr=create_pr,
    )

    res = outcome.remediation
    table = Table(title="Pipeline Workflow Outcome", show_header=True, header_style="bold magenta", safe_box=True)
    table.add_column("Property", style="cyan", width=25)
    table.add_column("Value / Details", style="white")

    status_color = "green" if res.status == RemediationStatus.RESOLVED else "yellow" if res.status == RemediationStatus.ALREADY_PASSING else "red"
    table.add_row("Status", f"[{status_color}]{res.status.value}[/{status_color}]")
    table.add_row("Incident ID", res.incident_id)
    table.add_row("Attempts Taken", str(res.total_attempts))
    table.add_row("Execution Duration", f"{outcome.duration_ms:.1f} ms")
    table.add_row("Summary", res.summary)

    if res.final_policy_decision:
        table.add_row(
            "Policy Decision",
            f"{res.final_policy_decision.level.value} ({res.final_policy_decision.reason})",
        )

    if outcome.pull_request:
        table.add_row("Pull Request URL", f"[bold green]{outcome.pull_request.url}[/bold green]")
        table.add_row("PR Branch", outcome.pull_request.branch)

    console.print(table)

    if res.successful_patch and res.successful_patch.unified_diff:
        console.print("\n[bold cyan]Verified Patch Unified Diff:[/bold cyan]")
        syntax = Syntax(res.successful_patch.unified_diff, "diff", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print(f"[bold green][OK] Verified in Sandbox. Ready for review.[/bold green]\n")


def run_morning_briefing(repo_name: str = "nightshift-demo"):
    """Generate and display the Morning Briefing from engineering memory."""
    memory_store = EngineeringMemoryStore()
    incidents = memory_store.get_recent_incidents(limit=10)
    session = memory_store.start_session(repo_name)
    closed_session = memory_store.close_session(
        session_id=session.session_id,
        incidents_handled=len(incidents),
        prs_opened=sum(1 for i in incidents if i.pr_url),
        blocked_count=sum(1 for i in incidents if "BLOCK" in i.status or "APPROVAL" in i.status),
    )

    generator = MorningBriefingGenerator()
    briefing = generator.generate(closed_session, incidents)
    generator.render_console(briefing, console)


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = args[0] if len(args) > 0 else "remediate"
    repo_arg = args[1] if len(args) > 1 else "nightshift-demo"
    create_pr_flag = "--pr" in args or mode == "pr"

    if mode == "diagnose":
        run_diagnostics(repo_arg)
    elif mode == "briefing":
        run_morning_briefing(repo_arg)
    else:
        run_pipeline(repo_arg, create_pr=create_pr_flag)
