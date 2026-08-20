"""Diff utilities for patch analysis and reporting."""

import difflib
from pathlib import Path


def generate_unified_diff(
    original_text: str,
    modified_text: str,
    file_path: str = "file",
) -> tuple[str, int]:
    """Generate a clean unified diff and count modified/added/deleted lines.
    
    Returns:
        tuple[unified_diff_str, total_diff_lines]
    """
    orig_lines = original_text.splitlines(keepends=True)
    mod_lines = modified_text.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    ))

    diff_str = "".join(diff_lines)
    # Count meaningful diff lines (+ and -, excluding headers)
    change_count = sum(1 for line in diff_lines if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))

    return diff_str, change_count
