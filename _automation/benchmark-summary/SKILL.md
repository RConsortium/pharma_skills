---
name: benchmark-summary
description: Generate a combined benchmark analysis for the group-sequential-design skill by reading all benchmark GitHub issues, selecting the latest completed run per issue, and producing a structured three-section report (summary table + overall scorecard + failure pattern analysis). Use this skill whenever the user asks to update the benchmark summary, generate the benchmark analysis, summarize skill vs no-skill results, add failure patterns, or produce `benchmark_analysis_YYYY-MM-DD.md`. Always invoke for any request to compare skill performance across issues over time.
---

# Benchmark Summary Skill

Produce the combined benchmark analysis document for `RConsortium/pharma-skills`. This involves reading benchmark results that live as comments on GitHub issues, selecting the right run for each, and synthesizing them into a structured report.

Repository: `RConsortium/pharma-skills`  
Output file: `benchmark_analysis_YYYY-MM-DD.md` in the repo root  
GitHub issue: post to `RConsortium/pharma-skills` after saving locally

---

## Step 1 — Discover all benchmark issues

List every open issue with a `[benchmark]` title prefix:

```bash
gh issue list --repo RConsortium/pharma-skills --limit 100 --json number,title,state \
  | jq '[.[] | select(.title | startswith("[benchmark]"))]'
```

Collect the issue numbers. Also fetch non-prefixed benchmark issues that are known eval cases (e.g. issues identified in prior summaries). When in doubt, fetch the issue and check whether it contains an "Automated Benchmark Results" comment.

---

## Step 2 — Fetch results for each issue

For each issue number, fetch all comments:

```bash
gh issue view <N> --repo RConsortium/pharma-skills --comments
```

Each benchmark result comment contains a **Run Metadata** table with:
- `Run date` — use this to order runs chronologically
- `Model` — collapse as described in Step 3
- A **Scorecard** table with With Skill / Without Skill scores
- A **Verdict** paragraph

Collect all result comments per issue. There may be multiple runs (different models or re-runs).

---

## Step 3 — Select the latest completed run per issue

Apply these rules in order to choose one run per issue:

**Exclude a run if any of these apply:**
- The scorecard note says "Partial run", "timeout", "rate-limit", "hit limit", or similar
- Both agents produced no output files
- The run was terminated before either agent finished
- The comment explicitly notes the run was superseded by a later one

**From the remaining completed runs, pick the most recent** by `Run date`.

**Model name normalisation** — collapse version suffixes for display:
- `claude-sonnet-4-6`, `claude-sonnet-4-7` → **Claude Sonnet**
- `claude-opus-4-5`, `claude-opus-4-7` → **Claude Opus**
- `claude-haiku-*` → **Claude Haiku**
- `gemini-*-flash*` → **Gemini Flash**
- `gemini-*-pro*` → **Gemini Pro**

---

## Step 4 — Build the three-section document

Follow the exact format below for the output document.

### Selection rules

- **One row per benchmark issue.** Use the **latest completed run** for each issue — ignore runs marked partial, timeout, rate-limit hit, or where both agents produced no output.
- **Do not treat `claude-sonnet-4-7` as a different model** from `claude-sonnet-4-6`; list both simply as "Claude Sonnet". Similarly collapse minor version suffixes (e.g. `claude-opus-4-7` → "Claude Opus").
- For each issue, record: run date, model, with-skill score (fraction + %), without-skill score, and a one-sentence verdict.

### Section 1 — Benchmark Summary Table

```markdown
## Benchmark Summary: Latest Completed Run per Issue (Skill vs No Skill)

| Issue | Scenario | Run Date | Model | With Skill | Without Skill | Verdict |
|-------|----------|----------|-------|-----------|--------------|---------|
| #N | <short description> | YYYY-MM-DD | <model> | X% (n/d) | Y% (n/d) | ✅/❌/➕ <one sentence> |
```

Verdict icons: ✅ = skill wins, ❌ = no-skill wins, ➕ = tie.

For no-skill wins, always add a parenthetical explaining whether it is a **skill scope gap** (wrong framework applied) or an **orchestration/environment bug** (not a content failure).

At the bottom of the table, add a note listing any excluded runs and why (partial, timeout, no output).

### Section 2 — Overall Scorecard

```markdown
## Overall Scorecard

| | With Skill | Without Skill |
|--|------------|--------------|
| **Wins** | N | N |
| **Ties** | N | N |
| **Avg score (excl. trivial)** | X% | Y% |

**The N no-skill wins are all structural skill gaps, not base model superiority:**

| Issue | No-skill win reason |
|-------|-------------------|
| #N | <one line> |

**What the benchmarks confirm the skill does well:**
- <bullet per consistent value driver>
```

Exclude issues with a trivial assertion (e.g. a dry-run with a single sanity-check assertion) from the average score calculation; note which issues were excluded.

### Section 3 — Failure Pattern Analysis

For each failure pattern, use this template:

```markdown
### Pattern N — <Short name>

**Affects:** #N, #N (scenario names)
**Verdict:** <skill wins / no-skill wins / both fail> — <one sentence on what the data shows>

<Two to four sentences describing what went wrong, with specific evidence from the benchmark runs.>

**Root cause:** <One sentence identifying the specific gap in SKILL.md / reference.md / examples.md / post_design.md.>

**Recommended fix:** <Concrete change — which file, what to add/change, example wording if helpful.>

**Priority:** P0 / P1 / P2 / P3 — <one-line justification>
```

Priority scale:
- **P0** — skill produces scientifically invalid or dangerous output for in-scope inputs
- **P1** — skill silently produces incorrect methodology (wrong framework, wrong estimand)
- **P2** — skill produces a correct but sub-optimal design, or execution reliability issue
- **P3** — gap already partially mitigated by skill; fix prevents residual risk

End the section with a **Priority Summary** table:

```markdown
## Priority Summary

| Pattern | Issues affected | Skill wins? | Priority |
|---------|----------------|-------------|----------|
| N. <name> | #N, #N | ✅/❌/Weak | **PN** — <one-line reason> |
```

Patterns to always check for (add others as evidence warrants):
- Scope gate missing (skill applies GSD to out-of-scope design)
- Competing-risks detection absent
- Post-design timing checks missing
- Prompt bundle size / misrouting
- Verification simulation not enforced
- Load-bearing reference files at risk during refactoring

---

## Step 5 — Save locally and post to GitHub

**Save locally:**

```
benchmark_analysis_YYYY-MM-DD.md
```

in the repo root (`C:/Users/zhangp/pharma-skills/pharma-skills/` on this machine). Use today's date.

**Post to GitHub** (requires user confirmation before posting):

```bash
gh issue create \
  --repo RConsortium/pharma-skills \
  --title "[analysis] Benchmark failure pattern analysis — group-sequential-design skill (YYYY-MM-DD)" \
  --body "$(cat benchmark_analysis_YYYY-MM-DD.md)"
```

Report the issue URL after posting.

---

## Incremental updates

If a prior `benchmark_analysis_*.md` already exists in the repo root, read it first. For each issue already in the prior summary, only re-fetch and update the row if a newer completed run exists on GitHub since the prior summary date. For new issues not yet in the prior summary, add them. Carry forward failure patterns from the prior summary and update or add new ones based on any new evidence.

This allows the summary to grow incrementally without re-reading every issue from scratch each time.
