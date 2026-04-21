# Claude Code Benchmark Routine

This document provides instructions for setting up an automated benchmark routine in Claude Code to monitor skill performance.

## Prerequisites

- **Claude Code CLI** or **Gemini CLI** installed and authenticated.
- **GitHub CLI (`gh`)** authenticated with `repo` and `issue` permissions.
- **R Environment**: The routine uses a pre-flight script (`setup_r_env.sh`) to ensure R and required statistical packages are present.

## Routine Setup

### For Claude Code
Claude Code manages routines using the `/schedule` command. You can set it up interactively or via a single command.

**Option 1: Interactive Setup**
Simply type `/schedule` in the Claude Code interactive prompt and follow the guided setup:
1. **Name**: "Daily Skill Benchmark"
2. **Prompt**: "Requirement: Using R not Python to complete the work. Read the skill instructions from ./_automation/benchmark-runner/SKILL.md and follow every step exactly."
3. **Schedule**: Select "Daily" (or use a custom cron via `/schedule update` later).

**Option 2: Direct Command**
```bash
/schedule Daily Skill Benchmark: Requirement: Using R not Python to complete the work. Read the skill instructions from ./_automation/benchmark-runner/SKILL.md and follow every step exactly. at 2am
```

**Managing Routines:**
- **List**: `/schedule list`
- **Update (e.g., set cron)**: `/schedule update [ID]`
- **Run Immediately**: `/schedule run [ID]`

### For Gemini CLI
```bash
gemini routine create "Daily Skill Benchmark" \
  --prompt "Requirement: Using R not Python to complete the work. Read the skill instructions from ./_automation/benchmark-runner/SKILL.md and follow every step exactly." \
  --schedule "0 2 * * *"
```

## Prompt Best Practices

Routines run autonomously, so prompts must be **self-contained and explicit**. The core instruction used by this routine is:

> Requirement: Using R not Python to complete the work. If required R and R package is not available, stop the rest work. 
> 
> Read the skill instructions from the file at the path below, then execute them exactly:
>  
> File: ./_automation/benchmark-runner/SKILL.md
> 
> If that path is not accessible, try the workspace mount path or fetch from GitHub:
> https://github.com/RConsortium/pharma_skills/blob/main/_automation/benchmark-runner/SKILL.md
> 
> Follow every step in the SKILL.md. The skill is self-contained — it describes how to discover evals, run sub-agents, score results, and post to GitHub issues.

## Environment & Security

- **Secrets**: Ensure `GITHUB_TOKEN` is available in the routine's environment if `gh auth status` is not pre-configured.
- **Branch Safety**: By default, Claude Code routines only push to `claude/`-prefixed branches. This is the recommended setting for benchmark runs to avoid polluting protected branches.
- **Runner ID**: Use the `PHARMA_SKILLS_RUNNER_ID` environment variable to identify this runner in distributed benchmark selection.
- **Allowed Domains**: Ensure your routine's configuration allows access to R repositories and GitHub (see `.claude/settings.json`).

## How it Works

1. **Pre-flight**: Checks for R and required statistical packages via `setup_r_env.sh`.
2. **Discovery**: Runs the dispatcher to find the next pending evaluation for the current model.
3. **Execution**: Launches two isolated sub-agents in parallel (Agent A with skill, Agent B without).
4. **Scoring**: Scores the anonymized outputs against rubric assertions using a fresh scoring session.
5. **Reporting**: Packages artifacts into a zip, uploads to GitHub Releases, and posts a scorecard as a comment on the original issue.

## Troubleshooting

- **Permissions**: If the routine fails to post comments, verify `gh auth status` or your `GITHUB_TOKEN` scopes.
- **R Packages**: If R package installation fails, verify that the required domains (e.g., `cran.r-project.org`, `packagemanager.posit.co`) are in the allowed domains list.
- **Minimum Interval**: Note that Claude Code routines have a minimum execution interval of **one hour**.
