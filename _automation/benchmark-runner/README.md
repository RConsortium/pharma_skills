# Skill Benchmark Runner

Automated benchmarking tool that compares AI agent performance **with** vs. **without** a skill, then posts scored results directly to the originating GitHub issue.

## How It Works

1. Scans the repo for any skill folder containing `evals/evals.json`
2. For each eval case, launches two sub-agents in parallel (one with the skill instructions, one without)
3. Scores both outputs against the assertions defined in the eval
4. Posts a structured comparison table as a comment on the linked GitHub issue

## Usage

### As a Cowork Scheduled Task

This skill is designed to be used as a [Cowork](https://claude.ai) scheduled task. Import `SKILL.md` as the task prompt and set it to manual trigger.

### As a Standalone Skill

Point any agents.md-compatible agent at this folder and ask it to "run benchmarks" or "compare skill performance".

## Report Format

Each benchmark posts a comment containing:

| Field | Description |
|---|---|
| **Eval ID** | Links back to the GitHub issue (e.g. `github-issue-2`) |
| **Model** | Which Claude model both agents used |
| **Skill version** | Git commit SHA of the skill's `SKILL.md` at time of run |
| **Scorecard** | Side-by-side pass/partial/fail counts |
| **Assertion breakdown** | Per-assertion comparison |
| **Verdict** | Summary of where the skill helped (or didn't) |

## Requirements

- GitHub CLI (`gh`) authenticated with write access to the repo, **or** Claude in Chrome as fallback
- Access to the Agent tool for parallel sub-agent execution

## License

MIT
