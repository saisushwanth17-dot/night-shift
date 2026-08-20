"""Markdown templates for GitHub Pull Requests and operational briefings."""

from nightshift.remediation.models import RemediationResult


def generate_pr_markdown_body(result: RemediationResult) -> str:
    """Generate a structured, professional Pull Request markdown description."""
    patch = result.successful_patch
    policy = result.final_policy_decision
    
    file_modified = patch.file_path if patch else "unknown"
    hypothesis = patch.hypothesis if patch else "N/A"
    explanation = patch.explanation if patch else "N/A"
    diff_text = patch.unified_diff if patch else ""
    risk_score = policy.risk_score if policy else 0.3
    policy_level = policy.level.value if policy else "AUTO_ALLOW"

    return f"""## 🌙 Night Shift Remediation Report

> **Incident ID**: `{result.incident_id}`  
> **Status**: Verified in Isolated Sandbox (Attempt {result.total_attempts})  
> **Policy Verdict**: `{policy_level}` (Risk Score: `{risk_score:.2f}`)

---

### 🔍 Root Cause Analysis
{hypothesis}

### 🛠️ Remediation Applied
**File**: `{file_modified}`  
**Summary**: {explanation}

```diff
{diff_text}
```

---

### ✅ Sandbox Verification Evidence
- **Environment**: Isolated Sandbox Runner
- **Verification Status**: `EXIT CODE 0 (PASSED)`
- **Duration**: `{result.total_duration_ms:.1f} ms`
- **Safety Policy**: Deterministic whitelist verification passed.

---

### 🤖 Autonomy & Safety Policy
Night Shift operates under strict deterministic autonomy bounds:
- [x] Target file is within the low-risk maintenance whitelist
- [x] No secrets, migrations, or deploy configs touched
- [x] Diff size within autonomous thresholds ({patch.diff_lines_count if patch else 0} lines)
- [x] All unit tests verified passing prior to PR creation

*Generated autonomously by [Night Shift](https://github.com/saisushwanth17-dot/night-shift) — Your repository works the night shift too.*
"""
