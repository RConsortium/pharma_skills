---
name: skill-benchmark-runner
description: Auto-discover all skills with evals in RConsortium/pharma_skills, benchmark each with vs. without skill using parallel sub-agents, and post scored results to the linked GitHub issue. Use whenever someone says "run benchmarks", "compare skill performance", "eval the skills", or wants to measure whether a skill improves output quality.
---

# Skill Benchmark Runner

Benchmark every skill in the `RConsortium/pharma_skills` repository that has an `evals/evals.json` file. For each eval case, run two Claude sub-agents in parallel — one using the skill, one without — then post a scored comparison as a comment on the originating GitHub issue.

Repository: `RConsortium/pharma_skills` (https://github.com/RConsortium/pharma_skills)

The repo follows the agents.md skill structure. Each skill is a top-level folder containing at minimum a `SKILL.md` and optionally an `evals/evals.json`.

---

## Step 1 — Discover all skills with evals

1. Fetch the repo file tree:
   ```
   https://github.com/RConsortium/pharma_skills
   ```
   Identify every top-level directory that is a skill (contains a `SKILL.md`). Exclude utility/meta folders like `.github`.

2. For each skill directory, check if `evals/evals.json` exists. Only benchmark skills that have evals.

3. Build a list of skills to benchmark. Example:
   ```
   [
     { "skill": "group-sequential-design", "skill_md": "group-sequential-design/SKILL.md", "evals": "group-sequential-design/evals/evals.json" },
     { "skill": "some-future-skill", "skill_md": "some-future-skill/SKILL.md", "evals": "some-future-skill/evals/evals.json" }
   ]
   ```

---

## Step 2 — For each skill, read its resources

For each skill in the list:

1. Fetch `SKILL.md` from: `https://github.com/RConsortium/pharma_skills/blob/main/{skill}/SKILL.md`

2. Fetch any supporting reference files that `SKILL.md` points to (e.g. `examples.md`, `reference.md`, etc.) from the same skill folder.

3. Fetch `evals/evals.json` from: `https://github.com/RConsortium/pharma_skills/blob/main/{skill}/evals/evals.json`

4. Parse the evals JSON. Each eval case has this schema (per agents.md / agentskills.io):
   ```json
   {
     "skill_name": "<name>",
     "evals": [
       {
         "id": "github-issue-N",
         "prompt": "...",
         "expected_output": "...",
         "files": [],
         "assertions": []
       }
     ]
   }
   ```

5. Determine the current git commit SHA for the skill's `SKILL.md` (use WebFetch on the GitHub commits page or `gh api`). Record as **skill version**.

6. If any eval case references files (e.g. PDFs, SAP documents), fetch them from the corresponding GitHub issue attachments.

---

## Step 3 — For each eval case, run two sub-agents in parallel

Use the Agent tool to launch both agents simultaneously for each eval case.

**Agent A — WITH the skill:**
- Provide the full contents of `SKILL.md` and all supporting reference files as context.
- Give the `prompt` from the eval case and any referenced `files`.
- Instruct: "Follow the skill workflow to complete this task. Produce all expected outputs."

**Agent B — WITHOUT the skill:**
- Give the exact same `prompt` and `files`.
- Instruct: "Complete this task using only your base knowledge and tools. Do NOT use any SKILL.md or skill instructions. Produce all expected outputs."

Both agents use the same model (whichever model this session is running).

---

## Step 4 — Score each output against assertions

For each agent's output, evaluate against every assertion in the eval case:
- Pass — assertion clearly met
- Fail — assertion clearly not met
- Partial — partially met

Score = (passes + 0.5 x partials) / total assertions, as a fraction and percentage.

---

## Step 5 — Format the benchmark report

Write a Markdown file at `/tmp/benchmark_comment_{skill}_{eval_id}.md` using this template:

```markdown
## Automated Benchmark Results — `{skill_name}`

### Run Metadata

| Field | Value |
|---|---|
| **Eval ID** | `{id}` |
| **Run date** | {YYYY-MM-DD HH:MM UTC} |
| **Model** | `{model name, e.g. claude-sonnet-4-6}` |
| **Skill version** | `{git commit SHA}` |
| **Triggered by** | Manual |

### Scorecard

| | With Skill | Without Skill |
|---|---|---|
| **Score** | {score_A} ({pct_A}%) | {score_B} ({pct_B}%) |
| **Assertions** | {pass_A} Pass {partial_A} Partial {fail_A} Fail | {pass_B} Pass {partial_B} Partial {fail_B} Fail |

### Assertion Breakdown

| Assertion | With Skill | Without Skill |
|---|---|---|
| {assertion_text_1} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |
| {assertion_text_2} | {Pass/Partial/Fail} | {Pass/Partial/Fail} |

### Key Observations

- {2-4 bullet points comparing both agents}

### Verdict

{1-2 sentence overall verdict}

---
*Posted automatically by `skill-benchmark-runner` · Repo: https://github.com/RConsortium/pharma_skills*
```

---

## Step 6 — Post to the linked GitHub issue

The eval `id` maps to an issue number. Extract the number from the id:
- `"github-issue-2"` -> issue **#2**
- `"github-issue-3"` -> issue **#3**
- General pattern: parse the trailing integer from `id`.

Post using the `gh` CLI:
```bash
gh issue comment {issue_number} --repo RConsortium/pharma_skills --body-file /tmp/benchmark_comment_{skill}_{eval_id}.md
```

If `gh` is not authenticated, fall back to Claude in Chrome:
1. Navigate to `https://github.com/RConsortium/pharma_skills/issues/{issue_number}`
2. Scroll to the comment box
3. Paste the Markdown report
4. Click "Comment"

Repeat Steps 3-6 for every eval case in every discovered skill.

---

## Execution Flow

```
Discover skills with evals/evals.json
  |-- For each skill:
       |-- Read SKILL.md + supporting files + evals.json + git SHA
       |-- For each eval case:
            |-- Agent A (with skill) ---+
            |-- Agent B (without skill)-+--- run in parallel
            |-- Score both against assertions
            |-- Format Markdown report
            |-- Post comment to GitHub issue #{N}
```

## Success Criteria

- All skills with `evals/evals.json` are discovered and benchmarked
- Both sub-agents complete each eval case
- Every assertion is scored for both agents
- The report includes all metadata (eval ID, date, model, skill version SHA, trigger type)
- Results are posted as comments on the correct GitHub issues
- Each comment is clearly labeled as an automated benchmark result
