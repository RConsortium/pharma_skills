---
name: benchmark-runner
description: Auto-discover all skills with evals in RConsortium/pharma_skills, benchmark each with vs. without skill using parallel sub-agents, and post scored results to the linked GitHub issue. Use whenever someone says "run benchmarks", "compare skill performance", "eval the skills", or wants to measure whether a skill improves output quality.
---

# Skill Benchmark Runner

Benchmark every evaluation case in the `_automation/evals/` directory of the `RConsortium/pharma_skills` repository. For each eval case, run two Claude sub-agents in parallel — one using the skill, one without — then post a scored comparison as a comment on the originating GitHub issue.

Repository: `RConsortium/pharma_skills` (https://github.com/RConsortium/pharma_skills)

---

## Cloud Environment Setup

If running in a cloud or CI/CD environment (like Gemini CLI, Claude Code, or GitHub Actions), ensure the following setup is performed once per session to enable CRAN access and R package installation:

1. **Network Access**: Verify the environment is configured with `Network access: Full` or `Custom` (allowing `*.r-project.org`).
2. **Install R**: If `R` is not available, run the following setup command (requires root/sudo):
   ```bash
   sudo apt update && sudo apt install -y r-base
   ```
3. **Fast Package Installation**: Always use the **Posit Public Package Manager** for pre-compiled Linux binaries to significantly reduce installation time:
   ```r
   options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/jammy/latest"))
   install.packages("gsDesign") # Example
   ```

---

## Step 1 — Get the Next Evaluation Case

Run the dispatcher script to identify the highest-priority pending evaluation:

```bash
python3 _automation/benchmark-runner/scripts/get_next_eval.py --model {CURRENT_MODEL_NAME}
```

- If the output is `STATUS: UP_TO_DATE`, stop and report that all benchmarks are finished.
- If the output is a JSON object, parse it. It contains the `prompt`, `files`, `assertions`, and metadata (`_skill_name`, `_skill_sha`, `_skill_content`, `_bundled_resources`).

---

## Step 2 — Run two sub-agents in parallel

Use the Agent tool (e.g., `generalist`) to launch both agents simultaneously for the selected eval case. **Record the start time for each agent.**

**Agent A — WITH the skill:**
- Provide the full contents of `_skill_content`.
- Provide all files from `_bundled_resources` (e.g., `reference.md`, `examples.md`, `scripts/gsd_report_template.py`).
- Provide any referenced `files` from the eval case.
- Give the `prompt` from the eval case.
- Instruct: "Follow the skill workflow to complete this task. Save all generated files into a directory named `output_A/`. Produce all expected outputs. **At the very end of your response, please state your best estimate of the total tokens used in this turn (input + output) using the format: `[USAGE: {total_tokens}]`.**"

**Agent B — WITHOUT the skill:**
- Give the exact same `prompt` and `files`.
- Instruct: "Complete this task using only your base knowledge and tools. Do NOT use any SKILL.md or skill instructions. Save all generated files into a directory named `output_B/`. Produce all expected outputs. **At the very end of your response, please state your best estimate of the total tokens used in this turn (input + output) using the format: `[USAGE: {total_tokens}]`.**"

Both agents use the same model (whichever model this session is running).

**When the agents return:**
- Extract the `[USAGE: {n}]` value from each agent's response.
- Run the recording script to capture duration and tokens:
  ```bash
  python3 _automation/benchmark-runner/scripts/record_run_result.py --eval-id {id} --model {CURRENT_MODEL_NAME} --status completed --tokens-a {tokens_A} --tokens-b {tokens_B}
  ```
- Note any system errors, tool failures, or retries.

---

## Step 3 — Score each output against assertions

For each agent's output, evaluate against every assertion in the eval case:
- Pass — assertion clearly met
- Fail — assertion clearly not met
- Partial — partially met

Score = (passes + 0.5 x partials) / total assertions, as a fraction and percentage.

Retrieve the recorded duration from the most recent entry in `_automation/benchmark-runner/runs/runs.json`.

Identify "Key Metrics" from the assertions (e.g., Sample Size, Power, Error Rates) to include in the scorecard for direct comparison.

---

## Step 4 — Archive and Upload Detailed Outputs

To allow for deep inspection of the results (and support downloading binary files like `.docx` and `.png`):

1. **Package:** Create a zip archive containing both `output_A/` and `output_B/` directories from the temporary folder.
   ```bash
   cd /tmp/benchmark_{id} && zip -r benchmark_results_{eval_id}.zip output_A/ output_B/
   ```
2. **Upload:** Use the GitHub CLI to upload the zip file to a dedicated "Benchmark Results" release.
   - First, check if the release exists. If not, create it:
     ```bash
     gh release view "benchmark-results" --repo RConsortium/pharma_skills || gh release create "benchmark-results" --repo RConsortium/pharma_skills --title "Automated Benchmark Results" --notes "Rolling release for automated benchmark zip files." --prerelease
     ```
   - Upload the zip file as a release asset (overwriting if it already exists):
     ```bash
     cd /tmp/benchmark_{id} && gh release upload "benchmark-results" benchmark_results_{eval_id}.zip --repo RConsortium/pharma_skills --clobber
     ```
   - Construct the direct download URL:
     `https://github.com/RConsortium/pharma_skills/releases/download/benchmark-results/benchmark_results_{eval_id}.zip`

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
*Posted automatically by `benchmark-runner` · Repo: https://github.com/RConsortium/pharma_skills*
```

---

## Step 6 — Post to the linked GitHub issue

Extract the issue number from the `id` (e.g., `"github-issue-21"` -> **#21**).

Post using the `gh` CLI:
```bash
gh issue comment {issue_number} --repo RConsortium/pharma_skills --body-file /tmp/benchmark_comment_{skill}_{eval_id}.md
```

---

## Execution Flow

```
Run get_next_eval.py (Detects composite skill SHA, model, and file order)
  |-- If STATUS: UP_TO_DATE -> Exit
  |-- If JSON ->
       |-- Agent A (with skill) ---+
       |-- Agent B (without skill)-+--- run in parallel
       |-- Score both against assertions       (Step 3)
       |-- Archive and upload detailed outputs (Step 4)
       |-- Format Markdown report              (Step 5)
       |-- Post comment to GitHub issue #{N}   (Step 6)
```

## Notes on Model Name

Pass `--model` using the canonical API model ID (e.g., `gemini-2.0-flash`, `gpt-4o`, `claude-3-7-sonnet`), not the
display name (e.g., `Claude Sonnet 3.7`). The deduplication logic normalises both sides,
but using the API ID avoids any ambiguity across runs.

## Success Criteria

- Only one high-priority evaluation is processed per run
- Deduplication correctly accounts for both Skill SHA and Model Name (normalised)
- LLM token usage is minimised by offloading discovery to a script
- Results are posted as comments on the correct GitHub issues
overy to a script
- Results are posted as comments on the correct GitHub issues
