"""Manual and scheduled API trigger routes."""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nightshift.agent.diagnose import DiagnosticEngine, DiagnosticReport
from nightshift.pipeline import NightShiftPipeline, PipelineOutcome

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


class DiagnosticRequest(BaseModel):
    repo_path: str = "demo_repo"
    test_command: str = "pytest test_data_pipeline.py"


class RemediationRequest(BaseModel):
    repo_path: str = "demo_repo"
    test_command: str = "pytest test_data_pipeline.py"
    repo_name: str = "demo_repo"
    create_pr: bool = False


@router.post("/diagnose", response_model=DiagnosticReport)
async def trigger_diagnostic(req: DiagnosticRequest):
    """Execute safe diagnostic investigation on a repository."""
    target = Path(req.repo_path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Repository path '{req.repo_path}' not found.")

    engine = DiagnosticEngine()
    try:
        report = engine.run_diagnostic(str(target), test_command=req.test_command)
        return report
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.post("/remediate", response_model=PipelineOutcome)
async def trigger_remediation(req: RemediationRequest):
    """Execute full autonomous remediation and bounded self-correction loop."""
    target = Path(req.repo_path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Repository path '{req.repo_path}' not found.")

    pipeline = NightShiftPipeline()
    try:
        outcome = pipeline.execute_recovery(
            repo_path=str(target),
            test_command=req.test_command,
            repo_name=req.repo_name,
            create_pr=req.create_pr,
        )
        return outcome
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
