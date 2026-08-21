"""GitHub Webhook receiver routes for autonomous CI failure ingestion."""

from typing import Any
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from nightshift.pipeline import NightShiftPipeline

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class WebhookResponse(BaseModel):
    status: str
    event: str
    action_taken: str
    incident_id: str | None = None
    repo: str | None = None


def _process_workflow_failure(repo_name: str, repo_path: str, test_cmd: str):
    """Background task to run the recovery pipeline."""
    pipeline = NightShiftPipeline()
    pipeline.execute_recovery(
        repo_path=repo_path,
        test_command=test_cmd,
        repo_name=repo_name,
        create_pr=False,
    )


@router.post("/github", response_model=WebhookResponse)
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default="workflow_run"),
):
    """Receive and parse GitHub Actions webhook events."""
    payload: dict[str, Any] = await request.json()

    if x_github_event == "ping":
        return WebhookResponse(
            status="received",
            event="ping",
            action_taken="Acknowledged ping from GitHub webhook.",
        )

    if x_github_event == "workflow_run":
        workflow_run = payload.get("workflow_run", {})
        action = payload.get("action")
        conclusion = workflow_run.get("conclusion")
        repo_info = payload.get("repository", {})
        repo_name = repo_info.get("full_name", "unknown/repo")

        # Check if this is a failed CI run
        if action == "completed" and conclusion == "failure":
            background_tasks.add_task(
                _process_workflow_failure,
                repo_name=repo_name,
                repo_path="nightshift-demo",
                test_cmd="pytest test_data_pipeline.py",
            )
            return WebhookResponse(
                status="queued",
                event="workflow_run",
                action_taken=f"CI failure detected in '{repo_name}'. Night Shift recovery pipeline scheduled.",
                repo=repo_name,
            )

        return WebhookResponse(
            status="ignored",
            event="workflow_run",
            action_taken=f"Workflow run '{workflow_run.get('name')}' status is '{conclusion}'. No remediation required.",
            repo=repo_name,
        )

    return WebhookResponse(
        status="ignored",
        event=x_github_event,
        action_taken=f"Event '{x_github_event}' is not monitored for CI recovery.",
    )
