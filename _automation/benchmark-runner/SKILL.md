---
name: benchmark-runner
description: Auto-discover all skills with evals in RConsortium/pharma-skills, benchmark each with vs. without skill using matched isolated sessions, and post scored results to the linked GitHub issue. Use whenever someone says "run benchmarks", "compare skill performance", "eval the skills", or wants to measure whether a skill improves output quality.
---

# Skill Benchmark Runner

Benchmark every evaluation case in the `_automation/evals/` directory of the `RConsortium/pharma-skills` repository. For each eval case, run two fresh Claude sessions in parallel — one using the skill, one without — score anonymized outputs, then post a scored comparison as a comment on the originating GitHub issue.

Repository: `RConsortium/pharma-skills` (https://github.com/RConsortium/pharma-skills)

---

## Step 0 — R Environment Pre-flight (mandatory, run before Step 1)

**Always run this script first, even if you believe R is already installed.**
It is idempotent — safe to re-run — and will exit non-zero if setup fails,
at which point you must stop and report the error rather than continuing.

```bash
bash _automation/benchmark-runner/scripts/setup_r_env.sh
```

The script handles everything in one shot:

1. **Installs R** (`r-base`) via `apt` if `R` is not on `PATH`.
2. **Configures Posit Public Package Manager** for pre-compiled Linux binaries
   (dramatically faster than building from source).
3. **Installs and verifies all required R packages:**

   | Package | Purpose |
   |---|---|
   | `jsonlite` | JSON parse/emit in R-based dispatcher helpers |
   | `digest` | SHA hashing used by deduplication logic |
   | `gsDesign` | Group sequential boundaries and sample size |
   | `gsDesign2` | Non-proportional hazards evaluation |
   | `lrstat` | Log-rank simulation for design verification |
   | `graphicalMCP` | Maurer-Bretz graphical multiplicity testing |
   | `eventPred` | Event prediction under non-proportional hazards |
   | `ggplot2` | Visualisation used in skill outputs |

If the script exits with a non-zero status, **stop here and report the error**.
Do not proceed to Step 1.

> **Note on R-based automation:** Transient R scripts (e.g. `get_next_eval.R`,
> `record_run_result.R`) should be written to `/tmp/` rather than `_automation/`
> to prevent workspace pollution.

---

## Step 1 — Get the Next Evaluation Case

Run the dispatcher script to identify the highest-priority pending evaluation:

```bash
python3 _automation/benchmark-runner/scripts/get_next_eval.py --model {CURRENT_MODEL_NAME}
```

By default, the dispatcher uses distributed selection: it hashes the model, a runner id,
the current UTC minute, the eval id, and the skill SHA to spread different people or
workers across different pending evals. You can optionally set a stable runner id for each
person or worker:

```bash
python3 _automation/benchmark-runner/scripts/get_next_eval.py \
  --model {CURRENT_MODEL_NAME} \
  --runner-id {YOUR_NAME_OR_WORKER_ID}
```

Use `--selection-salt {YYYY-MM-DDTHH:MMZ}` to reproduce a prior distributed order, or
`--selection-mode daily` to use the older day-last-digit ordering.

- If the output is `STATUS: UP_TO_DATE`, stop and report that all benchmarks are finished.
- If the output is a JSON object, parse it. It contains the raw eval fields plus benchmark metadata:
  `_skill_name`, `_skill_sha`, `_skill_content`, `_bundled_resources`, `_prompt_a`,
  `_prompt_b`, `_common_task_prompt`, `_input_files`, `_scoring_prompt`, and
  `_blinded_scoring_map`.

---

## Step 2 — Run matched isolated agents in parallel

Run both agents simultaneously in separate working directories. **Record the start time for each agent.**
Both agents must use the same launcher, explicit model, tool allowlist, and neutralized input file names.

Create the benchmark directories:

```bash
mkdir -p /tmp/benchmark_{id}/agent_A/input /tmp/benchmark_{id}/agent_A/output_A
mkdir -p /tmp/benchmark_{id}/agent_B/input /tmp/benchmark_{id}/agent_B/output_B
```

Stage every `_input_files` item into both `input/` directories using only its neutral `alias`.
The `source` path is for the orchestrator only; do not expose original filenames or repository
paths to either agent:

```bash
cp {source_1} /tmp/benchmark_{id}/agent_A/input/{alias_1}
cp {source_1} /tmp/benchmark_{id}/agent_B/input/{alias_1}
```

Text files are also embedded in `_common_task_prompt` under neutral names such as
`input_001.csv`; binary files are only staged in `input/`.

**Agent A — WITH the skill:**
- Start a brand-new `claude -p` session from `/tmp/benchmark_{id}/agent_A`.
- Use the same explicit model and allowed tools as Agent B.
- Provide `_skill_content` and `_bundled_resources`, then provide `_prompt_a` exactly as emitted.
- Do not include the full dispatcher JSON, `_input_files.source`, raw eval file paths, or additional instructions beyond the skill bundle and `_prompt_a`.

**Agent B — WITHOUT the skill:**
- Start a brand-new `claude -p` session from `/tmp/benchmark_{id}/agent_B`.
- Use the same explicit model and allowed tools as Agent A.
- Provide `_prompt_b` exactly as emitted.
- Do not include `_skill_content`, `_bundled_resources`, skill filenames, package hints, `_input_files.source`, raw eval file paths, or prior conversation context.

Example launcher shape for each side:

```bash
cd /tmp/benchmark_{id}/agent_A && cat prompt_A.txt | claude -p --model "{CURRENT_MODEL_NAME}" --allowedTools "Bash,Read,Write,Edit,Glob" --output-format stream-json | tee agent_A_run.jsonl
cd /tmp/benchmark_{id}/agent_B && cat prompt_B.txt | claude -p --model "{CURRENT_MODEL_NAME}" --allowedTools "Bash,Read,Write,Edit,Glob" --output-format stream-json | tee agent_B_run.jsonl
```

`prompt_A.txt` should contain only the skill context plus `_prompt_a`. `prompt_B.txt` should
contain only `_prompt_b`. The experimental contrast must be skill access, not launcher,
model, cwd, file naming, or prior-session context.

The `--output-format stream-json` flag emits one JSON object per line covering every event in
the agent's run: session init, assistant turns, tool calls, tool results, and a final `result`
record with API-reported token counts. `tee` writes this to `agent_{X}_run.jsonl` while still
forwarding the stream so the orchestrator can read the response inline.

**When the agents return:**
- Extract token counts from the JSONL `result` event (more accurate than self-reported values):
  ```bash
  python3 - <<'PY'
  import json
  for path, label in [("agent_A_run.jsonl", "A"), ("agent_B_run.jsonl", "B")]:
      for line in open(f"/tmp/benchmark_{id}/agent_{label}/{path}"):
          ev = json.loads(line)
          if ev.get("type") == "result":
              u = ev.get("usage", {})
              total = u.get("input_tokens", 0) + u.get("output_tokens", 0)
              print(f"tokens_{label}={total}")
              break
  PY
  ```
  Fall back to grepping `[USAGE: {n}]` from the plain-text response if the JSONL file is
  absent or the `result` event has no `usage` field.
- Run the recording script to capture duration and tokens:
  ```bash
  python3 _automation/benchmark-runner/scripts/record_run_result.py --eval-id {id} --model {CURRENT_MODEL_NAME} --status completed --tokens-a {tokens_A} --tokens-b {tokens_B}
  ```
- Note any system errors, tool failures, or retries visible in the JSONL stream.

---

## Step 3 — Score blinded outputs against assertions

Before scoring, copy outputs according to `_blinded_scoring_map`:

```text
candidate_1 -> output_A or output_B
candidate_2 -> output_A or output_B
```

Start a fresh scoring session from a directory that contains only `candidate_1/`,
`candidate_2/`, and `_scoring_prompt`. Do not expose `_blinded_scoring_map`,
`_skill_content`, `_bundled_resources`, `output_A`, or `output_B` labels to the scorer.

For each candidate output, evaluate against every assertion in the eval case:
- Pass — assertion clearly met
- Fail — assertion clearly not met
- Partial — partially met

Score = (passes + 0.5 x partials) / total assertions, as a fraction and percentage.

Retrieve the recorded duration from the most recent entry in `_automation/benchmark-runner/runs/runs.json`.

Identify "Key Metrics" from the assertions (e.g., Sample Size, Power, Error Rates) while
still blinded. After the scoring table and qualitative notes are finalized, unblind with
`_blinded_scoring_map` and translate the results back to "With Skill" and "Without Skill"
for the report.

---

## Step 4 — Archive and Upload Detailed Outputs

To allow for deep inspection of the results (and support downloading binary files like `.docx` and `.png`):

1. **Package:** Create a zip archive containing both isolated output directories and the JSONL run logs.
   ```bash
   cd /tmp/benchmark_{id} && zip -r benchmark_results_{eval_id}.zip \
     agent_A/output_A/ agent_A/agent_A_run.jsonl \
     agent_B/output_B/ agent_B/agent_B_run.jsonl
   ```

2. **Check/create the release (MCP primary):**
   Use the `mcp__github__get_release_by_tag` tool with `tag = "benchmark-results"` and
   `owner = "RConsortium"`, `repo = "pharma-skills"`. If the call succeeds, the release
   already exists — note its `upload_url` for the next step. If it returns an error (release
   not found), you must create it via the REST API fallback below, as the MCP server does not
   expose a create-release tool.

   REST API fallback to create the release (requires `GH_TOKEN` or `GITHUB_TOKEN`):
   ```bash
   curl -s -X POST \
     -H "Authorization: Bearer ${GH_TOKEN:-$GITHUB_TOKEN}" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/RConsortium/pharma-skills/releases \
     -d '{"tag_name":"benchmark-results","name":"Automated Benchmark Results","body":"Rolling release for automated benchmark zip files.","prerelease":true}'
   ```

3. **Upload the zip as a release asset (REST API):**
   The MCP server does not expose a release-asset upload endpoint, so use the REST API
   directly. Replace `{upload_url_base}` with the `upload_url` from step 2 (strip the
   `{?name,label}` template suffix):
   ```bash
   curl -s -X POST \
     -H "Authorization: Bearer ${GH_TOKEN:-$GITHUB_TOKEN}" \
     -H "Content-Type: application/zip" \
     "{upload_url_base}?name=benchmark_results_{eval_id}.zip" \
     --data-binary @/tmp/benchmark_{id}/benchmark_results_{eval_id}.zip
   ```
   If neither `GH_TOKEN` nor `GITHUB_TOKEN` is set, skip the upload and include all agent
   outputs inline in the report instead (see Step 5 artifacts section).

4. **Construct the direct download URL** (whether upload succeeded or not):
   `https://github.com/RConsortium/pharma-skills/releases/download/benchmark-results/benchmark_results_{eval_id}.zip`

Capture this URL for inclusion in the markdown report. If the upload was skipped, note that
in the report and include outputs inline.

---

## Step 5 — Format the benchmark report (write the Markdown file)

Write a Markdown file at `/tmp/benchmark_comment_{skill}_{eval_id}.md` using this template:

```markdown
## Automated Benchmark Results — `{_skill_name}`

### Run Metadata

| Field | Value |
|---|---|
| **Eval ID** | `{id}` |
| **Run date** | {YYYY-MM-DD HH:MM UTC} |
| **Model** | `{model name}` |
| **Skill version** | `{_skill_sha}` |
| **Triggered by** | Scheduled/Manual |

### Scorecard

| Metric | With Skill | Without Skill |
|---|---|---|
| **Score** | {score_A} ({pct_A}%) | {score_B} ({pct_B}%) |
| **Assertions** | {pass_A} Pass {partial_A} Partial {fail_A} Fail | {pass_B} Pass {partial_B} Partial {fail_B} Fail |
| **Skills loaded** | {n_skills_A} | {n_skills_B} |
| **Execution time (min)** | {time_A}m | {time_B}m |
| **Token usage** | {tokens_A} | {tokens_B} |
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
| {assertion_text_2} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |



### Debugging Information

Parse `agent_A_run.jsonl` / `agent_B_run.jsonl` (included in the zip above) for full event
history. Each line is one JSON event: `system/init`, `assistant`, `tool_use`, `tool_result`,
or `result`. The `result` line contains API-reported `usage.input_tokens` /
`usage.output_tokens` and `cost_usd`.

#### Agent A (With Skill)
- **Total Tool Calls:** {count — `tool_use` events in agent_A_run.jsonl}
- **Tool Success Rate:** {rate}% — `tool_result` events where `is_error` is false
- **Errors/Retries:** {any errors or "None"}

#### Agent B (Without Skill)
- **Total Tool Calls:** {count — `tool_use` events in agent_B_run.jsonl}
- **Tool Success Rate:** {rate}% — `tool_result` events where `is_error` is false
- **Errors/Retries:** {any errors or "None"}

### Detailed Artifacts

**Detailed Outputs:** [Download Full Benchmark Archive (.zip)]({upload_url})

#### Agent A (With Skill)
{Repeat for key files like .R, .py, .json}
**{file_name}**
```{language}
{file_content}
```

#### Agent B (Without Skill)
**{file_name}**
```{language}
{file_content}
```

</details>

---
*Posted automatically by `benchmark-runner` · Repo: https://github.com/RConsortium/pharma-skills*
```

---

## Step 6 — Post to the linked GitHub issue

Extract the issue number from the `id` (e.g., `"github-issue-21"` -> **#21**).

If a benchmark result for the same model already exists on the issue, **update it** instead
of creating a new comment. "Same model" is detected by scanning comment bodies for the string
`"Automated Benchmark Results"` together with the model name (e.g. `claude-sonnet-4-6`).

**Primary — MCP tools (no token required):**

1. Fetch existing comments with `mcp__github__issue_read`:
   ```
   method: get_comments
   owner:  RConsortium
   repo:   pharma-skills
   issue_number: {issue_number}
   ```
2. Scan the returned comments for one whose `body` contains both
   `"Automated Benchmark Results"` and `{CURRENT_MODEL_NAME}`.
   - **Found** — note its `id`, then PATCH it via REST:
     ```bash
     curl -s -X PATCH \
       -H "Authorization: Bearer ${GH_TOKEN:-$GITHUB_TOKEN}" \
       -H "Accept: application/vnd.github+json" \
       -H "Content-Type: application/json" \
       https://api.github.com/repos/RConsortium/pharma-skills/issues/comments/{comment_id} \
       --data-binary @/tmp/benchmark_comment_{skill}_{eval_id}.md \
       | python3 -c "import json,sys; print(json.load(sys.stdin).get('html_url',''))"
     ```
     > Note: `--data-binary` sends raw JSON body. Wrap the file contents in `{"body": "..."}` if using a JSON payload builder.
   - **Not found** — create a new comment with `mcp__github__add_issue_comment`:
     ```
     owner: RConsortium
     repo:  pharma-skills
     issue_number: {issue_number}
     body: <contents of /tmp/benchmark_comment_{skill}_{eval_id}.md>
     ```

**Fallback — REST API (requires `GH_TOKEN` or `GITHUB_TOKEN`):**
If the MCP tool is unavailable or returns an error, the Python script handles the full
upsert automatically:
```bash
python3 _automation/benchmark-runner/scripts/post_issue_comment.py {issue_number} \
  --repo RConsortium/pharma-skills \
  --body-file /tmp/benchmark_comment_{skill}_{eval_id}.md \
  --model {CURRENT_MODEL_NAME}
```
Pass `--model` so the script can find and update an existing comment. Without `--model` it
always creates a new comment.

---

## Execution Flow

```
Run get_next_eval.py (Detects composite skill SHA, model, and file order)
  |-- If STATUS: UP_TO_DATE -> Exit
  |-- If JSON ->
       |-- Agent A (with skill) ---+
       |-- Agent B (without skill)-+--- run in parallel
       |-- Score blinded candidates           (Step 3)
       |-- Archive and upload detailed outputs (Step 4)
       |-- Format Markdown report              (Step 5)
       |-- Post comment to GitHub issue #{N}   (Step 6)
```

## Notes on Model Name

Pass `--model` using the canonical API model ID (e.g., `gemini-2.0-flash`, `gpt-4o`, `claude-3-7-sonnet`), not the
display name (e.g., `Claude Sonnet 3.7`). The deduplication logic normalises both sides,
but using the API ID avoids any ambiguity across runs.

## Notes on Distributed Selection

When several people run the same model, they should set distinct `--runner-id` values
or `PHARMA_SKILLS_RUNNER_ID` environment variables. The dispatcher uses that id to create
a stable per-runner ordering of the pending evals for the current UTC minute. If runner ids
are not available, the minute-level salt still reshuffles the ordering as people start runs
at different times. This reduces collisions without requiring a central lock. It does not
eliminate races completely; runners that start in the same minute with the same model and
same runner id can still pick the same eval. The GitHub issue-comment deduplication prevents
completed duplicate model/SHA results from being selected on later runs.

## Success Criteria

- Only one high-priority evaluation is processed per run
- Deduplication correctly accounts for both Skill SHA and Model Name (normalised)
- LLM token usage is minimised by offloading discovery to a script
- Results are posted as comments on the correct GitHub issues using `gh` or the REST fallback
