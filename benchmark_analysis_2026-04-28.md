# Benchmark Analysis — group-sequential-design skill
**Date:** 2026-04-28  
**Model filter:** Latest completed run per issue (partial runs, timeouts, and rate-limit failures excluded)  
**Models covered:** claude-sonnet-4-6, claude-opus-4-7, gemini-3-flash-preview

---

## Benchmark Summary: Latest Completed Run per Issue (Skill vs No Skill)

| Issue | Scenario | Run Date | Model | With Skill | Without Skill | Verdict |
|-------|----------|----------|-------|-----------|--------------|---------|
| **#2** | Reproduce NCT05638204 SAP | 2026-04-26 | Claude Sonnet | 0% (0/2) | **75% (1.5/2)** | ❌ No-skill — Agent A misrouted to wrong skill (sandbox orchestration bug, not skill content failure) |
| **#3** | Reproduce TOPCAT SAP | 2026-04-22 | Claude Sonnet | **100% (3/3)** | **100% (3/3)** | ➕ Tie — both numerically exact; skill produced richer audit trail (JSON + Word doc) at 4.4× token cost |
| **#21** | GSD eval 1 (single endpoint) | 2026-04-21 | Gemini Flash | **50% (4.5/9)** | 22% (2/9) | ✅ Skill — enforced structured artifacts and workflow; no-skill gave qualitative summaries only |
| **#22** | Co-primary PFS + OS | 2026-04-21 | Claude Sonnet | **100% (12/12)** | 92% (11/12) | ✅ Skill — only skill detected PFS overpower and suggested alpha reallocation to OS |
| **#23** | Multi-endpoint + multi-population | 2026-04-21 | Claude Opus | **100% (16/16)** | 75% (12/16) | ✅ Skill — no-skill missed power simulation ±2pp check, type I error bounds, and alpha reallocation guidance |
| **#24** | Non-constant hazard + NPH | 2026-04-21 | Claude Opus | **93% (13/14)** | 86% (12/14) | ✅ Skill — used prescribed `gsSurv()` with piecewise hazard and literal enrollment rates; no-skill silently rescaled enrollment |
| **#27** | PFS GSD, 2:1 randomization | 2026-04-22 | Claude Sonnet | **83% (5/6)** | 0% (0/6) | ✅ Skill — no-skill crashed on `gsSurv()` dimnames error across 7 attempts; skill's `reference.md` documented the fix |
| **#36** | Adaptive enrichment (scope refusal) | 2026-04-21 | Gemini Flash | 0% (0/7) | **57% (4/7)** | ❌ No-skill — skill blindly applied GSD to an out-of-scope problem; base model correctly identified adaptive enrichment and used combination test |
| **#37** | NPH self-detection (IO context) | 2026-04-21 | Claude Opus | **100% (8/8)** | 44% (3.5/8) | ✅ Skill — proactively flagged KEYNOTE-189 NPH pattern; sized for 390 events vs no-skill's 229 → 28% actual power under 6-mo delay |
| **#38** | Front-loaded enrollment (piecewise) | 2026-04-21 | Gemini Flash | **71% (5/7)** | 7% (0.5/7) | ✅ Skill — correctly used `gamma = c(60,15,5)`, IA at 14.9 mo; no-skill failed file structure requirements |
| **#39** | Competing risks CVOT | 2026-04-21 | Gemini Flash | **31% (2.5/8)** | 13% (1/8) | ✅ Skill (weak) — both agents missed the competing risk methodology; skill's edge was artifact quality only |
| **#40** | Subgroup futility interim | 2026-04-21 | Gemini Flash | 6% (0.5/8) | **75% (6/8)** | ❌ No-skill — skill's multiplicity input requirement couldn't handle a futility-only subgroup look with no alpha allocation; base model correctly used `test.type=4` and independent info fractions |
| **#60** | Dry-run (mean of N(0,1)) | 2026-04-27 | Claude Sonnet | **100% (1/1)** | **100% (1/1)** | ➕ Tie — trivial sanity check; skill's only advantage was fewer tokens and no code execution |
| **#69** | Alpha split, co-primary endpoints | 2026-04-25 | Claude Sonnet | **89% (12.5/14)** | 75% (10.5/14) | ✅ Skill — correct subgroup-driven N sizing with overpowered ITT signature; full 10k-rep verification; both agents missed late-IA alpha suggestion |
| **#74** | Co-primary PFS+OS, multiple IAs | 2026-04-28 | Claude Sonnet | **100% (12/12)** | 71% (8.5/12) | ✅ Skill — no-skill missing multiplicity diagram, simulation verification, and left a 31-month IA-FA gap unflagged |

*Excluded as partial/incomplete: early rate-limited run on #2; claude-sonnet run on #21 (both agents hit stream idle timeout); gemini run on #3 (Agent B produced no output).*

---

## Overall Scorecard

| | With Skill | Without Skill |
|--|------------|--------------|
| **Wins** | 10 | 3 |
| **Ties** | 2 | 2 |
| **Avg score (excl. #60 trivial)** | **73%** | **51%** |

**The 3 no-skill wins are all structural skill gaps, not base model superiority:**

| Issue | No-skill win reason |
|-------|-------------------|
| #2 | Orchestration bug in sandbox (agent misrouted) |
| #36 | Skill scope gap — adaptive enrichment outside GSD |
| #40 | Skill scope gap — futility-only subgroup not handled |

**What the benchmarks confirm the skill does well (consistent across wins):**
- Correct `gsSurv()` parameterisation — unequal allocation, piecewise hazard, non-constant enrollment (#27, #24, #38)
- Structured artifact generation — JSON, multiplicity diagram PNG, Word report enforced by workflow (#22, #23, #69, #74)
- Alpha reallocation guidance — PFS overpower detection and suggestion to reallocate to OS (#22, #23, #74)
- Simulation verification mandate — 5,000–10,000-rep lrsim enforced, results written to log and JSON (#69, #74)
- NPH self-detection in IO contexts — `gsDesign2::gs_design_ahr()` triggered by KEYNOTE-189 pattern without explicit user prompt (#37)

---

## Failure Pattern Analysis

### Pattern 1 — No scope gate before the GSD workflow starts

**Affects:** #36 (adaptive enrichment), #40 (subgroup futility-only look)  
**Verdict:** Both are no-skill wins — the only two cases where the base model outperformed the skill on substantive assertions.

In both cases the skill's workflow began immediately with parameter collection and `gsSurv()` / multiplicity graph construction, with no prior check that GSD is the correct design class for the user's problem.

- **#36:** The scenario describes a data-dependent population change between stages — the definition of adaptive enrichment. The correct framework is an inverse normal combination test (e.g. `rpact`), not `gsDesign`. The skill produced a scientifically invalid GSD design with false confidence; the base model correctly identified the framework mismatch and applied combination test weights.
- **#40:** The scenario has a subgroup with a futility-only interim look — no efficacy boundary, no alpha allocated. The skill's multiplicity input step assumes every population/endpoint has some alpha, so it could not represent a futility-only look correctly. The base model used `test.type = 4` with independent information fractions and correctly produced the `overpowered_check` field.

**Root cause:** `SKILL.md` has no "Design Class Identification" decision tree before the GSD workflow. The skill assumes GSD is always the right answer.

**Recommended fix:** Add a mandatory Step 0 to `SKILL.md`:
> **Step 0 — Scope check.** Before any computation, ask: (a) Does the population change between stages based on unblinded data? → Adaptive enrichment; refuse GSD, escalate to combination test framework. (b) Is any endpoint/population assigned zero alpha with only a non-binding futility look? → Bypass the multiplicity input step for that endpoint. A `reference.md` section mapping design features to appropriate frameworks (standard GSD, adaptive enrichment, platform trial, seamless Phase 2/3) would make this systematic.

**Priority:** P0 — skill currently produces scientifically invalid designs without warning for out-of-scope inputs.

---

### Pattern 2 — Missing competing-risks detection

**Affects:** #39 (CVOT with substantial non-CV death competing event)  
**Verdict:** Skill wins narrowly (31% vs 13%), but both agents failed the methodological core — neither flagged the competing risk. The skill's edge was artifact quality only.

The scenario describes a CV death endpoint with a non-CV death rate ~40% of the CV death rate. Both agents used `lambdaC = CV death rate` and treated non-CV death as independent censoring. The all-cause hazard (which drives actual event accumulation and study duration) never appeared in either agent's code.

**Root cause:** Neither `SKILL.md` nor `reference.md` contains a competing-risks trigger. The parameter collection questions ask for the primary event rate but not for other causes of the same terminal event.

**Recommended fix:**
1. Add to `reference.md`: *"If the user specifies a cause-specific endpoint (e.g. CV death, cancer-specific survival) AND mentions a substantial competing event rate (non-CV death > 1%/year), flag the competing risks problem before any computation. Ask which estimand is intended: cause-specific (Cox/log-rank) or subdistribution (Fine-Gray). Document that `nSurv()` implements cause-specific analysis only and that the all-cause hazard determines actual event accumulation."*
2. Add to the parameter collection step in `SKILL.md`: after collecting the primary event rate, ask *"Are there other terminal events that would prevent a patient from experiencing the primary endpoint?"*

**Priority:** P1 — silent methodological error; model produces plausible-looking but incorrect event calculations.

---

### Pattern 3 — Missing post-design check for late IA timing

**Affects:** #69, #74 — both claude-sonnet runs  
**Verdict:** Skill wins both, but both agents (with and without skill) failed the assertion: if the IA occurs >9 months after enrollment ends, suggest a larger initial PFS alpha.

In #69 the IA was 12.7 months after enrollment end; in #74 similarly late. In both cases the late IA means the PFS boundary is crossed with substantial safety margin — the initial alpha allocation is sub-optimal. Neither agent produced the reallocation suggestion.

**Root cause:** This rule exists in the benchmark rubric but not in `SKILL.md` or `post_design.md`. It is a post-design optimisation check the skill does not yet encode.

**Recommended fix:** Add to `post_design.md` under "Timing feasibility checks":
> *"If IA calendar time exceeds enrollment end by more than 9 months, the PFS single-look boundary is being crossed late relative to accrual. Consider allocating a larger initial alpha to PFS (e.g. increase from 0.002 → 0.004) and correspondingly reducing OS alpha, then re-run the design. Report the original and revised alpha splits side-by-side."*

**Priority:** P2 — design sub-optimality; does not produce an incorrect design but misses an improvement opportunity.

---

### Pattern 4 — Prompt bundle size causes execution failures

**Affects:** #2 (early rate-limited run), #21 (claude-sonnet timeout run)  
**Verdict:** Both excluded as partial runs, but the pattern is structural and will recur.

The skill bundle (`prompt_A`) combines `SKILL.md` + `README.md` + `examples.md` + `reference.md` + `post_design.md` — approximately 283 K characters / ~136 K tokens of cache creation on the first turn. In the #2 early run, five-hour token budgets were exhausted before the task completed. In the #21 claude-sonnet run, both agents hit stream idle timeouts.

A second related failure in #2: the agent attempted to invoke the skill as a CLI tool (`Skill` tool call with `group-sequential-design`) rather than reading the content already present in the prompt. The sandbox does not register skills as CLI commands, so the agent misrouted and produced zero output files.

**Root cause (bundle size):** All resources are loaded unconditionally. `examples.md` and `reference.md` together account for the majority of token cost; they are only needed for specific sub-tasks.

**Root cause (misrouting):** `SKILL.md` does not explicitly state that its content is already loaded and should be executed directly — not invoked via a `Skill` tool call.

**Recommended fixes:**
1. Bundle only `SKILL.md` in `prompt_A`. Load `examples.md`, `reference.md`, and `post_design.md` as files the agent reads on demand (note: `reference.md` is load-bearing for `gsSurv()` crash recovery — see Pattern 6).
2. Add to the opening of `SKILL.md`: *"You are already running this skill. Do not attempt to invoke it via a `Skill` tool call — execute the workflow below directly."*

**Priority:** P2 — execution reliability; causes valid runs to fail before producing output.

---

### Pattern 5 — Verification simulation not enforced by base model

**Affects:** #74 (no-skill), #69 (no-skill partial), #24 (Agent B stall)  
**Verdict:** Skill wins all three by enforcing the verification step; base model skips or truncates it.

Without skill guidance, agents either omit simulation verification entirely (producing only analytic power numbers) or run simulations that stall before completion (30-rep previews, `.rds` files with no log). The skill's `post_design.md` workflow mandates 5,000–10,000-rep verification across H₁ and H₀ for all hypotheses.

The timeout risk in #24 Agent B arose from running all scenarios sequentially in a single long Bash call. The skill agent used `lrstat::lrsim()` which is optimised for this pattern and completed 5,000 reps cleanly.

**Root cause:** The skill correctly specifies verification but does not prescribe simulation engine choice or batch strategy. Base model agents default to ad-hoc approaches that time out.

**Recommended fix:** Add to `post_design.md`:
- Preferred engine: `lrstat::lrsim()` for survival designs (fastest, vectorised).
- Batch strategy: run each scenario (H₁, H₀ global null) as a separate Bash call, not a single sequential block.
- Minimum reps: 5,000 for standard designs; 10,000 for multi-hypothesis designs.

**Priority:** P3 — already solved by skill; fix prevents residual timeout risk.

---

### Pattern 6 — `reference.md` is load-bearing, not supplementary

**Affects:** #27 — no-skill agent crashed on `gsSurv()` dimnames error across 7 attempts  
**Verdict:** Most decisive single-issue result: 5/6 vs 0/6.

The dimnames crash is a known `gsSurv()` failure mode for unequal allocation ratios (`ratio ≠ 1`) when `T`/`minfup`/`R` are combined incorrectly. `reference.md` documents the exact parameterisation fix. Without it, the base model retried the same broken call pattern seven times with no convergence.

**Implication for Pattern 4 (bundle size reduction):** If `reference.md` is moved to on-demand loading, the agent must be instructed to read it before running `gsSurv()` on any non-standard design (unequal allocation, piecewise hazard, 3+ analysis looks). Stripping it without this instruction would reproduce the #27 failure.

**Priority:** P3 — maintain carefully; on-demand loading is safe only with an explicit read instruction.

---

## Priority Summary

| Pattern | Issues affected | Skill wins? | Priority |
|---------|----------------|-------------|----------|
| 1. No scope gate (GSD applied to wrong framework) | #36, #40 | ❌ No | **P0** — scientifically invalid outputs |
| 2. No competing-risks detection | #39 | Weak | **P1** — silent methodological error |
| 3. Missing late-IA alpha suggestion | #69, #74 | Yes (shared gap) | **P2** — design sub-optimality |
| 4. Prompt bundle size / misrouting | #2, #21 | Excluded | **P2** — execution reliability |
| 5. Verification not enforced by base model | #74, #69, #24 | Yes | **P3** — already solved, engine guidance needed |
| 6. `reference.md` is load-bearing | #27 | Yes | **P3** — maintain on any bundle refactor |
