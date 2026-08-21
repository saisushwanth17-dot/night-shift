"""Morning Briefing and Engineering Memory query routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from nightshift.memory.models import IncidentRecord, RepoProfile
from nightshift.memory.store import EngineeringMemoryStore
from nightshift.reporting.briefing import MorningBriefing, MorningBriefingGenerator

router = APIRouter(prefix="/api", tags=["Briefing & Memory"])


class BriefingResponse(BaseModel):
    briefing: MorningBriefing
    markdown: str


@router.get("/briefing", response_model=BriefingResponse)
async def get_morning_briefing(repo_name: str = Query(default="demo_repo")):
    """Generate and return the Morning Briefing in JSON and Markdown formats."""
    store = EngineeringMemoryStore()
    incidents = store.get_recent_incidents(repo_name=repo_name, limit=10)
    session = store.start_session(repo_name=repo_name)
    closed = store.close_session(
        session_id=session.session_id,
        incidents_handled=len(incidents),
        prs_opened=sum(1 for i in incidents if i.pr_url),
        blocked_count=sum(1 for i in incidents if "BLOCK" in i.status or "APPROVAL" in i.status),
    )

    generator = MorningBriefingGenerator()
    briefing = generator.generate(closed, incidents)
    markdown_text = generator.format_markdown(briefing)

    return BriefingResponse(briefing=briefing, markdown=markdown_text)


@router.get("/incidents", response_model=list[IncidentRecord])
async def list_recent_incidents(
    repo_name: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List recent incident records from Engineering Memory."""
    store = EngineeringMemoryStore()
    return store.get_recent_incidents(repo_name=repo_name, limit=limit)


@router.get("/profiles/{repo_name:path}", response_model=RepoProfile)
async def get_repo_profile(repo_name: str):
    """Retrieve saved engineering conventions profile for a repository."""
    store = EngineeringMemoryStore()
    profile = store.get_repo_profile(repo_name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile found for repository '{repo_name}'.")
    return profile
