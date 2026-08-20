"""Sandbox execution and testing tools for the Strands Agent."""

from pathlib import Path
from strands import tool

from nightshift.policy.engine import PolicyEngine
from nightshift.sandbox.runner import create_sandbox

policy_engine = PolicyEngine()


@tool
def sandbox_run_test_suite(repo_path: str, test_command: str = "pytest") -> dict:
    """Execute a test command or test suite inside an isolated sandbox environment.
    
    Args:
        repo_path: Path to the target repository directory.
        test_command: Test execution command to run (e.g., 'pytest test_data_pipeline.py').
    """
    # 1. Policy Gate
    decision = policy_engine.evaluate_command(test_command)
    if not decision.allowed:
        return {
            "success": False,
            "blocked": True,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
        }

    # 2. Setup Sandbox
    sandbox = create_sandbox()
    try:
        source_path = Path(repo_path).resolve()
        if not source_path.exists():
            return {"success": False, "error": f"Repo path '{repo_path}' does not exist."}

        sandbox.setup_workspace(source_path)
        cmd_result = sandbox.run_command(test_command)

        return {
            "success": cmd_result.success,
            "exit_code": cmd_result.exit_code,
            "stdout": cmd_result.stdout,
            "stderr": cmd_result.stderr,
            "duration_ms": cmd_result.duration_ms,
            "command": cmd_result.command,
        }
    finally:
        sandbox.cleanup()


@tool
def sandbox_apply_patch_file(repo_path: str, relative_file_path: str, new_content: str) -> dict:
    """Apply a modified file patch inside the isolated sandbox after policy verification.
    
    Args:
        repo_path: Path to the target repository directory.
        relative_file_path: Relative path of the file to modify.
        new_content: Full content of the proposed updated file.
    """
    diff_lines = len(new_content.splitlines())
    decision = policy_engine.evaluate_file_mutation(relative_file_path, diff_lines_count=diff_lines)

    if not decision.allowed:
        return {
            "success": False,
            "blocked": True,
            "requires_human": decision.requires_human,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "file_path": relative_file_path,
        }

    return {
        "success": True,
        "policy_verdict": decision.level.value,
        "risk_score": decision.risk_score,
        "file_path": relative_file_path,
        "message": f"File mutation on '{relative_file_path}' passed policy check ({decision.level.value}).",
    }
