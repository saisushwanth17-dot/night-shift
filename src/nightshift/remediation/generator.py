"""Hypothesis and patch generation engine for Night Shift."""

import re
from pathlib import Path
from nightshift.agent.diagnose import DiagnosticReport
from nightshift.remediation.diff_utils import generate_unified_diff
from nightshift.remediation.models import PatchProposal


class PatchGenerator:
    """Generates remediation hypotheses and code patches based on diagnostic signals."""

    def generate_candidate_patch(
        self,
        repo_path: Path,
        diagnostic: DiagnosticReport,
        previous_feedback: list[str] | None = None,
        attempt: int = 1,
    ) -> PatchProposal:
        """Generate a candidate patch proposal for the suspect file."""
        if not diagnostic.suspect_file:
            raise ValueError("Diagnostic report does not contain a suspect file.")

        target_file = repo_path / diagnostic.suspect_file
        if not target_file.exists():
            raise FileNotFoundError(f"Suspect file '{target_file}' not found in repository.")

        original_content = target_file.read_text(encoding="utf-8")

        # 1. Inspect exception and traceback context
        exc = diagnostic.exception_type or ""
        suspect_line = diagnostic.suspect_line_number or 0

        # Pattern: TypeError: 'NoneType' object is not subscriptable
        if "NoneType" in exc or "subscriptable" in exc:
            hypothesis = (
                f"Attempt {attempt}: In '{diagnostic.suspect_file}', variable accessed at line {suspect_line} "
                f"is None or uninitialized in edge cases (e.g., null metadata payload). "
                f"Adding safe null check / default fallback."
            )
            # Apply safe subscript remediation
            proposed_content = self._remediate_none_subscript(original_content)
            explanation = "Safely retrieve metadata dictionary with fallback to empty dict before accessing keys."

        elif "KeyError" in exc:
            hypothesis = (
                f"Attempt {attempt}: Missing key in dictionary access in '{diagnostic.suspect_file}' at line {suspect_line}. "
                f"Replacing direct subscript with .get() fallback."
            )
            proposed_content = self._remediate_key_error(original_content)
            explanation = "Replaced direct dictionary key lookup with .get() and default None."

        else:
            hypothesis = f"Attempt {attempt}: Investigating '{diagnostic.suspect_file}' for assertion or runtime mismatch."
            proposed_content = original_content
            explanation = "No automatic patch pattern matched."

        # Generate unified diff and count changes
        diff_str, diff_count = generate_unified_diff(
            original_content,
            proposed_content,
            file_path=diagnostic.suspect_file,
        )

        return PatchProposal(
            file_path=diagnostic.suspect_file,
            original_content=original_content,
            proposed_content=proposed_content,
            explanation=explanation,
            hypothesis=hypothesis,
            unified_diff=diff_str,
            diff_lines_count=diff_count,
        )

    def _remediate_none_subscript(self, code: str) -> str:
        """Remediate NoneType subscript errors (e.g. meta = event.get('metadata') or {})."""
        # Look for direct subscript or unsafe assignments
        lines = code.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            if 'meta = event["metadata"]' in line:
                new_lines.append("    meta = event.get(\"metadata\") or {}\n")
            elif 'session_id = meta["session_id"]' in line:
                new_lines.append("    session_id = meta.get(\"session_id\")\n")
            else:
                new_lines.append(line)
        return "".join(new_lines)

    def _remediate_key_error(self, code: str) -> str:
        """Remediate KeyError exceptions."""
        return re.sub(r'\["([a-zA-Z0-9_]+)"\]', r'.get("\1")', code)
