---
name: benchmark-runner
description: Auto-discover all skills with evals in RConsortium/pharma-skills, benchmark each with vs. without skill using matched isolated sessions, and post scored results to the linked GitHub issue. Use whenever someone says "run benchmarks", "compare skill performance", "eval the skills", or wants to measure whether a skill improves output quality.
---

# Skill Benchmark Runner

Benchmark every evaluation case in the `_automation/evals/` directory of the `RConsortium/pharma-skills` repository. Each routine invocation is **one of two short phases (~20 min each)**. The routine inspects GitHub issue comments on startup to decide which phase to execute — no configuration needed, no commits required, no repo write access required from the human user.

Repository: `RConsortium/pharma-skills` (https://github.com/RConsortium/pharma-skills)

---

## Routine Setup (one-time)

Create a single routine at [claude.ai/code/routines](https://claude.ai/code/routines):

| Field | Value |
|---|---|
| **Prompt** | `Read _automation/benchmark-runner/SKILL.md and execute.` |
| **Repository** | `RConsortium/pharma-skills` |
| **Schedule** | `0 1,6 * * *` (1 AM and 6 AM UTC — 5 h gap, matches rolling usage window) |

That is all. The skill determines its own phase on every invocation.

---

## GitHub Access — Use Whichever Method Works

Throughout this skill you will read issue comments, post issue comments, and create release assets. **Use whatever method is available in your environment** — pick the one that works without prompting:

| Method | Best when | Notes |
|---|---|---|
| `mcp__github__*` MCP tools | Running inside Claude Code with the GitHub MCP server | No token required; preferred when available |
| `gh` CLI (`gh issue view`, `gh release upload`, etc.) | Running locally with `gh` authenticated | Concise, supports all operations |
| REST API via `curl` | Anywhere with `GH_TOKEN` / `GITHUB_TOKEN` set | Universal fallback; use for release-asset upload (no MCP equivalent) |
| Provider-specific GitHub tools (Codex, Gemini, etc.) | Running under another agent CLI | Use whatever the host provides |

Reason about which method to use; do not enforce a rigid order. If one fails, try another. Always confirm the operation succeeded (e.g., the comment URL came back, the asset was uploaded) before continuing.

For release-asset upload there is currently no MCP tool — use `gh release upload` or `curl` POST to the upload URL.

---

## Turn-Control Configuration

Both Agent A and Agent B are launched with runner-side turn controls. These caps live in the runner, **not** in the skill prompt — the skill at `group-sequential-design/SKILL.md` is owned by another team and is not modified from this side.

Define these once before launching either agent:

```bash
# Hard turn cap for both agents — fires loud (is_error=true, subtype=error_max_turns)
# rather than silently truncating. Tuned from the 2026-05-05 opus-4-7 run where
# Agent A ran 66 turns before the skill's pacing rules let it stop.
MAX_TURNS=30

# Runner-injected stop rules. Appended to the system prompt at launch time;
# does NOT modify the skill's own SKILL.md or _skill_content.
STOP_RULES="When the deliverables listed in your task prompt exist on disk, stop. Do not re-read files you wrote earlier this run, do not re-run scripts that already produced their expected output, do not re-print or re-summarize results that are already on disk."

# Per-agent output ceilings. Skill output legitimately needs the headroom on A;
# B is markdown-only and doesn't need 64K — a lower ceiling discourages drift.
MAX_OUT_TOKENS_A=64000
MAX_OUT_TOKENS_B=32000
```

When the turn cap fires, `agent_{A,B}_run.json` will contain `is_error: true` with `subtype: "error_max_turns"`. The runner must check `subtype` (not just `is_error`) and record `status: error_a_max_turns` / `error_b_max_turns` in `runs.json` rather than treating a capped run as a clean partial.

---

## Phase Detection — Run Before Any Other Step

Scan all benchmark eval issues to find any that are waiting for Phase 2 (Agent B + scoring) **for the model you are running**:

1. List all eval files: `ls _automation/evals/*.json` — extract each `id` field (e.g. `github-issue-27` → issue **#27**).

2. For each issue number, fetch comments using whichever GitHub access method is available (see above). Scan each comment body for a `<!-- BENCHMARK_PARTIAL:` marker.

3. Filter and evaluate each `BENCHMARK_PARTIAL` marker found:
   - **Skip if `state.model` does not match `{CURRENT_MODEL_NAME}`.** This is critical: a partial run by another user on a different model belongs to that user. Only pick up partials matching your current model.
   - Skip if a later comment on the same issue contains a matching `<!-- BENCHMARK_COMPLETE: {"eval_id":"{same}","model":"{same}"` — Phase 2 already finished for that combination.
   - Otherwise → **Phase 2 candidate**. Extract the JSON from the marker (see format below) and note the partial comment `id`.

4. **Decision:**
   - One or more Phase 2 candidates found → pick the **oldest** (earliest `created_at`) → **enter Phase 2** with that state.
   - No candidates for your model → **enter Phase 1**.

**BENCHMARK_PARTIAL marker format** (hidden HTML comment embedded in the issue comment body):
```
<!-- BENCHMARK_PARTIAL: {"eval_id":"github-issue-27","model":"claude-sonnet-4-6","skill_sha":"b5ede6a...","issue_number":27,"blinded_map":{"candidate_1":"output_B","candidate_2":"output_A"},"agent_a_asset_url":"https://github.com/RConsortium/pharma-skills/releases/download/benchmark-results/benchmark_agent_a_github-issue-27.zip","run_date":"2026-05-03T06:00Z","tokens_a":199382,"partial_comment_id":4367060533} -->
```

---

## Phase 1 — Agent A Run (With Skill)

Runs when no Phase 2 candidate is found. Executes Agent A, archives its output, and posts a partial comment that holds state for Phase 2.

### Step 0 — R Environment Pre-flight

**Always run first. Idempotent — safe to re-run.**

```bash
bash _automation/benchmark-runner/scripts/setup_r_env.sh
```

Exits non-zero on failure — stop and report the error. Do not proceed.

> R packages installed: `jsonlite`, `digest`, `gsDesign`, `gsDesign2`, `lrstat`, `graphicalMCP`, `eventPred`, `ggplot2`

### Step 1 — Discover Next Eval

```bash
python3 _automation/benchmark-runner/scripts/get_next_eval.py --model {CURRENT_MODEL_NAME}
```

- `STATUS: UP_TO_DATE` → all evals complete for this model+SHA. Exit.
- JSON output → parse to a temp file; extract `_skill_name`, `_skill_sha`, `_skill_content`, `_bundled_resources`, `_prompt_a`, `_blinded_scoring_map`, and the issue number from `id`.

Optional flags:
```bash
--runner-id {YOUR_NAME}           # stable per-person ordering
--priority-issue github-issue-{N} # force a specific eval
```

### Step 2 — Run Agent A (With Skill)

Create the working directory:

```bash
mkdir -p /tmp/benchmark_{id}/agent_A/output_A
```

**Stage bundled resource files to disk** (progressive disclosure — files read on demand, not embedded in the prompt):

```python
import os, json
agent_a_dir = "/tmp/benchmark_{id}/agent_A"
for rel_path, content in eval_case["_bundled_resources"].items():
    if rel_path == "SKILL.md":
        continue
    dest = os.path.join(agent_a_dir, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)
```

**Write `prompt_A.txt`** — `_skill_content` (SKILL.md) followed by `_prompt_a` only. No bundled resource content in the prompt:

```python
prompt_a = eval_case["_skill_content"] + "\n\n" + eval_case["_prompt_a"]
with open(os.path.join(agent_a_dir, "prompt_A.txt"), "w", encoding="utf-8") as f:
    f.write(prompt_a)
```

**Launch Agent A:**

```bash
cd /tmp/benchmark_{id}/agent_A && \
  cat prompt_A.txt | CLAUDE_CODE_MAX_OUTPUT_TOKENS=$MAX_OUT_TOKENS_A claude -p --model "{CURRENT_MODEL_NAME}" \
  --allowedTools "Bash,Read,Write,Edit,Glob" \
  --max-turns $MAX_TURNS \
  --append-system-prompt "$STOP_RULES" \
  --output-format json > agent_A_run.json 2>&1
```

> **Env-var placement.** `CLAUDE_CODE_MAX_OUTPUT_TOKENS=...` must be on the **right side of the pipe** (immediately before `claude`). In bash, a `VAR=val cmd1 | cmd2` prefix only sets `VAR` in `cmd1`'s environment — putting it before `cat` would silently leave claude on its default cap.

`--output-format json` emits a single JSON object when the agent finishes — resilient to long-running agents and session timeouts. `--max-turns` and `--append-system-prompt` are the runner-side turn controls defined in the [Turn-Control Configuration](#turn-control-configuration) section above.

> **Diagnosing an in-flight run.** With `--output-format json`, `agent_A_run.json` stays at **0 bytes** for the entire duration of the run and is only written when claude exits. **An empty file is not evidence of a crash** — do NOT relaunch on that basis. To check progress while a run is in flight:
>
> 1. Confirm the process is alive: `pgrep -af 'claude -p' | grep agent_A` (the launcher's PID should still be there).
> 2. Tail the live session transcript: the most recent `.jsonl` under `~/.claude/projects/-tmp-benchmark-{id}-agent-A/` is being appended turn-by-turn while the run is in flight.
> 3. Only relaunch if (a) no `claude -p` process is running AND (b) `agent_A_run.json` is empty or fails `json.load()`. Before relaunching, kill any stragglers: `pkill -f 'claude -p.*agent_A'` — two `claude -p` processes writing to the same `> agent_A_run.json` produces interleaved bytes that won't parse.

**When Agent A returns**, extract token count and check whether the turn cap fired:

```python
import json
d = json.load(open("/tmp/benchmark_{id}/agent_A/agent_A_run.json"))
u = d.get("usage", {})
tokens_a   = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
is_error_a = d.get("is_error", False)
subtype_a  = d.get("subtype", "")  # "success", "error_max_turns", "error_during_execution"

if subtype_a == "error_max_turns":
    # Turn cap hit. Record as error_a_max_turns and surface to the issue
    # comment so the skill owner can see the cap fired. Do NOT silently
    # treat this as a clean partial.
    status_for_runs = "error_a_max_turns"
else:
    status_for_runs = "partial_a"
```

Record in `runs.json` (use `$status_for_runs` from the previous block — it will be `partial_a` on success, `error_a_max_turns` if the cap fired):

```bash
python3 _automation/benchmark-runner/scripts/record_run_result.py \
  --eval-id {id} --model {CURRENT_MODEL_NAME} \
  --status {status_for_runs} --tokens-a {tokens_a}
```

### Step 3 — Archive Agent A Output

Create the zip:

```bash
cd /tmp/benchmark_{id} && zip -r benchmark_agent_a_{eval_id}.zip \
  agent_A/output_A/ agent_A/agent_A_run.json
```

Upload to the `benchmark-results` GitHub release as a named asset. **The release must already exist** (create it once if needed). Use whichever method works in your environment — examples below; pick what works:

- **`gh` CLI** (simplest if available):
  ```bash
  gh release view benchmark-results --repo RConsortium/pharma-skills \
    || gh release create benchmark-results --repo RConsortium/pharma-skills \
       --prerelease --title "Automated Benchmark Results" --notes "Rolling release."
  gh release upload benchmark-results /tmp/benchmark_{id}/benchmark_agent_a_{eval_id}.zip \
    --repo RConsortium/pharma-skills --clobber
  ```
- **REST API via `curl`** (when only `GH_TOKEN` is available):
  ```bash
  # Get-or-create release, then POST to its upload_url with the zip as data-binary.
  # See https://docs.github.com/en/rest/releases for the exact endpoints.
  ```
- **MCP** does not currently expose a release-asset upload tool — use `gh` or `curl` for the upload step. Comment posting and reading can still use MCP.

Construct the asset download URL (used in the partial comment state):
```
https://github.com/RConsortium/pharma-skills/releases/download/benchmark-results/benchmark_agent_a_{eval_id}.zip
```

**If no upload method works** (no `gh`, no token), skip the upload and set `agent_a_asset_url: null` in the partial state. Phase 2 will detect the null URL and re-run Agent A for that eval — wasteful but correct.

### Step 4 — Post Partial Comment

Write the partial comment body to `/tmp/partial_comment_{eval_id}.md`:

```markdown
## Automated Benchmark Results — `{_skill_name}` 🟡 In Progress

### Run Metadata

| Field | Value |
|---|---|
| **Eval ID** | `{id}` |
| **Run date** | {YYYY-MM-DD HH:MM UTC} |
| **Model** | `claude-sonnet-4-6` |
| **Skill version** | `{_skill_sha[:7]}` |
| **Phase** | 1 of 2 complete — Agent A (with skill) finished |

Agent A has completed. Agent B (without skill) will run in the next scheduled window (~5 h).
Results will be updated here automatically.

<!-- BENCHMARK_PARTIAL: {"eval_id":"{id}","model":"{CURRENT_MODEL_NAME}","skill_sha":"{_skill_sha}","issue_number":{N},"blinded_map":{_blinded_scoring_map},"agent_a_asset_url":"{asset_url}","run_date":"{ISO8601}","tokens_a":{tokens_a}} -->
```

Post it using whichever GitHub access method is available (see "GitHub Access" above). The partial comment `id` returned by the API is not needed for Phase 2 (Phase 2 discovers it by scanning), but log it for debugging.

**Phase 1 is complete.** Print this summary to the user before exiting:

```
✓ Phase 1 complete — Agent A finished for {eval_id} ({model})
  • Output archived: {asset_url}
  • Partial comment: {comment_url}
  • Tokens used: {tokens_a:,}

NEXT STEP — Phase 2 (Agent B + scoring):
  • If running as a scheduled routine: nothing to do. The next scheduled
    invocation (≥5 h from now, after the rolling usage window resets) will
    detect this partial state automatically and run Phase 2.
  • If running manually: re-invoke this skill any time. It will
    detect the BENCHMARK_PARTIAL marker on issue #{N} and run Phase 2 to
    completion.
```

Then exit cleanly.

---

## Phase 2 — Agent B Run + Scoring

Runs when a `BENCHMARK_PARTIAL` state is found in a GitHub issue comment. Loads Agent A's output, runs Agent B, scores both, posts the full result.

### Step 5 — Load Partial State

Parse the `BENCHMARK_PARTIAL` JSON from the comment body found during Phase Detection:

```python
import re, json
marker_re = re.compile(r'<!-- BENCHMARK_PARTIAL: ({.*?}) -->', re.DOTALL)
m = marker_re.search(comment_body)
state = json.loads(m.group(1))
# state keys: eval_id, model, skill_sha, issue_number, blinded_map,
#             agent_a_asset_url, run_date, tokens_a
```

Also reload the full eval case (for assertions, scoring prompt, prompt_b):

```bash
python3 _automation/benchmark-runner/scripts/get_next_eval.py \
  --model {state["model"]} \
  --priority-issue {state["eval_id"]} \
  > /tmp/eval_case_{id}.json 2>&1
```

Restore Agent A's output. If `agent_a_asset_url` is set, download and unzip it. Use whichever method works:

```bash
mkdir -p /tmp/benchmark_{id}/agent_A/output_A

# Option A — gh CLI:
gh release download benchmark-results --repo RConsortium/pharma-skills \
  --pattern "benchmark_agent_a_{eval_id}.zip" --dir /tmp/benchmark_{id}/

# Option B — curl (release assets are public for public repos; token only needed for private):
curl -L "{agent_a_asset_url}" -o /tmp/benchmark_{id}/benchmark_agent_a_{eval_id}.zip

# Then unzip:
cd /tmp/benchmark_{id} && unzip -q benchmark_agent_a_{eval_id}.zip
```

If `agent_a_asset_url` is `null` (Phase 1 could not upload), re-run Agent A from scratch using the same procedure as Phase 1 Step 2 before continuing.

### Step 6 — Run Agent B (Without Skill)

```bash
mkdir -p /tmp/benchmark_{id}/agent_B/output_B
```

Write `prompt_B.txt` — contains only `_prompt_b`. No skill content, no resource files:

```python
with open("/tmp/benchmark_{id}/agent_B/prompt_B.txt", "w") as f:
    f.write(eval_case["_prompt_b"])
```

Launch Agent B (lower output cap — B is markdown-only and doesn't need 64K):

```bash
cd /tmp/benchmark_{id}/agent_B && \
  cat prompt_B.txt | CLAUDE_CODE_MAX_OUTPUT_TOKENS=$MAX_OUT_TOKENS_B claude -p --model "{state['model']}" \
  --allowedTools "Bash,Read,Write,Edit,Glob" \
  --max-turns $MAX_TURNS \
  --append-system-prompt "$STOP_RULES" \
  --output-format json > agent_B_run.json 2>&1
```

> **Env-var placement.** `CLAUDE_CODE_MAX_OUTPUT_TOKENS=...` must be on the **right side of the pipe** (immediately before `claude`). A `VAR=val cmd1 | cmd2` prefix only sets `VAR` in `cmd1`'s environment, so a prefix before `cat` would silently leave claude on its default cap.

> **Diagnosing an in-flight run.** With `--output-format json`, `agent_B_run.json` stays at **0 bytes** until claude exits — an empty file is not a crash, do NOT relaunch on that basis. To check progress: `pgrep -af 'claude -p' | grep agent_B` (process should still be there); tail the most recent `.jsonl` under `~/.claude/projects/-tmp-benchmark-{id}-agent-B/` for incremental turn-by-turn output. Only relaunch if (a) no `claude -p` process is running AND (b) the JSON file is empty or unparseable; kill any stragglers first with `pkill -f 'claude -p.*agent_B'`.

Extract token count, check turn cap, and record:

```python
d = json.load(open("/tmp/benchmark_{id}/agent_B/agent_B_run.json"))
u = d.get("usage", {})
tokens_b   = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
is_error_b = d.get("is_error", False)
subtype_b  = d.get("subtype", "")

if subtype_b == "error_max_turns":
    status_for_runs = "error_b_max_turns"  # cap fired — flag it, still proceed to scoring
else:
    status_for_runs = "completed"
```

```bash
python3 _automation/benchmark-runner/scripts/record_run_result.py \
  --eval-id {state["eval_id"]} --model {state["model"]} \
  --status {status_for_runs} --tokens-b {tokens_b}
```

### Step 7 — Score Blinded Outputs

Copy outputs per `state["blinded_map"]` to `/tmp/benchmark_{id}/scoring/`:

```bash
mkdir -p /tmp/benchmark_{id}/scoring/candidate_1 /tmp/benchmark_{id}/scoring/candidate_2
# blinded_map: {"candidate_1": "output_B", "candidate_2": "output_A"} (or reversed)
cp -r /tmp/benchmark_{id}/agent_{X}/output_{X}/. /tmp/benchmark_{id}/scoring/candidate_1/
cp -r /tmp/benchmark_{id}/agent_{Y}/output_{Y}/. /tmp/benchmark_{id}/scoring/candidate_2/
```

For each candidate, evaluate every assertion in the eval case:
- **Pass** — clearly met
- **Partial** — partially met
- **Fail** — not met

Score = `(passes + 0.5 × partials) / total_assertions`

Then unblind using `state["blinded_map"]` to map candidate scores back to "With Skill" and "Without Skill".

### Step 8 — Format Full Report

Write `/tmp/benchmark_comment_{skill}_{eval_id}.md`:

```markdown
## Automated Benchmark Results — `{_skill_name}`

### Run Metadata

| Field | Value |
|---|---|
| **Eval ID** | `{id}` |
| **Run date** | {YYYY-MM-DD HH:MM UTC} |
| **Model** | `{model}` |
| **Skill version** | `{skill_sha[:7]}` |
| **Triggered by** | Scheduled |

### Scorecard

| Metric | With Skill | Without Skill |
|---|---|---|
| **Score** | {score_A} ({pct_A}%) | {score_B} ({pct_B}%) |
| **Assertions** | {pass_A} Pass · {partial_A} Partial · {fail_A} Fail | {pass_B} Pass · {partial_B} Partial · {fail_B} Fail |
| **Skills loaded** | 1 | 0 |
| **Execution time** | {time_A} min | {time_B} min |
| **Token usage** | {tokens_a} | {tokens_b} |
| **{Key Metric 1}** | {value_A1} | {value_B1} |
| **{Key Metric 2}** | {value_A2} | {value_B2} |

### Key Observations

- {2-4 bullet points comparing both agents}

### Verdict

{1-2 sentence overall verdict}

---

## Technical Details & Artifacts

<details>
<summary>View Assertion Breakdown, Code Artifacts, and Logs</summary>

### Assertion Breakdown

| Assertion | With Skill | Without Skill |
|---|---|---|
| {assertion_text_1} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |

### Debugging Information

#### Agent A (With Skill)
- **Total Turns:** {num_turns from agent_A_run.json}
- **Errors/Retries:** {is_error value, or "None"}

#### Agent B (Without Skill)
- **Total Turns:** {num_turns from agent_B_run.json}
- **Errors/Retries:** {is_error value, or "None"}

### Detailed Artifacts

**Agent A Output:** [Download Agent A Archive]({agent_a_asset_url})

#### Agent A (With Skill)
{Key output files — .R, .json, text summaries}

#### Agent B (Without Skill)
{Key output files}

</details>

---
<!-- BENCHMARK_COMPLETE: {"eval_id":"{id}","model":"{model}","skill_sha":"{skill_sha}"} -->
*Posted automatically by `benchmark-runner` · Repo: https://github.com/RConsortium/pharma-skills*
```

Note the `<!-- BENCHMARK_COMPLETE: -->` marker at the bottom — this tells future Phase Detection scans that Phase 2 is done for this eval+model+sha.

### Step 9 — Post Full Results Comment

Post as a **new comment** using whichever GitHub access method is available (see "GitHub Access" above). The new comment carries the `BENCHMARK_COMPLETE` marker; the partial comment can stay in place — future Phase Detection scans will see the COMPLETE marker on a later comment and skip the partial.

If you prefer to also edit the partial comment to mark it as superseded (cleaner timeline), use whatever update method works in your environment (`gh api` PATCH, REST PATCH with `GH_TOKEN`, etc.). Optional — not required for correctness.

**Phase 2 is complete.** Print this summary to the user before exiting:

```
✓ Phase 2 complete — full benchmark posted for {eval_id} ({model})
  • Score: With Skill {pct_A}% · Without Skill {pct_B}%
  • Comment: {comment_url}
  • Tokens — A: {tokens_a:,} · B: {tokens_b:,}
```

Then exit cleanly.

---

## Execution Flow

```
EVERY ROUTINE INVOCATION:

  Phase Detection
    │
    ├─ BENCHMARK_PARTIAL found (no BENCHMARK_COMPLETE for same eval+model) ──► Phase 2
    │     Step 5: load state from comment + restore Agent A output
    │     Step 6: run Agent B (without skill)
    │     Step 7: score blinded
    │     Step 8: format full report
    │     Step 9: post full results comment (with BENCHMARK_COMPLETE marker)
    │     EXIT
    │
    └─ No partial found ──► Phase 1
          Step 0: R pre-flight
          Step 1: get_next_eval.py → if UP_TO_DATE, EXIT
          Step 2: run Agent A (with skill)
          Step 3: archive + upload Agent A output
          Step 4: post partial comment (with BENCHMARK_PARTIAL marker + state JSON)
          EXIT
```

---

## Notes on Model Name

Pass `--model` using the canonical API model ID (e.g., `claude-sonnet-4-6` or `gemini-3.1-pro-preview`), not the display name. The deduplication logic normalises both sides, but using the API ID avoids ambiguity.
* **For Gemini CLI:** Read the **Runtime Context** block injected into your system prompt to find the `Active Model` (e.g., `gemini-3-pro-preview`) if you don't already know it.

## Notes on Distributed Selection

When several people run the same model, set distinct `--runner-id` values. The dispatcher hashes runner-id + model + UTC minute + eval-id + skill-SHA to spread different runners across different pending evals. Runners starting in the same minute may collide; the GitHub issue-comment deduplication (checking for `BENCHMARK_COMPLETE` markers) prevents redundant Phase 1 runs.

## Notes on Rate Limits

If Agent A or Agent B hits a usage rate limit mid-run (`is_error: true`, result contains "You've hit your limit"):
- **Agent A rate-limited in Phase 1**: record `status: error_a_rate_limited` in `runs.json`, do NOT post a partial comment, exit. The next Phase 1 invocation will retry.
- **Agent B rate-limited in Phase 2**: record `status: error_b_rate_limited`, do NOT post a full results comment. Leave the `BENCHMARK_PARTIAL` comment in place so the next Phase 2 invocation retries Agent B. Include a note in the partial comment body edit if possible.

## Success Criteria

- One phase executed per invocation (~20 min each)
- State persists entirely in GitHub issue comments — no commits, no repo write access needed from the human user
- Blinded scoring: `_blinded_scoring_map` is never visible to the scorer
- Deduplication: `BENCHMARK_COMPLETE` marker prevents re-running finished evals
- Results posted on the correct GitHub issue with full assertion breakdown
