# Night Shift

**Autonomous Software Maintenance Agent**  
*Built with Strands Agents SDK for the AWS / Strands Agents Hackathon*

> "Your repository works the night shift too."  
> "Wake up to progress, not chores."

---

## Overview

Night Shift is an autonomous after-hours software maintenance worker that handles low-risk engineering chores, reproduces and remediates CI failures in an isolated sandbox, verifies every change, and wakes developers only when human judgment is required.

## Core Capabilities

1. **Autonomous CI Recovery**: Detects failed CI runs, extracts tracebacks, reproduces failures in a sandbox, generates minimal patches, verifies via test suite, and opens Pull Requests.
2. **Policy-Bounded Autonomy**: Deterministic safety engine enforcing strict boundaries (`AUTO_ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`). Zero unchecked mutations.
3. **Engineering Memory**: SQLite store tracking repository test conventions, package configurations, and past remediation patterns.
4. **Morning Briefing**: Clear operational summary of completed maintenance and items requiring review.
