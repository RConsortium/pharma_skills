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
cd /tmp/benchmark_{id}/agent_A && cat prompt_A.txt | claude -p --model "{CURRENT_MODEL_NAME}" --allowedTools "Bash,Read,Write,Edit,Glob"
cd /tmp/benchmark_{id}/agent_B && cat prompt_B.txt | claude -p --model "{CURRENT_MODEL_NAME}" --allowedTools "Bash,Read,Write,Edit,Glob"
```

`prompt_A.txt` should contain only the skill context plus `_prompt_a`. `prompt_B.txt` should
contain only `_prompt_b`. The experimental contrast must be skill access, not launcher,
model, cwd, file naming, or prior-session context.

**When the agents return:**
- Extract the `[USAGE: {n}]` value from each agent's response.
- Run the recording script to capture duration and tokens:
  ```bash
  python3 _automation/benchmark-runner/scripts/record_run_result.py --eval-id {id} --model {CURRENT_MODEL_NAME} --status completed --tokens-a {tokens_A} --tokens-b {tokens_B}
  ```
- Note any system errors, tool failures, or retries.

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

1. **Package:** Create a zip archive containing both isolated output directories.
   ```bash
   cd /tmp/benchmark_{id} && zip -r benchmark_results_{eval_id}.zip agent_A/output_A/ agent_B/output_B/
   ```
2. **Upload:** Use the GitHub CLI to upload the zip file to a dedicated "Benchmark Results" release.
   - First, check if the release exists. If not, create it:
     ```bash
     gh release view "benchmark-results" --repo RConsortium/pharma-skills || gh release create "benchmark-results" --repo RConsortium/pharma-skills --title "Automated Benchmark Results" --notes "Rolling release for automated benchmark zip files." --prerelease
     ```
   - Upload the zip file as a release asset (overwriting if it already exists):
     ```bash
     cd /tmp/benchmark_{id} && gh release upload "benchmark-results" benchmark_results_{eval_id}.zip --repo RConsortium/pharma-skills --clobber
     ```
   - Construct the direct download URL:
     `https://github.com/RConsortium/pharma-skills/releases/download/benchmark-results/benchmark_results_{eval_id}.zip`

Capture this direct download URL for inclusion in the markdown report.

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

#### Agent A (With Skill)
- **Total Tool Calls:** {count}
- **Tool Success Rate:** {rate}%
- **Errors/Retries:** {any errors or "None"}

#### Agent B (Without Skill)
- **Total Tool Calls:** {count}
- **Tool Success Rate:** {rate}%
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

Post using the `gh` CLI:
```bash
gh issue comment {issue_number} --repo RConsortium/pharma-skills --body-file /tmp/benchmark_comment_{skill}_{eval_id}.md
```

If `gh` is missing, unauthenticated, or blocked, use the REST API fallback. It requires
`GH_TOKEN` or `GITHUB_TOKEN` with permission to write issue comments:

```bash
python3 _automation/benchmark-runner/scripts/post_issue_comment.py {issue_number} \
  --repo RConsortium/pharma-skills \
  --body-file /tmp/benchmark_comment_{skill}_{eval_id}.md
```

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
