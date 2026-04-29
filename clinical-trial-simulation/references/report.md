# Simulation Report — Structure for QC

This file describes how to write the simulation report at the end of
the workflow. **It is the policy hook for organizational
customization** — edit this file to encode your group's reporting
standards. Defaults below are reasonable starting points.

## Purpose

The report is what the user reads. It serves three purposes:

1. **Answer the research questions.** Operating characteristics
   presented next to the questions they answer.
2. **Enable QC.** A reviewer audits each piece incrementally — code,
   rationale, and result side by side.
3. **Reproducibility.** The report plus the script is enough to rerun
   the simulation and get the same results.

## Structure: build-order spine

Mirror the build order in the report. The agent assembled the
simulation block by block; the report walks the reader through the
same sequence. Each section pairs (a) the relevant code snippet,
(b) a short paragraph explaining what was implemented and the
parameters used, (c) caveats inline if any.

```
0. Cost and token usage           — top of report; session-total tokens + cost
1. Why this design                — opening rationale (thought trail)
2. Confirmed parameters           — single source of truth (table)
2.5 Boundary computation          — only if external tools (rpact /
                                    gsDesign / multcomp / ...) were used
3. Arms (with endpoints)          — per arm: endpoint(...) calls +
                                    arm() + add_endpoints(), bundled
4. Trial setup                    — n, duration, accrual, dropout, stratification
5. Milestones                     — per milestone (trigger + action summary)
6. Action functions               — per action (full body verbatim)
7. Operating characteristics      — mapped back to research questions
8. Caveats and limitations        — placeholders, stubs, helper-dependencies
```

The build-order sections that have a clear *design* meaning (3-7)
each pair a code block with explanation. **The listener and the
`controller(...) / controller$run()` calls are plumbing — omit them
from the report.** They are identical across designs and add noise to
the audit trail.

### Code style in the report

Code blocks in the report are for review, not just illustration. Two
rules:

- **One statement per line.** Never chain with `;`. A reviewer must
  be able to scan the code block top to bottom and comment on
  individual lines.
- **Show the code as it actually appears in the script** — same
  variable names, same arguments, same line breaks. The report is
  the script narrated, not a paraphrase.

### 0. Cost and token usage (at the very top of the report)

A small table reporting the total token usage and cost for the
entire session — from the moment `/simulate` was invoked to the
moment the report is generated. The user wants to see this without
having to run any extra command.

The agent retrieves these via whatever telemetry is available in the
running environment. Likely paths in Claude Code:

- **`/cost` slash command output** — if the agent can capture it
  (read the conversation log, parse a recent `/cost` invocation).
- **Session JSONL log** at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`
  — each turn typically records `usage` with `input_tokens`,
  `output_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`. Sum across turns; multiply by the
  model's per-token rate.
- **Telemetry directory** at `~/.claude/telemetry/` if usage events
  are emitted there.

Use the recorded model name to look up the rate. If multiple models
were used in the session (rare), sum their costs.

If automated retrieval genuinely isn't possible, leave the placeholder
table and one line asking the user to run `/cost` and paste the
numbers — but make a real effort first.

Recommended format:

| Metric | Value |
|---|---|
| Input tokens | ... |
| Output tokens | ... |
| Cache read tokens | ... |
| Cache write tokens | ... |
| Total cost (USD) | $... |
| Model | claude-opus-4-7 (or actual) |
| Session duration | hh:mm |

### 1. Why this design

A short paragraph (3-6 sentences) capturing the reasoning that led to
this design.

- **Mode A (exploration):** include the alternatives that were
  considered and briefly why each was set aside. This is a thought
  trail — visible reasoning is more auditable than polished claims.
- **Mode B (implementation):** restate the user's brief in the
  agent's words so the user can confirm the interpretation.

### 2. Confirmed parameters

A single table that is the source of truth for every value used in
the simulation. Subsequent sections reference this table rather than
restating numbers. Include:

- Endpoint distribution parameters per arm
- Readout times for non-TTE endpoints
- Correlation structure (and which generator implements it)
- Sample size, duration, accrual schedule, dropout
- Stratification factors
- Milestone trigger thresholds
- Helper-derived literals with the helper that produced them
  (e.g., `h01 = 0.075` from `solveThreeStateModel(median_pfs=7, median_os=15, corr=0.68)`)

If a parameter is a stub (dummy decision rule, placeholder for a
combination test), mark it clearly in this table.

### 2.5 Boundary computation (only if external tools were used)

If decision boundaries were computed via an external package
(`rpact`, `gsDesign`, `multcomp`, `gMCP`, etc.), include both the
**call** and the **output** verbatim from the boundary script. The
reviewer must be able to reproduce the calculation without leaving
the report. Do not paraphrase the call or summarize the output.

```r
# scripts/boundaries.R contents — verbatim
library(rpact)
design <- getDesignGroupSequential(
  kMax             = 2,
  informationRates = c(0.66, 1.00),
  alpha            = 0.025,
  beta             = 0.20,
  sided            = 1,
  typeOfDesign     = "asOF"
)
sample <- getSampleSizeSurvival(design = design, hazardRatio = 0.74,
                                allocationRatioPlanned = 1)
```

```
# output of running boundaries.R — verbatim (key fields):
Critical z-values (one-sided, upper):  2.524  1.992
Local one-sided alpha at each stage:   0.005798  0.023210
Max events (final, 100% IF):           351
Interim events (66% IF):               232
```

The literals from this output are what get hardcoded into the
relevant `milestone(...)` extra args or `action_*` functions in §6.
Cross-reference §2 (Confirmed parameters) so the reviewer can
verify the literals match.

Skip this section entirely when no external boundary tool was used.

### 3. Arms (with endpoints)

Bundle each arm's full assembly into one block: the `endpoint(...)`
call(s) for that arm, the `arm(...)` call, and the `$add_endpoints(...)`
call. Define everything for one arm before moving to the next. This
matches the package's build order and lets a reviewer audit each arm
in one pass without scrolling.

Per arm:

- Code block showing `endpoint(...)` → `arm(...)` → `$add_endpoints(...)`,
  one statement per line, verbatim from the script.
- Short paragraph: what the arm represents clinically, what
  distribution / generator was chosen and why, readout times for
  non-TTE endpoints, any filter conditions, any helper used to
  derive parameters.
- Caveats inline (e.g., "`CorrelatedPfsAndOs3` is incompatible with
  Cox PH; final analysis uses log-rank instead.")

When two or more arms share the same endpoint structure with only
parameter differences, the explanation can be written once at the
top of the section and arms below reference it — but **the code
blocks per arm should still be shown in full** so each arm is
self-contained for review. A small per-arm parameter table is also
fine when many arms differ only in numeric values.

### 4. Trial setup

Show the `trial(...)` call. Explain:
- Sample size and duration (and whether `set_duration`/`resize` will
  modify them adaptively).
- Accrual schedule and the rationale (e.g., "30/mo for the first 6
  months reflects ramp-up; 50/mo thereafter").
- Dropout: which distribution and the helper that produced its
  parameters (`weibullDropout(...)` if used).
- Stratification factors (if any) and which baseline endpoints
  implement them.

### 5. Milestones

Per milestone:
- Show the `milestone(...)` call with its `when` condition.
- One paragraph: what triggers it (in clinical terms), what happens
  at the trigger, when in the trial it is expected to fire (cite
  expected milestone time from the calibration run if available).

### 6. Action functions

**Show the full body of each action function** as a code block —
verbatim from the script, one statement per line. Prose summaries
are not enough for QC; the reviewer needs to see the actual logic.
The code block should already be liberally commented (see SKILL.md
"Comment action functions liberally" rule).

After (not before) the code block, add a short narrative covering:

- **Trigger** — restate from §5.
- **Data lock** — what `get_locked_data` returns at this point;
  which arms / endpoints are populated.
- **Analysis** — which test, which wrapper, why this choice. **If
  a stub for a combination/group-sequential test, flag it
  prominently.**
- **Adaptation** — which `trial$*()` methods are called, with the
  rule. **If a dummy rule, flag it: "DUMMY: replace with actual
  rule."**
- **What gets saved** — each `trial$save()` mapped to which
  operating characteristic it supports.

The narrative annotates the code block; it does not replace it.

### 7. Operating characteristics

For each operating characteristic the user asked about:
- Restate the research question in the user's words.
- Show the answer (number, with the post-processing call that
  produced it: e.g., `mean(out$reject_h0)`).
- A small table or plot if the OC has structure (per-arm power,
  per-stage decision rates, allocation distribution).
- Cite which `trial$save()` call from §6 supplies the underlying
  value.

Include `summarizeMilestoneTime(out)` output for milestone-time
distributions when relevant. **When you do, add a one-line note
that these times are non-binding** — they reflect when each
milestone fired in the simulation, where every replicate runs to
completion, not the actual stopping time under a binding-interim
rule. If the design has early stopping, also report the binding-
interim expected duration derived post-hoc from saved decision
flags (per the "trials never stop early in simulation" principle in
SKILL.md and helpers.md), and explain the difference. Do not let a
reader confuse the two.

If applicable, include Monte Carlo standard error estimates next to
each OC so the reader can judge precision (e.g., for a power estimate
`p` from `n` replicates, MCSE ≈ √(p(1−p)/n)).

### 8. Caveats and limitations

A short list of things the user should know:
- Dummy decision rules that need replacement before the design is
  finalized
- Stubs for combination/group-sequential/graphical tests
- Helper-derived literals that depend on assumed inputs (e.g.,
  Pearson correlation from `solveThreeStateModel`)
- Sample-size / runtime trade-offs in the production run
- Any deviations from the original user brief

Caveats that apply to a single section can also appear inline within
that section — duplicate placement is fine if it improves
auditability.

## Output format

Default: write the report as Markdown, render it to HTML alongside,
and open the HTML in the user's default browser when ready.

```r
Rscript -e 'markdown::mark_html("report.md", output = "report.html"); browseURL("report.html")'
```

`markdown::mark_html()` is what RStudio's Markdown Preview button
uses, so the rendered HTML matches the style the user is already
familiar with. The HTML is the user's primary view; the `.md` is
the source of truth for any edits.

Place the report in the per-trial output folder (see SKILL.md
"Output organization") with consistent filenames — `report.md` /
`report.html` is the suggested default.

If the user explicitly wants a different format (Quarto,
`rmarkdown::render` with a custom template, an internal corporate
template), ask early and use that instead. The default above is for
when the user has not specified.

## Editing this file

This file is intentionally policy-light. If your organization has
specific reporting requirements — required disclosures, naming
conventions, regulatory boilerplate, audit-trail formats — edit this
file to encode them. The agent will follow whatever this file says.
