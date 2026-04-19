---
name: benchmark-runner
description: Auto-discover all skills with evals in RConsortium/pharma_skills, benchmark each with vs. without skill using parallel sub-agents, and post scored results to the linked GitHub issue. Use whenever someone says "run benchmarks", "compare skill performance", "eval the skills", or wants to measure whether a skill improves output quality.
---

# Skill Benchmark Runner

Benchmark every skill in the `RConsortium/pharma_skills` repository that has an `evals/evals.json` file. For each eval case, run two Claude sub-agents in parallel — one using the skill, one without — then post a scored comparison as a comment on the originating GitHub issue.

Repository: `RConsortium/pharma_skills` (https://github.com/RConsortium/pharma_skills)

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
- Instruct: "Follow the skill workflow to complete this task. Save all generated files into a directory named `output_A/`. Produce all expected outputs."

**Agent B — WITHOUT the skill:**
- Give the exact same `prompt` and `files`.
- Instruct: "Complete this task using only your base knowledge and tools. Do NOT use any SKILL.md or skill instructions. Save all generated files into a directory named `output_B/`. Produce all expected outputs."

Both agents use the same model (whichever model this session is running).

**When the agents return:**
- Record the end time and calculate duration.
- Extract total token usage from the agent response metadata.
- Note any system errors, tool failures, or retries.

---

## Step 3 — Score each output against assertions

For each agent's output, evaluate against every assertion in the eval case:
- Pass — assertion clearly met
- Fail — assertion clearly not met
- Partial — partially met

Score = (passes + 0.5 x partials) / total assertions, as a fraction and percentage.

Identify "Key Metrics" from the assertions (e.g., Sample Size, Power, Error Rates) to include in the scorecard for direct comparison.

---

## Step 4 — Archive and Upload Detailed Outputs

To allow for deep inspection of the results:

1. **Package:** Create a zip archive containing both `output_A/` and `output_B/` directories.
   ```bash
   zip -r benchmark_results_{eval_id}.zip output_A/ output_B/
   ```
2. **Upload:** 
   - **Preferred:** If running in a CI environment with artifact support, upload the zip and capture the URL.
   - **Fallback (Gist):** For a quick public reference of the most important files (scripts, JSON results, logs), create a GitHub Gist:
     ```bash
     gh gist create output_A/*.py output_A/*.R output_A/*.json output_B/*.py output_B/*.R output_B/*.json --public --desc "Benchmark Details: {_skill_name} - {eval_id}"
     ```
   - **Local/Repo:** If instructed, commit the zip to the `{skill}/evals/benchmark-results/` directory in the repository.

Capture the resulting URL for inclusion in the report.

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
| **Detailed Outputs** | [View Archive/Gist]({upload_url}) |

### Scorecard

| Metric | With Skill | Without Skill |
|---|---|---|
| **Score** | {score_A} ({pct_A}%) | {score_B} ({pct_B}%) |
| **Assertions** | {pass_A} Pass {partial_A} Partial {fail_A} Fail | {pass_B} Pass {partial_B} Partial {fail_B} Fail |
| **Skills loaded** | {n_skills_A} | {n_skills_B} |
| **Execution time** | {time_A}s | {time_B}s |
| **Token usage** | {tokens_A} | {tokens_B} |
| **{Key Metric 1}** | {value_A1} | {value_B1} |
| **{Key Metric 2}** | {value_A2} | {value_B2} |

### Assertion Breakdown

| Assertion | With Skill | Without Skill |
|---|---|---|
| {assertion_text_1} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |
| {assertion_text_2} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |

### Key Observations

- {2-4 bullet points comparing both agents}

### Debugging Information

<details>
<summary>Agent A (With Skill) Execution Details</summary>

- **Total Tool Calls:** {count}
- **Tool Success Rate:** {rate}%
- **Errors/Retries:** {any errors or "None"}
- **Environment Note:** {e.g. R unavailable, specific library missing}
</details>

<details>
<summary>Agent B (Without Skill) Execution Details</summary>

- **Total Tool Calls:** {count}
- **Tool Success Rate:** {rate}%
- **Errors/Retries:** {any errors or "None"}
- **Environment Note:** {same or different}
</details>

### Verdict

{1-2 sentence overall verdict}

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

Pass `--model` using the canonical API model ID (e.g., `claude-sonnet-4-6`), not the
display name (e.g., `Claude Sonnet 4.6`). The deduplication logic normalises both sides,
but using the API ID avoids any ambiguity across runs.

## Success Criteria

- Only one high-priority evaluation is processed per run
- Deduplication correctly accounts for both Skill SHA and Model Name (normalised)
- LLM token usage is minimised by offloading discovery to a script
- Results are posted as comments on the correct GitHub issues
