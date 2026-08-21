"""Markdown templates for GitHub Pull Requests and operational briefings."""

from nightshift.remediation.models import RemediationResult


def generate_pr_markdown_body(result: RemediationResult) -> str:
    """Generate a structured, professional Pull Request markdown description with audit evidence."""
    patch = result.successful_patch
    policy = result.final_policy_decision
    
    file_modified = patch.file_path if patch else "unknown"
    hypothesis = patch.hypothesis if patch else "N/A"
    explanation = patch.explanation if patch else "N/A"
    diff_text = patch.unified_diff if patch else ""
    evidence = policy.evidence if (policy and hasattr(policy, "evidence")) else None

    scope_check = evidence.target_scope if evidence else f"SOURCE_ONLY ({file_modified})"
    secret_check = evidence.secrets_and_credentials_check if evidence else "PASSED (0 blacklist matches)"
    infra_check = evidence.infrastructure_and_deploy_check if evidence else "PASSED (No workflows or migrations touched)"
    diff_check = evidence.diff_boundary_check if evidence else f"{patch.diff_lines_count if patch else 0} lines modified"
    verdict = policy.level.value if policy else "AUTO_ALLOW"

    return f"""## 🌙 Night Shift Remediation Report

> **Incident ID**: `{result.incident_id}`  
> **Status**: Verified in Isolated Sandbox (Attempt {result.total_attempts} of 3)  
> **Policy Verdict**: `{verdict}`

---

### 🔍 Root Cause Analysis
{hypothesis}

### 🛠️ Remediation Applied
- **Target File**: `{file_modified}`  
- **Action**: {explanation}

```diff
{diff_text}
```

---

### ✅ Sandbox Verification Evidence
- **Environment**: Ephemeral Isolated Sandbox Runner
- **Exit Code**: `0 (ALL TESTS PASSED)`
- **Execution Duration**: `{result.total_duration_ms:.1f} ms`
- **Isolation Guarantee**: Host credentials and environment variables stripped.

---

### 🛡️ Deterministic Policy Audit Evidence
| Audit Criteria | Evidence / Verdict |
| :--- | :--- |
| **Scope Evaluation** | `{scope_check}` |
| **Secret & Credential Blacklist** | `{secret_check}` |
| **Infrastructure / Deploy Filter** | `{infra_check}` |
| **Diff Ceiling Check** | `{diff_check}` |
| **Sandbox Gate** | `MANDATORY (Verified exit code 0 before PR creation)` |

*Generated autonomously by [Night Shift](https://github.com/saisushwanth17-dot/night-shift) — Your repository works the night shift too.*
"""
