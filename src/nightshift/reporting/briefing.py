"""Morning Briefing operations report generator for Night Shift."""

from datetime import datetime
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nightshift.memory.models import IncidentRecord, MaintenanceSession


class BriefingDecision(BaseModel):
    """A direct decision or action item required from the developer."""

    title: str
    target: str
    reason: str
    action_prompt: str


class MorningBriefing(BaseModel):
    """Structured morning operational summary for the developer."""

    repo_name: str
    shift_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    duration_minutes: float
    completed_chores: list[str] = Field(default_factory=list)
    ready_for_review_prs: list[dict[str, str]] = Field(default_factory=list)
    blocked_tasks: list[dict[str, str]] = Field(default_factory=list)
    decisions_required: list[BriefingDecision] = Field(default_factory=list)


class MorningBriefingGenerator:
    """Compiles shift activity into an executive morning operations briefing."""

    def generate(
        self,
        session: MaintenanceSession,
        incidents: list[IncidentRecord],
    ) -> MorningBriefing:
        """Compile session incidents into structured morning briefing."""
        completed = []
        ready_prs = []
        blocked = []
        decisions = []

        for inc in incidents:
            if inc.status == "RESOLVED":
                chore_desc = f"Recovered CI failure in {inc.suspect_file} ({inc.failure_signature[:45]}...)"
                completed.append(chore_desc)
                if inc.pr_url:
                    ready_prs.append({
                        "title": f"PR {inc.incident_id}: Fix {inc.suspect_file}",
                        "url": inc.pr_url,
                        "branch": inc.pr_branch or "N/A",
                        "reason": f"Autonomous verification passed in sandbox ({inc.duration_ms:.0f}ms).",
                    })

            elif inc.status in ["BLOCKED_BY_POLICY", "REQUIRES_HUMAN_APPROVAL"]:
                blocked.append({
                    "target": inc.suspect_file,
                    "reason": inc.hypothesis or "Outside autonomous safety policy bounds.",
                    "status": inc.status,
                })
                decisions.append(BriefingDecision(
                    title=f"Review Blocked Modification in '{inc.suspect_file}'",
                    target=inc.suspect_file,
                    reason=inc.hypothesis or "High risk change detected.",
                    action_prompt=f"Review proposed changes in {inc.suspect_file} and decide whether to proceed.",
                ))

        return MorningBriefing(
            repo_name=session.repo_name,
            duration_minutes=session.duration_minutes,
            completed_chores=completed,
            ready_for_review_prs=ready_prs,
            blocked_tasks=blocked,
            decisions_required=decisions,
        )

    def format_markdown(self, briefing: MorningBriefing) -> str:
        """Format briefing as GitHub / Slack compatible Markdown."""
        lines = [
            f"# Good Morning - Night Shift Operations Briefing",
            f"**Repository**: `{briefing.repo_name}` | **Shift Date**: `{briefing.shift_date}` | **Runtime**: `{briefing.duration_minutes:.1f} minutes`",
            "",
            "---",
            "",
            "### [COMPLETED] Maintenance Chores",
        ]
        if briefing.completed_chores:
            for chore in briefing.completed_chores:
                lines.append(f"- [OK] {chore}")
        else:
            lines.append("- *No completed chores in this shift.*")

        lines.extend(["", "### [READY FOR REVIEW] Pull Requests"])
        if briefing.ready_for_review_prs:
            for pr in briefing.ready_for_review_prs:
                lines.append(f"- **[{pr['title']}]({pr['url']})** (`{pr['branch']}`)")
                lines.append(f"  *Reason*: {pr['reason']}")
        else:
            lines.append("- *No new Pull Requests pending review.*")

        lines.extend(["", "### [BLOCKED] Outside Autonomy Policy"])
        if briefing.blocked_tasks:
            for blk in briefing.blocked_tasks:
                lines.append(f"- **Target**: `{blk['target']}` (`{blk['status']}`)")
                lines.append(f"  *Reason*: {blk['reason']}")
        else:
            lines.append("- *No blocked tasks.*")

        lines.extend(["", "### [ACTION ITEMS] Your Decisions Today"])
        if briefing.decisions_required:
            for idx, dec in enumerate(briefing.decisions_required, 1):
                lines.append(f"{idx}. **{dec.title}**")
                lines.append(f"   - Target: `{dec.target}`")
                lines.append(f"   - Prompt: {dec.action_prompt}")
        else:
            lines.append("- *Zero human decisions required. You are clear to focus on high-leverage work.*")

        lines.extend([
            "",
            "---",
            "*Generated by [Night Shift](https://github.com/saisushwanth17-dot/night-shift) - Wake up to progress, not chores.*",
        ])
        return "\n".join(lines)

    def render_console(self, briefing: MorningBriefing, console: Console) -> None:
        """Render rich console visualization of the morning briefing."""
        console.print(Panel.fit(
            f"[bold cyan]NIGHT SHIFT[/bold cyan] - [bold white]Morning Operations Briefing[/bold white]\n"
            f"[dim]Repository: {briefing.repo_name} | Shift Date: {briefing.shift_date} | Runtime: {briefing.duration_minutes:.1f} mins[/dim]",
            border_style="cyan",
        ))

        # Completed
        table_completed = Table(title="[bold green]Completed Maintenance Chores[/bold green]", safe_box=True)
        table_completed.add_column("Chore Description", style="white")
        if briefing.completed_chores:
            for c in briefing.completed_chores:
                table_completed.add_row(f"[green][OK][/green] {c}")
        else:
            table_completed.add_row("[dim]None[/dim]")
        console.print(table_completed)

        # Ready PRs
        if briefing.ready_for_review_prs:
            table_prs = Table(title="[bold yellow]Ready for Review PRs[/bold yellow]", safe_box=True)
            table_prs.add_column("PR Title", style="cyan")
            table_prs.add_column("Branch", style="magenta")
            table_prs.add_column("Reason / Evidence", style="white")
            for pr in briefing.ready_for_review_prs:
                table_prs.add_row(pr["title"], pr["branch"], pr["reason"])
            console.print(table_prs)

        # Blocked
        if briefing.blocked_tasks:
            table_blocked = Table(title="[bold red]Blocked / Outside Autonomy Policy[/bold red]", safe_box=True)
            table_blocked.add_column("Target", style="red")
            table_blocked.add_column("Status", style="yellow")
            table_blocked.add_column("Reason", style="white")
            for b in briefing.blocked_tasks:
                table_blocked.add_row(b["target"], b["status"], b["reason"])
            console.print(table_blocked)

        # Decisions
        if briefing.decisions_required:
            console.print("\n[bold yellow]Human Decisions Required:[/bold yellow]")
            for idx, dec in enumerate(briefing.decisions_required, 1):
                console.print(f"  [bold cyan]{idx}. {dec.title}[/bold cyan]: {dec.action_prompt}")
        else:
            console.print("\n[bold green][OK] Zero human decisions required. Runway cleared![/bold green]\n")
