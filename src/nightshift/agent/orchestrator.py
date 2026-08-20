"""Strands Agent Orchestrator for Night Shift."""

from typing import Any
from strands import Agent

from nightshift.agent.prompts import NIGHTSHIFT_SYSTEM_PROMPT
from nightshift.config import settings
from nightshift.tools.repo_tools import repo_list_files, repo_read_file, repo_search_text
from nightshift.tools.sandbox_tools import sandbox_apply_patch_file, sandbox_run_test_suite


def get_default_tools() -> list[Any]:
    """Retrieve the standard toolset for the Night Shift agent."""
    return [
        repo_list_files,
        repo_read_file,
        repo_search_text,
        sandbox_run_test_suite,
        sandbox_apply_patch_file,
    ]


def create_nightshift_agent(
    model: Any | None = None,
    tools: list[Any] | None = None,
) -> Agent:
    """Instantiate a configured Night Shift Strands Agent.
    
    Args:
        model: Optional LLM model instance (e.g. Bedrock Claude/Nova or mock model).
        tools: Optional custom list of tools.
    """
    selected_tools = tools if tools is not None else get_default_tools()
    
    return Agent(
        name="NightShiftOrchestrator",
        description="Autonomous after-hours software maintenance agent.",
        system_prompt=NIGHTSHIFT_SYSTEM_PROMPT,
        tools=selected_tools,
        model=model or settings.bedrock_model_id,
    )
