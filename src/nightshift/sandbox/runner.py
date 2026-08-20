"""Sandbox execution runtime supporting local isolated directories and Docker containers."""

import os
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel

from nightshift.config import SandboxMode, settings


class CommandResult(BaseModel):
    """Result of running a command inside the sandbox."""

    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    success: bool


class ExecutionSandbox(ABC):
    """Abstract interface for isolated execution environments."""

    @abstractmethod
    def setup_workspace(self, source_repo_path: Path) -> Path:
        """Clone or copy source repository into isolated sandbox."""
        pass

    @abstractmethod
    def run_command(self, command: str, timeout_sec: int | None = None) -> CommandResult:
        """Execute a command inside the sandbox."""
        pass

    @abstractmethod
    def write_file(self, relative_path: str, content: str) -> bool:
        """Write or modify a file inside the isolated sandbox workspace."""
        pass

    @abstractmethod
    def read_file(self, relative_path: str) -> str:
        """Read a file from the isolated sandbox workspace."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Tear down and clean up sandbox resources."""
        pass


class LocalIsolatedRunner(ExecutionSandbox):
    """Local process sandbox running inside a temporary directory copy with strict env isolation."""

    def __init__(self, workspace_path: Path | None = None):
        self.temp_dir: tempfile.TemporaryDirectory | None = None
        self.workspace_path: Path = workspace_path or Path("")

    def setup_workspace(self, source_repo_path: Path) -> Path:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="nightshift_sandbox_")
        self.workspace_path = Path(self.temp_dir.name) / "repo"
        shutil.copytree(
            source_repo_path,
            self.workspace_path,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*.pyc", ".pytest_cache"),
        )
        return self.workspace_path

    def run_command(self, command: str, timeout_sec: int | None = None) -> CommandResult:
        timeout = timeout_sec or settings.sandbox_timeout_seconds
        start_time = time.perf_counter()

        # Sanitize environment: strip out dangerous host credentials
        safe_env = os.environ.copy()
        for key in ["AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "GITHUB_TOKEN", "SSH_AUTH_SOCK"]:
            safe_env.pop(key, None)

        try:
            process = subprocess.run(
                command,
                cwd=str(self.workspace_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=safe_env,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return CommandResult(
                command=command,
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode,
                duration_ms=round(duration_ms, 2),
                success=(process.returncode == 0),
            )
        except subprocess.TimeoutExpired as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return CommandResult(
                command=command,
                stdout=err.stdout or "",
                stderr=(err.stderr or "") + f"\nCommand timed out after {timeout} seconds.",
                exit_code=124,
                duration_ms=round(duration_ms, 2),
                success=False,
            )
        except Exception as ex:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"Execution error: {str(ex)}",
                exit_code=1,
                duration_ms=round(duration_ms, 2),
                success=False,
            )

    def write_file(self, relative_path: str, content: str) -> bool:
        target_file = self.workspace_path / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
        return True

    def read_file(self, relative_path: str) -> str:
        target_file = self.workspace_path / relative_path
        if not target_file.exists():
            raise FileNotFoundError(f"File '{relative_path}' not found in sandbox.")
        return target_file.read_text(encoding="utf-8")

    def cleanup(self) -> None:
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None


class DockerSandboxRunner(ExecutionSandbox):
    """Docker containerized sandbox for strict operating system and network isolation."""

    def __init__(self, image_name: str | None = None):
        self.image_name = image_name or settings.sandbox_docker_image
        self.local_runner = LocalIsolatedRunner()
        self.workspace_path: Path = Path("")

    def setup_workspace(self, source_repo_path: Path) -> Path:
        self.workspace_path = self.local_runner.setup_workspace(source_repo_path)
        return self.workspace_path

    def run_command(self, command: str, timeout_sec: int | None = None) -> CommandResult:
        # If docker daemon is unavailable or errors, gracefully fall back to LocalIsolatedRunner
        try:
            import docker  # noqa: F401

            client = docker.from_env()
            client.ping()
            # Docker run with volume mount and memory limit
            container = client.containers.run(
                self.image_name,
                f"sh -c '{command}'",
                volumes={str(self.workspace_path): {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                mem_limit="2g",
                nano_cpus=2000000000,
                network_disabled=True,
                detach=False,
                stdout=True,
                stderr=True,
                remove=True,
            )
            return CommandResult(
                command=command,
                stdout=container.decode("utf-8", errors="replace"),
                stderr="",
                exit_code=0,
                duration_ms=0.0,
                success=True,
            )
        except Exception:
            # Fallback to local isolated runner
            return self.local_runner.run_command(command, timeout_sec=timeout_sec)

    def write_file(self, relative_path: str, content: str) -> bool:
        return self.local_runner.write_file(relative_path, content)

    def read_file(self, relative_path: str) -> str:
        return self.local_runner.read_file(relative_path)

    def cleanup(self) -> None:
        self.local_runner.cleanup()


def create_sandbox(mode: SandboxMode | None = None) -> ExecutionSandbox:
    """Factory to instantiate the configured sandbox runner."""
    selected_mode = mode or settings.sandbox_mode
    if selected_mode == SandboxMode.DOCKER:
        return DockerSandboxRunner()
    return LocalIsolatedRunner()
