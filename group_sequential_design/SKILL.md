---
name: group_sequential_design
description: >
  Design group sequential clinical trials for survival endpoints (OS, PFS, DFS) with interim analyses,
  spending functions, boundaries, multiplicity, and event/enrollment prediction. Triggers on: Phase 3 trial design, sample size/events for survival endpoints, alpha spending, group sequential design, interim analysis planning, or enrollment/event timeline prediction for clinical trials.
---

## Bundled Resources

| File | What it contains | When to read |
|------|-----------------|--------------|
| `reference.md` | Design guidance, parameter tables, spending functions, key rules, failure modes, analysis framework, protocol references | After collecting user inputs, before writing R code |
| `examples.md` | All R code examples organized by design pattern | When you need code for a specific pattern — read only the relevant section |
| `post_design.md` | IA timing checks (warning messages, user options), verification procedure (pass criteria, lrsim code, log template) | After computing the design (step 6), before delivering |

Do NOT read these files upfront. Read them only when you reach the corresponding step.

---

## Compact Instructions

When the conversation gets long and context is compressed, preserve information in this priority order:

1. **Architecture decisions** — never re-summarize these; they are settled
2. **Key changes** — what was computed, what parameters were chosen
3. **Current verification status** — pass/fail only, drop verbose logs
4. **Tool outputs** — can be deleted; keep only essential numbers (events, boundaries, power, sample size)

---

## Workflow

**Task Progress Tracking:** At the start of step 6 (after user confirms inputs), create a task checklist using `TaskCreate` for all remaining steps. Mark each task `in_progress` when starting and `completed` when done. Typical tasks:
1. Write and run R design script (gsd_design.R)
2. Check IA timing constraints
3. Run verification simulation (gsd_verification.R)
4. Generate Word report (gsd_report.py)

This gives the user a visual progress indicator (spinner → checkmark) throughout the computation.

---

1. **Create output subfolder** — Immediately after the user answers Q1 (disease/setting), create `output/gsd_{disease}_{endpoints}_{YYYYMMDD}/` (e.g., `output/gsd_1l_mnsclc_pfs_os_20260327/`). Use a placeholder for `{endpoints}` if not yet known (e.g., `output/gsd_1l_mnsclc_20260327/`), and rename later once endpoints are confirmed. ALL outputs — including any exploratory plots or comparisons generated during the Q&A phase — go in this subfolder.
2. **Collect inputs** — Ask the questions below, one at a time
3. **Summarize and confirm** — Present a clean table, get user confirmation
4. **Read `reference.md`** — Review design guidance, key rules, and failure modes
5. **Read relevant sections of `examples.md`** — Get code for the chosen design pattern
6. **Write and run the R design script** — Compute boundaries, save results to `gsd_results.json`, generate `multiplicity_diagram.png` via `graphicalMCP::graph_create()` + `plot()`. Save all outputs to the subfolder created in step 1.

   **Transition matrix validation (step-down designs only).** Immediately after defining the transition matrix in the R script, call `validate_transition_matrix(tm, gate_prereqs)` (see `examples.md` → "Transition Matrix Validation"). This function checks Rule 3 programmatically and stops with an error if any transition routes alpha to a hypothesis that must already be rejected. The script must not proceed to boundary computation if validation fails.

   **N-first approach.** N is a top-level design parameter — all results (IA timing, FA timing, events, power) depend on N. The design script follows three phases:
   - **Phase A: Determine starting N** — Compute required events via Schoenfeld, estimate minimum N from events and prevalence, pick starting N from user's feasibility range (Q13b). Derive R from enrollment ramp. See `reference.md` → "N-First Design Algorithm".
   - **Phase B: Design at fixed N** — All calculations use fixed R/N. Find IA time (event-driven), derive OS IF, compute boundaries. No `gsSurv()` for enrollment sizing.
   - **Phase C: Evaluate and adjust** — If requirements aren't met (power, timing, OS IF), present N adjustment as an option alongside other levers. Re-run Phase B.

   **IA/FA timing must be event-driven.** The design script should:
   1. Compute the required events for each hypothesis that has a power target
   2. Find the calendar time when those events accrue (event-driven timing)
   3. Set IA time = max(event-driven times for IA-tested hypotheses, enrollment end + min follow-up)
   4. Set FA time = max(event-driven time for OS power, IA + min gap)
   5. Report which constraint is binding (event target vs min follow-up vs min gap)

   For single-look endpoints with derived power (not targeted), do NOT include their event requirement in the IA timing calculation — their power is whatever results from the events available at the IA.

   **Multiplicity diagram:** The node labels must show the **actual initial alpha** (e.g., 0.005), not the fraction of total alpha. Pass the raw alpha values directly as `hypotheses` — `graphicalMCP` displays whatever values you pass. Use `hyp_names` for the hypothesis name + endpoint (e.g., `"H1\nPFS-Ext"`) and `precision = 4` in `plot()`.

7. **Check IA timing vs enrollment** — Compare each interim analysis calendar time against the enrollment duration. If ANY interim analysis occurs before enrollment completes, **warn the user** and present options to fix it (see "IA Timing vs Enrollment Check" section below). Do NOT proceed until the user confirms the design or adjusts it.
7b. **NPH Evaluation** *(only if user specified NPH in Q7b)* — With the PH design complete (events, boundaries, enrollment from steps 1–7), evaluate it under the NPH assumptions. See "NPH Evaluation Workflow" section below. Present the NPH evaluation table to the user. If power under NPH is unacceptable, discuss options before proceeding:
   - **Add looks for NPH robustness**: If there is a large gap between analyses AND the endpoint's AHR improves over time, suggest adding the endpoint to an additional analysis. This gives the endpoint a second chance at a later timepoint with better AHR. See `reference.md` → "Adding Looks for NPH Robustness" for the full strategy. When evaluating timing options for the additional analysis, always compute and compare the NPH endpoint's power at each option — the timing should be driven by NPH power, not just the triggering endpoint's IF.
   - **Alpha reallocation**: Shift alpha from an over-powered endpoint to the NPH-affected endpoint
   - **Increase N**: More events improve AHR over time (modest effect)
   - **Accept lower NPH power**: If NPH is a sensitivity analysis, not the primary design basis
8. **Verify via simulation** — Run `lrstat` simulation. Save verification script and log in the subfolder. If verification FAILS, investigate and fix the design before proceeding. *(If NPH was specified, run verification under BOTH PH and NPH assumptions.)*
9. **Generate Word report via Python** — Only after verification passes. **Before writing `gsd_report.py`, read `reference.md` → "Report Sections", "Boundary Table Format", "IA/FA Plan Table Format", and "Sample Size and Power Summary"** to get the exact section order, table columns, and content requirements. Then write the script to match that spec exactly. The report has 6 sections: (1) Design Assumptions, (2) IA/FA Analysis Plan, (3) Multiplicity Strategy, (4) Efficacy/Futility Boundaries, (5) Sample Size and Power Summary, (6) Design Assessment.

   **Critical: Zero hardcoded design values.** The report script must be a pure template driven entirely by `gsd_results.json`. Every number in the report — alpha values, event counts, timing, power, section headings, narrative text, and improvement suggestions — must be read from the JSON. The script should produce a correct report for ANY version of the JSON without editing the script itself. This means:
   - Section headings (e.g., "H1: PFS-Ext, α = ...") use `h['H1']['alpha']`, not a literal
   - Narrative paragraphs reference `timing['ia_time']`, `ss['total_N']`, etc.
   - Design Assessment uses conditional logic based on JSON values to decide which limitations and improvements to include
   - When the design is revised (alpha reallocation, sample size change), re-running the same `gsd_report.py` on the updated JSON must produce a correct report with no manual edits
10. **Copy all scripts** — Copy `gsd_design.R`, `gsd_report.py`, and `gsd_verification.R` into the output subfolder.
11. **Deliver outputs** — Report the subfolder path, summarize results, and present the key strengths/limitations to the user

### Design Iteration

- **Comparison table**: When the user requests a modification, automatically produce a before/after table showing all changed metrics. Bold improved values. Present before proceeding with verification.
- **Ask before leaping**: When a structural change (merging IAs, changing triggers) makes parameters free or constrained differently, ask the user before re-deriving. See `reference.md` → "Design Iteration Guardrails".
- **Over-powered hypotheses**: See `reference.md` → "Handling Over-Powered Hypotheses" for options (increase alpha vs accept derived power).

### Sample Size and Study Duration

- **N ↔ duration trade-off**: Fewer patients → slower event accrual → longer study. Always present both N and timing in the comparison table. See `reference.md` → "High OS IF at IA" for the full mechanism.
- **OS IF > 85%**: Increasing N can lower OS IF at IA. Run an N sensitivity table. See `reference.md` → "High OS IF at IA".
- **Short-survival diseases** (median OS 8–10 mo): The N-duration effect is disproportionately large. If FA is too late, present N sensitivity table first — modest N increases often solve the problem. See `reference.md` → "Short-survival amplification".
- **N sensitivity table values must be consistent with the enrollment ramp.** Iterate over the last enrollment period duration K and compute actual N = sum(gamma × R). Do NOT use arbitrary round numbers.

---

## AskUserQuestion

Collect design parameters by asking **ONE question at a time**. Wait for the user's response before moving to the next question. **Do NOT provide defaults or recommendations.** Always present options and let the user choose.

### AskUserQuestion Format

- **Write for a smart 16-year-old.** Plain English, no jargon, no R function names, no implementation details.
- **Use concrete examples and analogies.** Instead of "information fraction", say "how far along the study is when you peek at the data."
- **Always offer lettered options.** A) ... B) ... C) ... — never mark one as recommended or default.
- **Keep it short.** One question, one paragraph max of context.
- **No defaults, no recommendations.** Present all options neutrally and wait for the user to decide.

### Questions (ask in this order)

1. "What disease are you studying, and what line of therapy? (e.g., first-line metastatic NSCLC, second-line bladder cancer)"

2. "How many patient populations will be tested in this trial?"
   - A) **One population** — everyone is analyzed together (e.g., all-comers, or a single biomarker-selected group)
   - B) **Two nested populations** — a biomarker-positive subgroup AND the overall/ITT population (e.g., PD-L1 CPS ≥ 20 subgroup + all patients)
   - C) **Three nested populations** — two biomarker subgroups AND the overall population (e.g., CPS ≥ 20, CPS ≥ 1, all patients)
   - D) Other — describe

   *(If B, C, or D — multi-population):*

   2b. "What is the biomarker and what defines each subgroup? (e.g., 'PD-L1 TPS ≥ 50% subgroup' and 'all patients (ITT)')"

   2c. "What fraction of the total enrolled patients do you expect to fall in each subgroup? The broadest population is always 100%."
   - Example for 2 populations: Biomarker+ subgroup: ___% (e.g., 50%), Overall/ITT: 100%

3. "What's the main thing you're measuring — how long patients live overall (OS), how long before the tumor grows (PFS), or both as co-primary endpoints?"
   - A) Overall survival (OS)
   - B) Progression-free survival (PFS)
   - C) Disease-free survival (DFS)
   - D) Co-primary — two endpoints tested together (e.g., PFS + OS)
   - E) Other — specify your endpoint

   *(If multi-population)* "Are the same endpoints tested in every population?"
   - A) Yes — same endpoints in all populations (e.g., PFS + OS in both subgroup and ITT)
   - B) No — different endpoints by population (specify)

   After Q3, enumerate all hypotheses for the user. Example for 2 populations with PFS+OS: "Your design has 4 hypotheses: H1 (PFS in subgroup), H2 (PFS in ITT), H3 (OS in subgroup), H4 (OS in ITT)."

4. *(Only if 2+ hypotheses — co-primary, multi-population, or both)* **Multiplicity strategy.** This is asked early because it defines the testing framework for everything else.

   4a. "What is the overall one-sided significance level (alpha) for the study? In most Phase 3 trials, this is 0.025 (one-sided), which is equivalent to 0.05 two-sided."
   - A) 0.025 (one-sided) — standard
   - B) Other — specify

   4b. *(If multi-population)* "How should the populations be tested?" See `reference.md` → "Choosing Between Step-Down and Alpha Split" for guidance.
   - A) **Step-down** — test the subpopulation first at full alpha. Only if positive, test the overall population. The subpopulation drives the sample size; the overall population is typically overpowered. Best when there is strong belief that the subpopulation has a better treatment effect.
   - B) **Alpha split** — divide the alpha between populations upfront. Each population is tested independently. Best when uncertain whether the subpopulation is truly superior.

   *(If B — alpha split)* When allocating alpha, assign **more alpha to the subpopulation** than to the overall population — the subpopulation has fewer events (due to prevalence) and needs the alpha advantage. The overall population has more events and can maintain power with less alpha. See `reference.md` → "Alpha Allocation in Alpha-Split Designs" for the full rationale and caveats.

   4c. "How do you want to distribute the initial alpha across your hypotheses? The amounts must sum to the total alpha."

   *(Single-population co-primary)* Example: PFS 0.005 + OS 0.020 = 0.025.

   *(Multi-population step-down)* All initial alpha goes to the subpopulation. Example: H1 (PFS-sub) = 0.005, H3 (OS-sub) = 0.020, H2 (PFS-ITT) = 0, H4 (OS-ITT) = 0.

   *(Multi-population alpha-split)* More alpha to subpopulation (fewer events, needs the advantage). Example: H1 (PFS-sub) = 0.003, H2 (PFS-ITT) = 0.002, H3 (OS-sub) = 0.015, H4 (OS-ITT) = 0.005.

   **Validation:** If the split does not sum to the total alpha, flag the discrepancy and ask the user to correct it.

   4d. *(If multi-population AND step-down only)* "What is the testing order within each chain?"

   **Skip this question for alpha-split designs.** In an alpha-split, every hypothesis receives initial alpha and is testable from the start — there is no gating. Proceed directly to Q4e.

   For step-down: subpopulation hypothesis must be rejected before the corresponding overall hypothesis can be tested. Additionally, for co-primary endpoints where OS > PFS: OS must be positive in a population before PFS in a broader population can be tested.

   Present the gating structure for confirmation. Example (step-down, PFS+OS):
   - H3 (OS-sub) must be rejected before H4 (OS-ITT) can be tested
   - H4 (OS-ITT) must be rejected before H2 (PFS-ITT) can be tested (OS positive = population positive)
   - H1 (PFS-sub) is tested initially with its allocated alpha (no gate)

   4e. "When a hypothesis is rejected, where should its freed alpha flow?"

   **Before applying any recycling rules, trace the gating chain for EVERY hypothesis.** For each hypothesis H, list which other hypotheses must already be rejected for H to be testable. These are H's "gate prerequisites" — H can NEVER send alpha to any of them (they are already rejected). Write out this table explicitly before constructing the transition matrix:

   | Hypothesis | Gate prerequisites (already rejected when H is tested) | Eligible recipients |
   |------------|-------------------------------------------------------|-------------------|
   | H1 | (none — tested initially) | H2, H3, H4 |
   | H2 | (none — tested initially) | H1, H3, H4 |
   | H3 | H2, H4 (gated behind both) | H1 only |
   | H4 | H2 (gated behind H2) | H1, H3 |

   Only after completing this table, apply the Alpha Recycling Priority Rules to the **eligible recipients only**:
   - Rule 1: PFS rejection → OS same population
   - Rule 2: OS rejection → OS next population
   - Rule 3: Do not pass alpha to already-rejected hypotheses (gating constraint) — **enforced by the table above**
   - Rule 4: Split alpha when multiple hypotheses could benefit
   - Rule 5: Use 1.0 vs 0.999 based on intent:
     - **1.0** when only one hypothesis is intended to receive alpha (e.g., PFS → OS same population — unambiguous, single destination)
     - **0.999/0.001** when multiple hypotheses could benefit (e.g., OS rejection — primary target gets 0.999, alternate gets 0.001 epsilon)
     - **Always confirm with the user when proposing weight = 1.0** — even when the rationale seems clear, present the reasoning and let the user confirm or adjust

   **Epsilon destination is a strategic choice.** When an OS hypothesis is rejected and epsilon goes to a PFS hypothesis, there are two valid strategies — present both and let the user decide:
   - Epsilon to PFS in the smaller population (fewer events, benefits more from alpha boost)
   - Epsilon to PFS in the same population as the rejected OS (to lock in both co-primary endpoints in that population first)

   Present the derived transition matrix and ask: "Does this alpha flow look right?"

   *(Single-population co-primary)* Simpler version: "If one endpoint wins, should its alpha flow to the other?"
   - A) Full bidirectional reallocation
   - B) One-way (PFS → OS only)
   - C) One-way (OS → PFS only)
   - D) No reallocation

5. "How are patients split between the new treatment and the standard?"
   - A) 1:1 — one patient on the new drug for every one on the standard
   - B) 2:1 — two patients on the new drug for every one on the standard
   - C) 3:1 — three patients on the new drug for every one on the standard
   - D) Other — specify a ratio

6. "On the standard treatment, how long do patients typically survive (or stay progression-free) before half of them have an event? This is the 'median' in months."

   **Piecewise control hazards:** If the user specifies a piecewise control hazard (e.g., "log(2)/4 for the first 3 months, then log(2)/8 thereafter"), accept it. This is common when early event rates differ from later rates (e.g., high early progression risk that decreases). Store as `lambdaC = c(log(2)/4, log(2)/8)` with breakpoint `S = 3`. Use `calc_expected_events_pw()` from `examples.md` for event calculations and `gsSurv(lambdaC=..., S=...)` for boundary computation. For required events, use Schoenfeld formula (not nSurv) when the HR is constant — see `reference.md` → "Schoenfeld vs nSurv with piecewise control hazards".

   *(If multi-population)* Ask per population × endpoint. Offer shortcut: "If medians are the same across populations, just give one number per endpoint."
   - Control median PFS in subgroup? (e.g., 8 months)
   - Control median PFS in ITT? (e.g., 6 months)
   - Control median OS in subgroup? (e.g., 18 months)
   - Control median OS in ITT? (e.g., 14 months)

7. "How much better do you expect the new treatment to be? This is expressed as a hazard ratio — lower means bigger benefit."
   - A) 0.80 — modest benefit (~20% risk reduction)
   - B) 0.75 — moderate benefit (~25% risk reduction)
   - C) 0.70 — strong benefit (~30% risk reduction)
   - D) 0.65 — large benefit (~35% risk reduction)
   - E) Other — specify a number

   *(If multi-population)* Ask per population × endpoint. "The treatment effect is often stronger in the biomarker-enriched subgroup."

7b–7c. **Non-proportional hazards (NPH) — do NOT ask proactively.** Only collect NPH specifications if the user explicitly requests an NPH evaluation. If they do, collect piecewise specs per endpoint (control hazard and HR by time period). The Q6/Q7 answers become the PH reference design; NPH specs are used only for evaluation afterward. See "NPH Evaluation Workflow" section for details.

8. *(Only if co-primary endpoints in Q3)* "For your co-primary endpoints, do the interim analyses happen at the same time for both endpoints, or does each endpoint have its own separate schedule?"
   - A) **Same time** — both endpoints are analyzed at every interim look and at the final analysis
   - B) **Separate schedules** — each endpoint has its own number of interims and its own timing

   If A: proceed to Q8a. If B: proceed to Q8b.

8a. *(Same-time IAs)* "How many total analyses (interims + final)?"
   - A) 1 interim + final (2 total looks)
   - B) 2 interims + final (3 total looks)
   - C) 3 interims + final (4 total looks)
   - D) No interim — just one final analysis
   - E) Other

   Then: "Which endpoint triggers each analysis?"
   - Give examples based on number chosen.

   **Immediately after establishing triggers**, ask: "Which endpoints are tested at which analysis?" An endpoint that triggers an analysis is always tested there, but a non-triggering endpoint may or may not be tested at every analysis. For example, if PFS triggers the IA and OS triggers the FA, PFS might be tested only at the IA (single look) or at both IA and FA.

   Present a table for confirmation showing which endpoint × analysis combinations are active. Example:

   | Analysis | PFS | OS |
   |----------|:---:|:---:|
   | IA (PFS-triggered) | Tested | Tested |
   | FA (OS-triggered) | ? | Tested |

   "Is PFS also tested at the FA, or only at the IA?" This determines whether PFS is a single-look (k=1) or multi-look endpoint, which affects boundary computation.

   *(If multi-population)* Expand the table to show all hypotheses (H1–H4) instead of just endpoints.

8b. *(Separate schedules)* Ask for each endpoint individually.

   *(Single endpoint — skip Q8/8a/8b)* "How many times do you want to peek at the data before the final analysis?" (same options as 8a)

9. *(Skip if no interims)* "When should the interim peek(s) happen? This is how far along the study should be — measured by what fraction of the total expected events have occurred."
   - **Single-look triggering endpoint (k=1):** If the endpoint that triggers an analysis is only tested once at that analysis (e.g., PFS tested only at the IA), there is NO information fraction to ask — the IA timing is fully determined by the number of events needed for that endpoint's test (driven by power, alpha, and HR). The non-triggering endpoint's IF at that analysis is calculated from the shared timeline. **Skip Q9 entirely for this case.**
   - **Multi-look triggering endpoint:** Only ask the information fraction for the **triggering endpoint** at each analysis. The non-triggering endpoint's IF is **calculated, not asked**.
   - If co-primary separate schedules: ask fractions separately per endpoint
   - Common choices: 50%, 60%, 75% (1 IA); 33%/67%, 50%/75% (2 IAs)
   - **Key concept:** Information fraction only applies to endpoints with multiple looks. For a single-look endpoint, 100% of its events are used at its only analysis — there is no fraction to choose.

   *(If multi-population)* After computing the design, present the derived event table for confirmation:

   | Analysis | PFS events (sub) | PFS events (ITT) | OS events (sub) | OS events (ITT) |
   |----------|------------------|-------------------|-----------------|------------------|
   | IA1 | ~NNN | ~NNN | ~NNN | ~NNN |
   | FA | — | — | ~NNN | ~NNN |

   "Do these event counts look reasonable, or would you like to adjust?"

10. *(Skip if no interims)* "How do you want to spend your alpha (false-positive budget) across the interim and final analyses?"
    - A) Conservative early, save most for the final look — Lan-DeMets O'Brien-Fleming (sfLDOF)
    - B) Moderately conservative — Hwang-Shih-DeCani gamma=-4 (sfHSD, gamma=-4)
    - C) Moderate — Hwang-Shih-DeCani gamma=-2 (sfHSD, gamma=-2)
    - D) Aggressive early, spread evenly — Lan-DeMets Pocock (sfLDPocock)
    - E) Other

    *(If multi-population)* "Should the same spending function be used for all hypotheses?"
    - A) Yes — same for all
    - B) No — specify per endpoint or per population

11. "How sure do you need to be that the trial will detect a real benefit if it exists? Higher power means a bigger study."
    - A) 80% — standard, smaller study
    - B) 85% — moderate confidence
    - C) 90% — higher confidence, larger study
    - D) Other — specify a percentage

    *(If co-primary endpoints)* Whether to ask power for each endpoint depends on what triggers its **last look**:
    - If an endpoint's last look is triggered by **itself** → its power is a free parameter — **ask the user**.
    - If an endpoint's last look is triggered by **another endpoint** → its power is derived — **calculate it, don't ask**.

    **Example 1:** IA1→PFS, IA2→OS, FA→OS. Only ask OS power.
    **Example 2:** IA→PFS, FA→OS. Ask power for both.

    *(If multi-population)* Ask power for the **lead hypothesis** that drives the study size (typically OS in the subpopulation for step-down, or OS in the broadest population for alpha-split). Gated hypotheses have their power calculated.

12. *(Skip if no interims)* "Should the study also be able to stop early for *futility* — i.e., if the drug clearly isn't working?"
    - A) Yes, with a non-binding rule (advisory, not forced)
    - B) Yes, with a binding rule (must stop if crossed)
    - C) No — efficacy stopping only

    *(If co-primary or multi-population)* Also ask which hypothesis/hypotheses should have futility stopping.

    *(If futility requested)* "How should the futility boundary be determined?"
    - A) **Beta spending** — boundary controls probability of stopping under H1.
    - B) **Under the null** — boundary set for high probability of stopping when HR=1.

    **Event inflation depends on binding vs non-binding:**
    - **Binding (test.type=3):** Beta spending inflates events.
    - **Non-binding (test.type=4):** No event inflation regardless of spending function or gamma.
    - **Under the null:** No event inflation.

    *(If beta spending)* "Which spending function for futility?"
    - A) HSD gamma=-2 — moderate (aggressive boundary)
    - B) HSD gamma=-4 — conservative
    - C) HSD gamma=-6 — very conservative
    - D) HSD gamma=-20 — minimal (boundary rarely crossed under H1)
    - E) Other

13. "How fast do you expect to enroll patients?"
    - A simple steady rate (e.g., "15 patients/month")
    - A ramp-up schedule (e.g., "5/month for 3 months, then 10/month, then 15/month")

13b. "What range of total sample size do you consider feasible for this trial? This helps us check whether the computed design falls within practical limits."
    - Example: "600–900 patients" or "no more than 800"
    - If the user provides a range, store it. After the design is computed, compare the resulting total N against this range. If N falls outside the range, flag it and discuss options (adjust alpha split, relax power target, change enrollment, etc.).
    - **N sensitivity exploration must center around the user's stated range.** The user's range reflects what is feasible and desired — anchor exploration there. If the user says "less than 600", explore e.g., 500–600 in steps of 20. If the user says "600–900", explore that range. Do NOT start from the computed minimum N and work up — that wastes the user's time on infeasible or uninteresting values.
    - **N values must be consistent with the enrollment ramp.** Do NOT use arbitrary round numbers (e.g., 520, 560, 600). Instead, compute the actual N that results from varying the last enrollment period duration. With a ramp of 5/mo×2mo + 20/mo×3mo + 30/mo×Kmo, the only free parameter is K (months of steady-state enrollment). Iterate over K values and report the resulting N = 5×2 + 20×3 + 30×K = 70 + 30K. For example: K=15→520, K=16→550, K=17→580, K=18→610. This ensures every N in the sensitivity table is achievable with the stated enrollment rates.
    - If the user says "no constraint" or declines to specify, skip and proceed.

14. "What percentage of patients do you expect to drop out of the study per year?"
    - A) ~2% per year
    - B) ~5% per year
    - C) ~10% per year
    - D) Other

    *(If co-primary endpoints)* Ask dropout separately for each endpoint.

15. *(Skip if no interims)* "What is the minimum follow-up you want before the first interim analysis? This is the time between when the last patient enrolls and when the first IA occurs."
    - A) 3 months
    - B) 6 months
    - C) Other — specify

16. *(Skip if no interims)* "What is the minimum gap you want between any two consecutive analyses (including IA→FA)? This accounts for data cleaning, database lock, and review time."
    - A) 6 months
    - B) 9 months
    - C) 12 months
    - D) Other — specify

    **Q15 and Q16 are minimum constraints, not fixed inputs.** The actual IA and FA timing is driven by event targets (information fractions or power requirements). The min follow-up and min gap only apply as lower bounds — if the event-driven timing already satisfies them, use the event-driven timing. Only push the analysis later if the event-driven timing would violate a constraint. This prevents over-powering the design by forcing analyses later than needed.

After all inputs are collected, **summarize everything in a clean table** and ask the user to confirm before running any computation.

### Confirmation Table Template (Single Population)

| Parameter | Value |
|-----------|-------|
| Disease / Setting | 1L metastatic NSCLC |
| Endpoints | Co-primary PFS + OS |
| Randomization | 1:1 |
| Control median PFS / OS | 8 mo / 20 mo |
| Target HR (PFS / OS) | 0.69 / 0.74 |
| Total alpha | 0.025 (one-sided) |
| Alpha split | PFS: 0.005, OS: 0.020 |
| Alpha reallocation | Full bidirectional |
| Analysis schedule | IA (PFS-triggered), FA (OS-triggered) |
| Alpha spending | Lan-DeMets OBF (both) |
| OS Power | 90% |
| Futility | Non-binding, OS only, HSD gamma=-20 |
| Enrollment | 5/mo × 3 mo, then 20/mo |
| Annual dropout | PFS: 5%, OS: 2% |

### Confirmation Table Template (Multi-Population)

| Parameter | Value |
|-----------|-------|
| Disease / Setting | 1L metastatic NSCLC |
| Populations | BM+ (PD-L1 TPS ≥ 50%, prevalence 50%), ITT |
| Endpoints | PFS + OS in both populations |
| Hypotheses | H1: PFS-BM+, H2: PFS-ITT, H3: OS-BM+, H4: OS-ITT |
| Population strategy | Step-down (subpop → overall) |
| Total alpha | 0.025 (one-sided) |
| Initial alpha | H1: 0.005, H3: 0.020, H2: 0, H4: 0 |
| Gating | H3→H4→H2; H1 tested initially |
| Transition matrix | H1→H3(1), H3→H4(1), H4→H1(0.5)+H2(0.5), H2→H1(1) |
| Randomization | 1:1 |
| Control median PFS (BM+ / ITT) | 8 / 6 mo |
| Control median OS (BM+ / ITT) | 18 / 14 mo |
| Target HR PFS (BM+ / ITT) | 0.60 / 0.70 |
| Target HR OS (BM+ / ITT) | 0.65 / 0.75 |
| Analysis schedule | IA1 + FA |
| Events per hypothesis at each analysis | [computed table] |
| Alpha spending | HSD gamma=-4 (all hypotheses) |
| Power (OS-BM+ at alpha 0.020) | 90% |
| Futility | Non-binding, OS-ITT only |
| Enrollment | 20/mo steady state |
| Annual dropout | PFS: 5%, OS: 2% |

### Pattern Selection

Based on the collected inputs, identify the closest design pattern from `examples.md`. Use the table below as a starting point — **not all designs will match a pattern exactly**.

| Condition | Pattern | examples.md section |
|-----------|---------|---------------------|
| Single endpoint (OS, PFS, or DFS) | Pattern 1 | "Single-Endpoint Design with gsSurv()" |
| Co-primary, alpha split, same triggers for all analyses | Pattern 2 | "Co-Primary Endpoints: Alpha Splitting" |
| Co-primary, fixed-sequence (e.g., DFS → OS) | Pattern 3 | "Co-Primary Endpoints: Fixed-Sequence Testing" |
| Non-proportional hazards (delayed effect) | **Not a standalone pattern** — see "NPH Evaluation Workflow" | Design under PH first, then evaluate under NPH |
| Multi-population, multi-endpoint, multi-arm | Pattern 5 | "Complex Graphical Multiplicity" |
| Co-primary, alpha split, cross-endpoint triggers | Pattern 6 | "Co-Primary Shared-Timing Iterative Workflow" |
| Co-primary, one endpoint tested at a single look only | Pattern 7 | "Co-Primary with Single-Look Endpoint" |

**Single-look (k=1) endpoints**: When a co-primary endpoint has only one analysis (e.g., PFS tested only at the IA), `gsDesign(k=1)` and `gsSurv(k=1)` will fail. Use `compute_single_look_boundary()` from `examples.md` and `nSurv()` for the baseline. See `reference.md` → "gsDesign(k=1) failure" for details.

**Multi-population designs**: Use Pattern 5 for any design with 2+ populations. Events are pre-specified (derived from prevalence via Schoenfeld formula — do NOT use `nSurv()`/`gsSurv()` which can oversize subpopulation designs), boundaries computed via `compute_gsd_boundaries()` per hypothesis, and multiplicity controlled via Maurer-Bretz graphical method. See `reference.md` → "Multi-Population Design" for the alpha recycling priority rules and step-down vs alpha-split strategies.

**Step-down gated hypotheses**: For hypotheses with initial alpha = 0 (gated behind other hypotheses), compute boundaries at **full alpha (0.025)**, not at the alpha that might flow through the gate. The gated hypothesis has no initial allocation — its effective alpha depends entirely on the cascade. Full alpha is the appropriate basis for design properties (boundaries, events, power).

**If no pattern matches exactly**, compose the design from building blocks across multiple patterns. The patterns are not mutually exclusive — real designs often combine elements. For example:
- A co-primary design with non-proportional hazards → design under PH (Pattern 6 or 7), then apply NPH Evaluation Workflow
- A single endpoint with multi-population subgroups → combine Patterns 1 + 5
- A multi-population co-primary with single-look PFS → combine Patterns 5 + 7 (see "Pattern 5+7 Combo" below)
- A 3-endpoint design with mixed fixed-sequence and alpha splitting → adapt Pattern 5

When composing, read `reference.md` → "Analysis Framework" for the 5-perspective approach (hypotheses, multiplicity, IA plan, boundaries, power) to structure any custom design systematically.

**Pattern 5+7 Combo: Multi-Population with Single-Look PFS**

This is a common pattern for aggressive diseases (e.g., 2L SCLC) with short PFS median. Uses the N-first algorithm (see `reference.md` → "N-First Design Algorithm"):

**Phase A — Determine starting N:**
1. Compute required events per hypothesis via Schoenfeld formula
2. Estimate N_min using `estimate_min_N()` (see `examples.md`)
3. Pick starting N from user's feasibility range (Q13b), close to N_min
4. Derive R from enrollment ramp (iterate K for last period)

**Phase B — Design at fixed N:**
1. Find IA time when PFS-ES reaches its Schoenfeld event target (PFS-triggered IA)
2. Compute OS events at IA → derive OS IF
3. Design OS boundaries with `gsSurv(gamma_es, R_fixed, minfup=NULL, T=NULL)` — only for boundaries, not enrollment
4. Find FA time when OS-ES reaches its required events
5. Recompute all cross-endpoint events at final IA and FA times
6. Compute single-look PFS boundaries via `compute_single_look_boundary()`
7. Compute OS GSD boundaries via `compute_gsd_boundaries()`
8. Gated hypotheses: compute boundaries at full alpha (0.025)

**Phase C — Evaluate and adjust N:**
If power < target, timing too late, or OS IF too high → present N adjustment alongside other levers (alpha reallocation, relaxed power). Re-run Phase B.

**N is a top-level design parameter.** All results depend on N. Do NOT let `gsSurv()` determine enrollment — always fix N first, then derive everything from the fixed enrollment.

Key differences from standard Pattern 7: enrollment rates are scaled by prevalence for subgroup hypotheses, events are derived from prevalence (not `nSurv()`), and the multiplicity graph uses Maurer-Bretz with step-down or alpha-split gating.

Then read `reference.md` and the relevant sections of `examples.md` to proceed.

---

## IA Timing Checks

After computing the design (step 6), **read `post_design.md` → "IA Timing Checks"** for the full checklist, warning messages, and user options.

Quick summary — all must pass before proceeding:
- [ ] IA1 occurs at least [Q15 answer] months after enrollment ends
- [ ] Consecutive analyses are at least [Q16 answer] months apart
- [ ] Co-primary endpoint power at each analysis meets user's target

---

## NPH Evaluation Workflow

When the user specifies non-proportional hazards (Q7b = B), follow the **"Design under PH, evaluate under NPH"** approach. Do NOT size the trial directly under NPH — it breaks the IA plan.

**Read `reference.md` → "NPH Evaluation: Design Under PH, Evaluate Under NPH"** for the full rationale, step-by-step algorithm, tool selection rules, and gotchas.

**Read `examples.md` → "NPH Evaluation with lrstat"** for the complete R code pattern.

Summary of the workflow:
1. Complete the PH design (steps 1–7) — this gives events, boundaries, enrollment
2. `expected_time()` → AHR and timing at each PH event target under NPH
3. `gs_power_npe()` → analytical power under NPH
4. `lrsim()` → verify analyticals (timing ±1 mo, power ±2 pp, type I error ±0.5 pp)
5. Present comparison table, assessment, and options to the user

---

## Co-Primary Shared-Timing Design Workflow

When co-primary endpoints share analysis calendar times but different endpoints trigger different analyses, the design requires an **iterative workflow** because the endpoints' event counts are interdependent through the shared timeline. You cannot design both endpoints independently.

**Read `reference.md` → "Co-Primary Shared-Timing: Iterative Design Workflow"** for the step-by-step algorithm.

**Read `examples.md` → "Co-Primary Shared-Timing Iterative Workflow"** for the complete R code pattern.

Key principle: **design the FA-triggering endpoint first** (it drives the study size), then derive everything else from the resulting timeline.

---

## Verification

Every new design MUST be verified by simulation before delivery. **Read `post_design.md` → "Verification"** for the full procedure: what to verify, pass criteria, how to run `lrsim()`, and the verification log template.

Quick pass criteria:
- Power (H1): within ±2 pp of calculated
- Type I error (H0): within ±0.5 pp of alpha
- Events: within ±5% of calculated
- Timing: within ±1 month of calculated

**Non-binding futility**: use `futilityBounds = rep(-6, k-1)` in BOTH H0 and H1 `lrsim()` calls. See `examples.md` → "Verification with lrsim()" for the code.
