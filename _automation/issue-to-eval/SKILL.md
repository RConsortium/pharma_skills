---
name: issue-to-eval
description: Converts one or more GitHub Issues into standardized benchmark data using automated scripts. Use when a user provides an issue number or URL and wants to add it to the evaluation suite.
---

# Issue to Eval

Converts GitHub Issues into standardized benchmark evaluation cases (JSON) and saves them to the `_automation/evals/` directory. It automatically discovers new issues labeled `benchmark` and updates existing evaluations if the issue content has been modified.

## Task Flow

### Option A: Sync All Benchmarks (Recommended)
Use this to automatically identify and update all evaluations from GitHub:
```bash
python3 _automation/issue-to-eval/scripts/sync_benchmarks.py
```
- Discovers all issues with the `benchmark` label.
- Compares each issue against the local files in `evals/`.
- Adds new cases and updates existing ones if the prompt or assertions have changed.

### Option B: Import Specific Issue
Use this for a one-off import or testing:
```bash
python3 _automation/issue-to-eval/scripts/import_issue_eval.py --issue {ISSUE_NUMBER_OR_URL}
```
   
## Review Output
- Report the status for each issue (Success/Updated/Skipped/Error) to the user.
- If an issue is modified on GitHub, running the sync script will propagate those changes to the local evaluation suite.

## Requirements
- The issue MUST follow the standard benchmark template with headers: `## Skills`, optional `## Language`, `## Query`, `## Expected Output`, `## Attached Files / Input Context`, and `## Rubric Criteria (Assertions)`.
- `## Skills` may contain one or more skill names, one per line or comma-separated. The generated eval stores them in `target_skills`.
- `## Language` is optional. When present, the generated eval stores it in `language` so the benchmark runner can pass the same language constraint to both agents.
