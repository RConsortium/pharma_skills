# Automation Skills

This directory contains automated workflows for managing, evaluating, and reporting on the `pharma_skills` ecosystem.

## Skills

| Folder | Name | Purpose |
|---|---|---|
| [`benchmark-runner/`](benchmark-runner/) | **Benchmark Runner** | Runs parallel "With Skill" vs. "Without Skill" evaluations to quantify skill performance. Posts results to GitHub issues. |
| [`issue-to-eval/`](issue-to-eval/) | **Issue to Eval** | Automatically syncs GitHub issues labeled `benchmark` into the local `_automation/evals/` directory. Supports updating existing tests if the issue content changes. |
| [`weekly-summary/`](weekly-summary/) | **Weekly Summary** | Aggregates repository activity (commits, PRs, issues) over the last 7 days and generates a concise status update for Slack. |

## Usage

Each skill contains a `SKILL.md` file that provides specific instructions for LLM agents to execute the workflow. To run a skill, point an agent at its directory or reference its `SKILL.md` content directly.

## Running as a Scheduled Job (Cloud CLI or CI/CD)

Automation skills can be scheduled as cloud-hosted jobs (e.g., Claude Code Routines, GitHub Actions, or custom Gemini CLI runners) that run on a cadence without your laptop being open.

Because these skills use R (via `Rscript`) to execute evaluations, the routine's cloud environment needs explicit CRAN network access and R installed. Follow the steps below.

### 1. Create a custom environment

If using a cloud CLI platform (like claude.ai/code, or equivalent Gemini/OpenAI cloud setups), create a new environment:

- **Name**: e.g. `pharma-skills-r`
- **Network access**: `Custom`
  - Check **"Also include default list of common package managers"** (keeps npm, PyPI, etc.)
  - Add the following domains, one per line:
    ```
    cran.r-project.org
    cloud.r-project.org
    r-lib.github.io
    packagemanager.posit.co
    *.r-project.org
    ```
- **Setup script** (installs R and pre-caches key packages — result is cached, runs once):
  ```bash
  #!/bin/bash
  bash _automation/benchmark-runner/scripts/setup_r_env.sh
  ```
  The script handles everything: installs R, system build libraries, pins CRAN to a
  stable IP to avoid DNS failures, bootstraps `pak`, and installs all required packages
  in parallel using pre-compiled binaries where available.

### 2. Create the routine

Go to [claude.ai/code/routines](https://claude.ai/code/routines) and click **New routine**:

| Field | Value |
|---|---|
| **Repository** | `RConsortium/pharma-skills` |
| **Environment** | The `pharma-skills-r` environment from step 1 |
| **Trigger** | Schedule — e.g. weekly on Monday at 09:00 |
| **Prompt** | See example below |

Example prompt for the benchmark runner:

```
Run the benchmark suite for all skills in this repository.
Follow the instructions in _automation/benchmark-runner/SKILL.md exactly.
Post results as comments on the relevant GitHub issues.
```

### 3. Verify CRAN access before the first scheduled run

Click **Run now** on the routine detail page and confirm that R package installation succeeds in the session log. If CRAN domains are missing, the setup script will fail with a network error — add the missing domain to the environment's custom allowlist and re-run.

### Notes

- **R is not pre-installed** in cloud sessions. The setup script above handles this; do not skip it.
- The setup script output is **cached** by Anthropic, so R and the pre-installed packages are available instantly on subsequent runs without reinstalling.
- Environment variables (e.g. `GH_TOKEN`, `GITHUB_TOKEN`, `PHARMA_SKILLS_RUNNER_ID`, `PHARMA_SKILLS_SLACK_CHANNEL`) are set in the environment config, not in `.claude/settings.json`. `GH_TOKEN` or `GITHUB_TOKEN` enables the benchmark runner's REST fallback when `gh` is unavailable. `PHARMA_SKILLS_RUNNER_ID` should be unique per person or scheduled worker to spread benchmark jobs across runners.
- The `.claude/settings.json` `permissions.allow` rules in this repo (e.g. `Bash(Rscript:*)`) apply to local CLI sessions only and have no effect on routine network access.
