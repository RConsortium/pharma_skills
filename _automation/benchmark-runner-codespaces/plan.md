# Benchmark Runner (Codespaces) — Improvement Plan

Captured from the 2026-05-05 review. The user asked the agent to execute SKILL.md
end-to-end inside a Codespace within ~30 min. That budget is structurally
infeasible with the current design (R bootstrap + sequential Phase 1 / Phase 2
scheduled 5 h apart). This document is the digest of why, and the concrete
fixes — ordered roughly by impact-per-effort.

---

## Why a single 30-min run is not currently possible

Fresh Codespace observations:

- R is not installed (`/usr/lib/R` missing, `command -v R` empty).
- `setup_r_env.sh` would `apt install r-base` + compile `pak` from source +
  install 8 R packages (`gsDesign`, `gsDesign2`, `lrstat`, `graphicalMCP`,
  `eventPred`, `ggplot2`, `jsonlite`, `digest`).
- Realistic timing on a fresh Ubuntu 24.04 codespace:
  - R env bootstrap: **20–40 min**
  - Agent A run: **10–15 min**
  - Agent B run: **10–15 min**
  - Scoring + post: **3–5 min**
  - **Total: 45–75 min minimum**, before the deliberate 5-h gap between
    Phase 1 and Phase 2.
- SKILL.md states "*One phase executed per invocation (~20 min each)*" and is
  scheduled `0 1,6 * * *`. Total walltime is by design > 5 h.

---

## 1. Delayed R-environment install

**Root cause.** Every Phase-1 invocation re-runs `setup_r_env.sh` from scratch:

- `apt update` + `apt install r-base` (~3–5 min)
- `pin_host` to CRAN via curl (~10 s, sometimes slow)
- Compile `pak` from source against system libcurl/openssl (~3–5 min)
- Install 8 packages — even via Posit PPM binaries (~5–10 min); from CRAN
  source it's 15–25 min.

### Fixes (in order of impact)

| # | Fix | Effort | Saving |
|---|---|---|---|
| 1.1 | **Bake R + packages into the codespace image** via `.devcontainer/devcontainer.json` (`features: { "ghcr.io/rocker-org/devcontainer-features/r-rig": {} }`) plus a post-create script that runs `setup_r_env.sh` once at image build. New codespaces start with R warm. | M | 20–35 min/run |
| 1.2 | **Persist `~/R/x86_64-pc-linux-gnu-library/4.x/`** to a workspace-mounted volume so packages survive codespace rebuilds. Add the path to `.devcontainer` mounts. | S | 10–15 min/run |
| 1.3 | **Short-circuit in `setup_r_env.sh`**: if `Rscript -e 'all(c("gsDesign","gsDesign2",...) %in% rownames(installed.packages()))'` returns `TRUE`, exit 0 immediately. (The script already partially does this; ensure it short-circuits before `apt update`.) | S | 30–60 s/run |
| 1.4 | **Use only PPM binaries**: force `repo_url = ppm_url` for Ubuntu 24.04 (`noble`); never fall back to CRAN source. PPM noble binaries exist for all required packages. | S | 5–10 min/run |
| 1.5 | **Run R setup in background while Agent A's prompt is being assembled** — Agent A doesn't need R until it actually executes scripts; you can overlap setup with eval-discovery and prompt staging. | S | 1–3 min/run |

---

## 2. Parallel Agent A and Agent B

**Root cause.** SKILL.md splits A and B across two scheduled invocations
explicitly to dodge Claude's 5-h usage-window cap. State is persisted via a
`BENCHMARK_PARTIAL` GitHub-issue marker.

### Fixes

| # | Fix |
|---|---|
| 2.1 | **Run A and B concurrently in one invocation** using `claude -p ... &` for both (or `xargs -P 2` / GNU parallel), each in its own `/tmp/benchmark_{id}/agent_{A,B}/` working dir. Then `wait` and proceed straight to scoring. Cuts wallclock ~50%. Risk: doubles the per-minute token rate — only safe if plan headroom and per-minute rate-limit allow it. Wrap each in a 429 handler so a hit falls back to the existing two-phase flow. |
| 2.2 | **Drop the partial-marker dance entirely** when running interactively (codespaces, manual). Keep it only for the cron path. Removes ~5 min of upload/download/comment round-trips per benchmark. |
| 2.3 | **Stream `agent_A_run.json` and `agent_B_run.json` to disk via `--output-format stream-json`** with `tee`, so even if one is killed, partial progress is salvageable without re-running. (Already used in the Windows variant per CLAUDE.md.) |
| 2.4 | **Score incrementally**: as soon as A finishes, kick off assertion-checks on A while B is still running. Final unblinded report waits for both. Saves 1–3 min. |

---

## 3. Too many replicated turns

**Root causes (typical from jsonl logs):**

- Agent re-reads the same files across turns (no memory of prior reads).
- Agent re-runs `Rscript` validations after every minor edit.
- "Pacing — one artifact per turn" rule (referenced in CLAUDE.md) is enforced
  by the skill prompt, not by the runner — Agent B (no skill) loops more, and
  Agent A still loops when it edits then re-validates.

### Fixes

| # | Fix |
|---|---|
| 3.1 | **Add a hard turn cap**: `claude -p --max-turns 25`. For benchmark fairness apply the same cap to both A and B. |
| 3.2 | **Tighten the prompt's stopping condition**: append to both `prompt_A.txt` and `prompt_B.txt` an explicit *"When the listed deliverables exist on disk, stop. Do not re-validate, re-summarise, or re-print files."* |
| 3.3 | **Disallow re-reading prompt assets**: `--allowedTools "Bash,Write,Edit,Glob"` (drop `Read` for inputs that are already on disk in the working dir) — *or* keep `Read` but pre-list the working tree at prompt time so the agent doesn't `Glob` repeatedly. |
| 3.4 | **Cache R script results**: instruct the agent to write outputs to a single `RESULTS/` subdir and check existence before re-running. |
| 3.5 | **Lower `CLAUDE_CODE_MAX_OUTPUT_TOKENS`** for B (no skill, simpler task) so B can't ramble — e.g. 16 K instead of 64 K. |

---

## 4. Always recognises old GitHub issues, not new ones

**Root cause — two layered selection biases:**

- `get_next_eval.py` `select_eval()` in `daily` mode: ties broken by
  `get_issue_num(e["id"])` **ascending** (line 132) — lower issue number wins
  on tie, so issue #2 beats issue #74 forever.
- Phase Detection step 4: "pick the **oldest** (earliest `created_at`)"
  partial. Once an old partial exists, new partials never get picked up.
- The eval list is built from `ls _automation/evals/*.json`, which
  lexicographically sorts (`github-issue-2.json` < `github-issue-21.json` <
  ... < `github-issue-74.json`) — old IDs first.

### Fixes

| # | Fix |
|---|---|
| 4.1 | **Invert the daily-mode tiebreaker**: `key=lambda e: (..., -get_issue_num(e["id"]))` so newer issues win ties. One-line change in `get_next_eval.py` ~line 132. |
| 4.2 | **Add `--prefer-newest` flag** that sorts `eligible_evals` by `get_issue_num` descending before any selection mode runs — useful for the codespaces interactive path. |
| 4.3 | **Phase 2 candidate picker**: switch from "earliest `created_at`" to "newest", *or* require partials older than N days to be ignored as stale (and post a `BENCHMARK_STALE` marker so they don't keep blocking new ones). |
| 4.4 | **Add a stale-partial sweeper** that, before phase detection, looks for `BENCHMARK_PARTIAL` markers > 7 days old with no matching `COMPLETE` and either (a) auto-resumes them with a fresh Agent B, or (b) edits the comment to `BENCHMARK_STALE` so phase detection skips. |
| 4.5 | **Sort `_automation/evals/*.json` by issue number descending** in the dispatcher — newer evals are evaluated first when nothing's pending. |

---

## Recommended sequencing

To make the next run actually finish in ~30 min on a warm codespace:

1. **Fix 1.1 + 1.2** — devcontainer with R baked in + persistent library.
   Turns the 25-min R bootstrap into 0.
2. **Fix 4.1 + 4.5** — one-line tiebreaker flip + descending ls sort. Low
   risk, fixes the "wrong issue" complaint immediately.
3. **Fix 2.1** — parallel A/B in one invocation, behind a `--parallel` flag so
   the cron path is unaffected.
4. **Fix 3.1 + 3.2** — turn caps + tightened stop condition.

After (1)+(2)+(3), a single eval should land in ~20–25 min wall time on a
warm codespace.
