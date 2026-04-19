# pharma_skills — Agent Instructions

## Repository Overview

This repository is a collection of agent skills for pharmaceutical R&D, built for Claude Code and compatible LLM agents. Skills follow the [agentskills.io](https://agentskills.io) specification.

## Directory Structure

```
pharma_skills/
├── group-sequential-design/   ← Main clinical trial design skill
│   ├── SKILL.md               ← Agent workflow instructions
│   ├── evals/evals.json       ← Benchmark test cases
│   └── scripts/               ← Supporting R and Python scripts
├── _automation/               ← Automation skills (see below)
│   ├── benchmark-runner/      ← A/B benchmark orchestration
│   ├── issue-to-eval/         ← GitHub Issue → evals.json converter
│   └── weekly-summary/        ← Weekly activity → Slack
└── .github/
    ├── ISSUE_TEMPLATE/benchmark.md  ← Template for benchmark issues
    └── workflows/             ← CI: skill validation + benchmark scheduling
```

## Available Skills and Trigger Phrases

| Skill | When to invoke |
|---|---|
| `group-sequential-design` | "design a Phase 3 trial", "group sequential design", "alpha spending", "interim analysis planning" |
| `benchmark-runner` | "run benchmarks", "compare skill performance", "eval the skills" |
| `issue-to-eval` | "parse this issue into a benchmark", "sync all benchmark issues" |
| `weekly-summary` | "generate weekly summary", "post to Slack" |

## Agent Guardrails

- **Do NOT edit `evals/evals.json` directly.** Use the `issue-to-eval` skill to add or update evaluation cases from GitHub Issues.
- **Do NOT run `benchmark-runner` unless explicitly requested.** It spawns sub-agents and posts to GitHub Issues.
- **Do NOT modify files in `_automation/` unless the task specifically targets automation.** The automation skills are self-contained.
- When running scripts, invoke them from the repository root so relative paths resolve correctly.

## Environment Variables

| Variable | Used by | Purpose |
|---|---|---|
| `PHARMA_SKILLS_SLACK_CHANNEL` | `weekly-summary` | Slack channel ID for posting. If unset, the skill reads from `_automation/weekly-summary/config.json`. |

## Contributing

See `LIFECYCLE.md` for the full skill development lifecycle (Design → Development → Evaluation → Release).
