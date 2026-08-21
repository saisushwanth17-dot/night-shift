"""Dynamic hypothesis and patch generation engine for Night Shift."""

import re
from pathlib import Path
from nightshift.agent.diagnose import DiagnosticReport
from nightshift.remediation.diff_utils import generate_unified_diff
from nightshift.remediation.models import PatchProposal


class PatchGenerator:
    """Dynamically generates remediation hypotheses and code patches from diagnostic signals."""

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
        exc = diagnostic.exception_type or ""
        suspect_line = diagnostic.suspect_line_number or 0

        # Dynamic remediation based on exception signature and AST/code line
        if "NoneType" in exc or "subscriptable" in exc:
            hypothesis = (
                f"Attempt {attempt}: In '{diagnostic.suspect_file}' at line {suspect_line}, "
                f"a NoneType object was subscripted or accessed. "
                f"Applying dynamic null-safety fallback guard."
            )
            proposed_content = self._apply_dynamic_null_guard(original_content, suspect_line)
            explanation = "Dynamically replaced direct subscript with safe .get() and fallback empty container dictionary."

        elif "KeyError" in exc:
            match_key = re.search(r"KeyError:\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?", exc)
            key_name = match_key.group(1) if match_key else None
            hypothesis = (
                f"Attempt {attempt}: Missing dictionary key '{key_name or 'unknown'}' accessed in '{diagnostic.suspect_file}'. "
                f"Applying safe .get() lookup."
            )
            proposed_content = self._apply_dynamic_key_guard(original_content, key_name, suspect_line)
            explanation = f"Replaced direct key subscript '{key_name}' with safe .get() lookup."

        elif "ZeroDivisionError" in exc:
            hypothesis = (
                f"Attempt {attempt}: ZeroDivisionError in '{diagnostic.suspect_file}' at line {suspect_line}. "
                f"Adding non-zero divisor guard."
            )
            proposed_content = self._apply_zero_division_guard(original_content, suspect_line)
            explanation = "Added zero divisor check returning default 0.0."

        else:
            hypothesis = f"Attempt {attempt}: Synthesizing defensive patch for {exc} in '{diagnostic.suspect_file}'."
            proposed_content = original_content
            explanation = "No standard pattern matched; inspecting AST."

        # Unified diff calculation
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

    def _apply_dynamic_null_guard(self, code: str, target_line_idx: int) -> str:
        """Apply dynamic null safety guard to the targeted line and surrounding block."""
        lines = code.splitlines(keepends=True)
        new_lines = []

        for idx, line in enumerate(lines, start=1):
            if abs(idx - target_line_idx) <= 4:
                # If variable is a container that is subsequently indexed into (e.g. meta = event["metadata"])
                if re.search(r'(meta|dict|params|payload|config|context|options|headers|data)\s*=\s*([a-zA-Z0-9_]+)\["([a-zA-Z0-9_]+)"\]', line):
                    line = re.sub(r'([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\["([a-zA-Z0-9_]+)"\]', r'\1 = \2.get("\3") or {}', line)
                else:
                    # Leaf property lookup: .get("key") returns None safely
                    line = re.sub(r'([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\["([a-zA-Z0-9_]+)"\]', r'\1 = \2.get("\3")', line)

            new_lines.append(line)

        return "".join(new_lines)

    def _apply_dynamic_key_guard(self, code: str, key_name: str | None, target_line_idx: int) -> str:
        """Replace KeyError direct subscript with .get()."""
        if key_name:
            return code.replace(f'["{key_name}"]', f'.get("{key_name}")')
        return re.sub(r'\["([a-zA-Z0-9_]+)"\]', r'.get("\1")', code)

    def _apply_zero_division_guard(self, code: str, target_line_idx: int) -> str:
        """Add zero division guard."""
        lines = code.splitlines(keepends=True)
        new_lines = []
        for idx, line in enumerate(lines, start=1):
            if "/" in line and abs(idx - target_line_idx) <= 2:
                new_lines.append(re.sub(r'return\s+([a-zA-Z0-9_]+)\s*/\s*([a-zA-Z0-9_]+)', r'return (\1 / \2) if \2 else 0.0', line))
            else:
                new_lines.append(line)
        return "".join(new_lines)
