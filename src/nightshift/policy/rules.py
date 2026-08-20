"""Deterministic safety rules and pattern definitions for Night Shift."""

import re

# File path blacklists (NEVER allow mutations on these paths)
BLOCKED_PATH_PATTERNS = [
    re.compile(r"^\.env.*", re.IGNORECASE),
    re.compile(r"^.*\.env.*", re.IGNORECASE),
    re.compile(r"^.*secrets?.*", re.IGNORECASE),
    re.compile(r"^.*credentials?.*", re.IGNORECASE),
    re.compile(r"^\.aws/.*", re.IGNORECASE),
    re.compile(r"^.*\.pem$", re.IGNORECASE),
    re.compile(r"^.*\.key$", re.IGNORECASE),
    re.compile(r"^.*\.p12$", re.IGNORECASE),
    re.compile(r"^migrations/.*", re.IGNORECASE),
    re.compile(r"^alembic/.*", re.IGNORECASE),
    re.compile(r"^\.github/workflows/deploy.*", re.IGNORECASE),
    re.compile(r"^\.github/workflows/release.*", re.IGNORECASE),
    re.compile(r"^terraform/.*", re.IGNORECASE),
    re.compile(r"^infra/.*", re.IGNORECASE),
]

# File path patterns that strictly require human approval
APPROVAL_REQUIRED_PATH_PATTERNS = [
    re.compile(r"^pyproject\.toml$", re.IGNORECASE),
    re.compile(r"^package\.json$", re.IGNORECASE),
    re.compile(r"^requirements.*\.txt$", re.IGNORECASE),
    re.compile(r"^Cargo\.toml$", re.IGNORECASE),
    re.compile(r"^docker-compose.*\.ya?ml$", re.IGNORECASE),
    re.compile(r"^Dockerfile.*", re.IGNORECASE),
    re.compile(r"^\.github/workflows/.*", re.IGNORECASE),
]

# Low-risk auto-allow path patterns
AUTO_ALLOW_PATH_PATTERNS = [
    re.compile(r"^README(\.md|\.rst)?$", re.IGNORECASE),
    re.compile(r"^docs/.*", re.IGNORECASE),
    re.compile(r"^tests?/.*", re.IGNORECASE),
    re.compile(r"^test_.*\.py$", re.IGNORECASE),
    re.compile(r"^src/.*", re.IGNORECASE),
    re.compile(r"^app/.*", re.IGNORECASE),
    re.compile(r"^lib/.*", re.IGNORECASE),
    re.compile(r"^pkg/.*", re.IGNORECASE),
    re.compile(r"^[^/]+\.py$", re.IGNORECASE),  # Root level python files (e.g. data_pipeline.py)
    re.compile(r"^[^/]+\.ts$", re.IGNORECASE),
    re.compile(r"^[^/]+\.js$", re.IGNORECASE),
]

# Blacklisted execution commands (sandbox or local)
BLOCKED_COMMAND_SUBSTRINGS = [
    "rm -rf /",
    "rm -rf ~",
    "sudo",
    "eval",
    "chmod -r 777",
    "chown",
    "curl -s",
    "wget",
    "nc -e",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "> /dev/sd",
]

# Maximum allowed lines in a single patch diff before requiring human approval
MAX_AUTO_DIFF_LINES = 150
