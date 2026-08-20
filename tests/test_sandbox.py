"""Unit tests for the sandbox execution environment."""

from pathlib import Path
import pytest
from nightshift.sandbox.runner import LocalIsolatedRunner


@pytest.fixture
def sample_workspace(tmp_path):
    demo_dir = tmp_path / "sample_repo"
    demo_dir.mkdir()
    (demo_dir / "app.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
    (demo_dir / "test_app.py").write_text(
        "from app import hello\ndef test_hello(): assert hello() == 'world'\n",
        encoding="utf-8",
    )
    return demo_dir


def test_sandbox_setup_and_execution(sample_workspace):
    runner = LocalIsolatedRunner()
    try:
        ws_path = runner.setup_workspace(sample_workspace)
        assert ws_path.exists()
        assert (ws_path / "app.py").exists()

        # Run pytest inside sandbox
        result = runner.run_command("pytest test_app.py")
        assert result.success is True
        assert result.exit_code == 0
        assert "passed" in result.stdout.lower()
    finally:
        runner.cleanup()


def test_sandbox_file_mutation(sample_workspace):
    runner = LocalIsolatedRunner()
    try:
        runner.setup_workspace(sample_workspace)
        # Edit file in sandbox
        runner.write_file("new_module.py", "CONSTANT = 42\n")
        assert runner.read_file("new_module.py") == "CONSTANT = 42\n"

        # Original source directory must NOT be modified
        assert not (sample_workspace / "new_module.py").exists()
    finally:
        runner.cleanup()
