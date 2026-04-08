# Group Sequential Design — Reference Guide

Read this file after collecting user inputs and before writing R code. It contains design guidance, parameter tables, key rules, and failure modes.

## Table of Contents

1. [R Environment](#r-environment)
2. [Core R Packages](#core-r-packages)
3. [Design Parameters](#design-parameters)
4. [Key Rules and Gotchas](#key-rules-and-gotchas)
5. [Spending Functions](#spending-functions)
6. [Multiplicity Strategies](#multiplicity-strategies)
7. [Key Formulas](#key-formulas)
8. [Report Output](#report-output)
9. [Common Failure Modes](#common-failure-modes)
10. [Analysis Framework](#analysis-framework)
11. [Reference Documents](#reference-documents)

---

## R Environment

Use the full path to `Rscript.exe` (or `Rscript` on macOS/Linux) as specified in the project's CLAUDE.md. Use base R pipe `|>` throughout (not `%>%`).

---

## Core R Packages

| Package | Purpose | Key Functions |
|---------|---------|---------------|
| `gsDesign` | Group sequential boundaries, sample size, event-driven design | `gsDesign()`, `gsSurv()`, `nSurv()`, `gsBoundSummary()`, `sfHSD`, `sfLDOF` |
| `gsDesign2` | NPH evaluation: AHR, timing, analytical power | `expected_time()`, `gs_power_npe()`, `gs_b`, `define_enroll_rate()`, `define_fail_rate()` |
| `lrstat` | Log-rank power, sample size, simulation under complex scenarios | `lrpower()`, `lrsamplesize()`, `lrsim()`, `getDesign()` |
| `eventPred` | Enrollment and event timeline prediction via simulation | `predictEnrollment()`, `predictEvent()` |
| `graphicalMCP` | Multiplicity diagrams (Maurer-Bretz graphical method) | `graph_create()` |

---

## Design Parameters

### Trial Structure
| Parameter | Description | Example |
|-----------|-------------|---------|
| Primary endpoint(s) | OS, PFS, DFS — one or co-primary | PFS + OS |
| Key secondary endpoint | If applicable (e.g., ORR) | ORR |
| Randomization ratio | Experimental : Control | 1:1 |
| Number of analyses | Total including final (e.g., 2 = 1 IA + FA) | 3 |
| Information fractions at IAs | Fraction of final events at each IA | c(0.5, 0.75) |

### Survival Assumptions
| Parameter | Description | Example |
|-----------|-------------|---------|
| Control median survival | Median time-to-event for control arm (months) | PFS: 13 mo, OS: 33 mo |
| Hazard ratio (H1) | Target HR under alternative hypothesis | 0.75 |
| Annual dropout rate | Proportion dropping out per year | 5% |

### Error Rates and Spending
| Parameter | Description | Example |
|-----------|-------------|---------|
| Alpha (1-sided) | Type I error rate | 0.025 |
| Power (1 - beta) | Desired power | 90% |
| Efficacy spending function | sfHSD, sfLDOF, sfLDPocock | sfLDOF |
| Efficacy spending parameter | gamma for HSD | -4 |
| Futility spending function | sfHSD or none | sfHSD |
| Futility spending parameter | gamma for HSD | -2 |
| Binding/non-binding futility | test.type 3 (binding) or 4 (non-binding) | Non-binding (test.type=4) |

### Enrollment
| Parameter | Description | Example |
|-----------|-------------|---------|
| Enrollment rates | Patients/month per period | c(5, 10, 15, 15) |
| Period durations | Months per period | c(3, 3, 6, 12) |

### Multiplicity (if co-primary endpoints)
| Parameter | Description | Example |
|-----------|-------------|---------|
| Testing strategy | Fixed-sequence or graphical (Maurer-Bretz) | Fixed-sequence: PFS → OS |
| Alpha allocation | How 2.5% is split initially | PFS: 0.2%, OS: 2.3% |

---

## Key Rules and Gotchas

**`gsSurv()` vs `gsDesign()`:**
- Use `gsSurv()` to **compute** required events and sample size from survival assumptions
- Use `gsDesign()` when events are **already known** (pre-specified in protocol, or computed from subpopulation prevalences)

**T / minfup / R interaction** — critical for `gsSurv()`:

| `T` | `minfup` | Behavior |
|-----|----------|----------|
| NULL | NULL | R is fixed as given. gsSurv computes T and minfup to achieve desired power. |
| NULL | fixed | Last element of R is adjusted to achieve power with specified min follow-up. |
| fixed | NULL | Total duration is fixed. gsSurv derives events/power within that window. |

**Dropout parameterization**: `eta` is a monthly hazard rate — see Key Formulas for the conversion formula.

**Total sample size**: `x$N` does not exist on `gsSurv` objects. Always use `sum(x$gamma * x$R)`.

**Enrollment duration rounding**: Always use `ceiling()` (not `round()`) for the total enrollment duration. `gsSurv()` returns non-integer R values (e.g., `R = [3, 40.15]`). The correct approach is a two-step process:

1. **First `gsSurv()` call** with `R = R_init` (e.g., `c(3, 100)`) and `minfup` set — this determines the rough enrollment duration and adjusts the last R element.
2. **Ceiling** the result: `R_ceiled = c(R[1], ceiling(sum(R)) - R[1])`.
3. **Second `gsSurv()` call** with `R = R_ceiled` and **`minfup = NULL`** — this ensures gsSurv uses the ceiled enrollment as-is. If `minfup` is set (even to the same value), gsSurv will re-adjust the last R element internally, defeating the ceiling.

Use `R_ceiled` for ALL downstream calculations — `total_N`, `calc_expected_events()`, `find_event_time()`, and constraint checks. The timing outputs (`$T`) from the second `gsSurv()` call are now based on the ceiled enrollment and can be used directly.

**Critical**: When passing ceiled R to `gsSurv()`, always set `minfup = NULL` and `T = NULL`. Setting `minfup` to any value causes gsSurv to re-solve for the last R element, overwriting the ceiling.

**HR boundaries**: Do NOT compute HR boundaries manually from Z-values. Always parse from `gsBoundSummary()`.

**Power with `gsDesign()`**: `delta = log(HR0/HR) / 2` — the `/2` is critical. Without it, power is massively overestimated.

**eventPred time unit**: Uses **days**. Convert: `daily_rate = monthly_rate / 30.4375`. `predictEvent()` does NOT accept `ngroups` or `alloc` — those belong only to `predictEnrollment()`.

**`nSurv()` for fixed-sample (k=1) baselines**: When you need a single-look design (no interim analyses), use `nSurv()` instead of `gsSurv(k=1)`. `gsSurv(k=1)` and `gsDesign(k=1)` both crash. `nSurv()` computes the required events, enrollment schedule, and timeline for a fixed-sample design without the k>=2 restriction.

**`nSurv()` vs `gsSurv()` field names**: These functions return different field names for the same quantities. Do NOT assume they are interchangeable.

| Quantity | `nSurv()` | `gsSurv()` |
|----------|-----------|------------|
| Required events | `$n` | `$n.I` (vector, one per analysis) |
| Study duration | `$T` | `$T` (vector, one per analysis) |
| Total sample size | `sum(x$gamma * x$R)` | `sum(x$gamma * x$R)` (same) |
| Enrollment periods | `$R` | `$R` |
| Enrollment rates | `$gamma` | `$gamma` |

**`nSurv()` cannot compute events at arbitrary calendar times**: `nSurv()` requires `T = sum(R) + minfup` exactly. It will crash with dimension errors if you try to evaluate events at a calendar time during the enrollment period (T < sum(R)). **Fix**: Use the analytical `calc_expected_events()` helper function (see `examples.md` → "Analytical Expected Events Calculator") which integrates the event probability over the enrollment schedule without this constraint.

**Competing risk adjustment in `calc_expected_events()`**: When computing expected events analytically (see `examples.md` → "Analytical Expected Events Calculator"), always include the competing risk factor `lambda/(lambda+eta)` per arm. This accounts for dropout as a competing risk. Without it, dropouts are counted as events, overestimating events by ~5% (for 5% annual dropout). Note: `gsSurv()` already accounts for competing risk internally — this rule only applies to the analytical helper function.

**`lrsim()` output structure**: Returns a list with `$overview` (aggregated summary) and `$sumdata` (per-iteration data frame), NOT a flat data frame. Access rejection rate via `sim$overview$overallReject`, events via `sim$overview$numberOfEvents`, timing via `sim$overview$analysisTime`.

**`lrsim()` requires `accrualDuration`**: Always pass `accrualDuration = <total enrollment months>`. Omitting it causes an error.

**Non-binding futility and `lrsim()`**: With `test.type=4` (non-binding futility), `gsDesign`/`gsSurv` compute BOTH alpha AND power as if futility bounds don't exist. All `lrsim()` calls must match:
- **H0 simulation**: omit futility bounds (`futilityBounds = rep(-6, k-1)`) to correctly verify type I error.
- **H1 simulation**: also omit futility bounds (`futilityBounds = rep(-6, k-1)`) to correctly verify statistical power. Including futility bounds gives "operational power" (lower), which does NOT match the analytical power from `gsDesign`/`gsSurv`/`expected_time()`.
- **Rule**: for non-binding futility, NEVER pass the actual futility bounds to `lrsim()`. Always use `rep(-6, k-1)` for both H0 and H1.

### NPH-Specific Gotchas

**Do NOT size trials directly under NPH.** Designing with `gs_design_ahr()` or `lrsamplesize()` under piecewise hazards changes events AND enrollment simultaneously, often causing the IA plan to collapse (IA and FA at the same time). Always design under PH first, then evaluate under NPH. See "NPH Evaluation" section.

**Use `expected_time()` for AHR, not `lrsamplesize()`.** `lrsamplesize()` computes its own event counts under NPH (different from the PH targets), so the AHR is evaluated at the wrong events. `expected_time(target_event = N)` targets the exact PH event count and returns the correct AHR at that point.

**`gs_power_npe()` output `probability` is cumulative.** Each row's `probability` is the cumulative rejection probability up to that analysis, NOT the incremental probability at that analysis. Total power = last upper row's `probability`, not the sum of all upper rows. Summing gives values > 1.

```r
# WRONG: sum gives > 100%
total_power <- sum(res$probability[res$bound == "upper"])

# CORRECT: last upper row is cumulative total
upper_probs <- res$probability[res$bound == "upper"]
total_power <- upper_probs[length(upper_probs)]
```

**NPH comparison table: only show what changes.** Events, boundaries, and type I error are fixed from the PH design — they do not change under NPH. Show only the metrics that differ: timing, AHR, and power. Including type I error (a design parameter) alongside simulated values creates confusion.

**NPH: analytical first, simulation to verify.** The primary NPH results come from analytical functions (`expected_time()` for AHR/timing, `gs_power_npe()` for power). `lrsim()` is used only to verify these analyticals, not as the primary result. Present analytical values in the comparison table; show simulation as a verification block.

---

## Spending Functions

| Function | R Object | Parameter | Behavior |
|----------|----------|-----------|----------|
| Hwang-Shih-DeCani | `sfHSD` | gamma (real number) | gamma=-4: conservative (OBF-like); gamma=-2: moderate; gamma=0: uniform (Pocock-like); gamma=1+: aggressive |
| Lan-DeMets O'Brien-Fleming | `sfLDOF` | none needed | Very conservative early, almost all alpha at final |
| Lan-DeMets Pocock | `sfLDPocock` | none needed | Uniform alpha spending |
| Kim-DeMets (power) | `sfPower` | rho (positive) | rho=3: OBF-like; rho=1: Pocock-like |

**Common protocol choices** (from real trials):
- KN564 DFS: efficacy = `sfLDOF`, futility = `sfHSD` gamma=-6 (non-binding)
- KN564 OS: efficacy = `sfLDOF`, futility = `sfHSD` gamma=-6 (non-binding)
- KN426 PFS: efficacy = `sfHSD` gamma=-2, futility = `sfHSD` gamma=-6
- KN426 OS: efficacy = linear + `sfHSD` gamma=-4 (Haybittle-Peto type), futility = `sfHSD` gamma=-6

---

## Multiplicity Strategies

**Strategy 1: Fixed-Sequence Testing (KN564 pattern)** — Test first endpoint at full alpha. Only if rejected, test second at full alpha.

**Strategy 2: Alpha Splitting with Graphical Method (KN426 pattern)** — Split alpha across endpoints with Maurer-Bretz reallocation upon rejection.

**Strategy 3: Complex Graphical Multiplicity (KN048 pattern)** — Multiple populations, endpoints, and arms with 10+ hypotheses. Use `gsDesign()` with pre-specified events.

**Non-Inferiority Testing**: For NI hypotheses (e.g., margin=1.2), the null is HR ≥ HR0 (not HR ≥ 1). Use `HR0 = 1.2` in HR-at-boundary and power delta. Z-values/p-values are unchanged.

**Multi-Population (Subgroup) Designs**: Events at each analysis differ by population based on prevalence. Events are typically pre-specified. See "Multi-Population Design" section below for the full framework.

**Multiplicity Diagram**: Show ALL weights including "1" on within-chain arrows. For complex diagrams (10+ hypotheses), stagger label positions at 30%/70% along arrows to avoid overlaps.

---

## Multi-Population Design

When a trial tests hypotheses in multiple nested populations (e.g., biomarker+ subgroup and ITT), the design adds complexity in three areas: (1) population testing strategy, (2) alpha recycling across hypotheses, and (3) event derivation from prevalence.

### Choosing Between Step-Down and Alpha Split

**Step-down** is preferred when there is strong prior belief that the subpopulation has a meaningfully better treatment effect than the overall population (e.g., a validated biomarker with known predictive value). In step-down, the subpopulation gets the full alpha and drives the sample size; the overall population is tested only after the subpopulation is positive and is typically overpowered.

**Alpha split** is preferred when there is uncertainty about whether the subpopulation truly has a better treatment effect than the overall population — i.e., the biomarker's predictive value is not well established, or the treatment effect may be similar across populations. Alpha split hedges the bet by giving both populations a chance to succeed independently.

### Alpha Allocation in Alpha-Split Designs

When splitting alpha between populations, **assign more alpha to the subpopulation** than to the overall population. Rationale:

1. **Fewer events in the subpopulation** — due to lower prevalence, the subpopulation accumulates fewer events at each analysis. More alpha compensates by providing a less stringent boundary, maintaining adequate power despite fewer events.
2. **Overall population has more statistical information** — all patients contribute events, so it can achieve good power with less alpha.
3. **Balances power across populations** — without this adjustment, the subpopulation would be underpowered relative to the overall.
4. **Reduces total sample size** — the subpopulation is typically the bottleneck driving enrollment; a more favorable boundary reduces the required events.

**Caveat on efficacy assumptions:** If the subpopulation is believed to have substantially better efficacy (lower HR) than the overall population, the power advantage from the stronger treatment effect may partially or fully offset the event deficit. In that case, a more even alpha split may be appropriate. However, note: if there is strong confidence that the subpopulation has much better efficacy, a **step-down** approach is likely more appropriate than alpha split. The reason alpha split is chosen is precisely because we are *not* confident the subpopulation is clearly superior — and in that scenario, assigning more alpha to the subpopulation is a reasonable default to compensate for the event disadvantage.

### Population Testing Strategies (Summary)

**Step-down**: Test subpopulation first at full alpha. Overall population tested only after subpopulation is positive. Subpopulation drives sample size; overall is typically overpowered. Use when there is strong belief in subpopulation superiority.

**Alpha split**: Divide alpha between populations upfront (more to subpopulation). Each population tested independently. Use when uncertain about subpopulation superiority.

### Alpha Recycling Priority Rules

These rules govern how freed alpha flows when a hypothesis is rejected in a multi-population, multi-endpoint design. Use these rules to **construct the transition matrix** rather than asking the user to specify raw weights.

**Rule 1: OS > PFS within a population.**
OS is the more important endpoint. If OS is positive in a population, that population is considered positive regardless of PFS. Therefore: **PFS rejection → pass alpha to OS in the SAME population first.**
- Example: H1 (PFS-subpop) rejected → alpha to H3 (OS-subpop), not to H2 (PFS-ITT).
- **PFS transitions are unambiguous.** When PFS is rejected, the only goal is to boost OS in the same population. This means PFS transitions typically use weight = 1.0 (Rule 5), because there is a single clear destination — no epsilon needed.

**Rule 2: OS positive → pass alpha to OS in the next population.**
Once OS is significant in one population, the next priority is OS significance in a broader population.
- Example (step-down): H3 (OS-subpop) rejected → alpha to H4 (OS-ITT).

**Rule 3: Only pass alpha where it is needed (step-down only).**
In step-down designs with gating, do NOT pass alpha to a hypothesis that must already be rejected for the current hypothesis to be testable. In a gating chain A → B, do not create a transition from B back to A.
- Example: H4 (OS-ITT) requires H3 (OS-subpop) rejection. Do NOT create H4→H3 transition.
- Example: H2 (PFS-ITT) requires H4 (OS-ITT) rejection. Do NOT create H2→H4 transition.
- **Note:** This rule does not apply to alpha-split designs, where all hypotheses are tested from the start with no gating. In alpha-split, any hypothesis can pass alpha to any other — the recycling is governed by Rules 1, 2, 4, and 5 instead.

**Rule 4: Split alpha to give multiple hypotheses a chance.**
When a hypothesis is rejected and multiple hypotheses could benefit, split the freed alpha to maximize the chance of testing as many hypotheses as possible.
- Example: H4 (OS-ITT) rejected → split 0.5 to H1 (PFS-sub, may not be rejected yet) + 0.5 to H2 (PFS-ITT, now open).

**Rule 5: Use epsilon (ε = 0.001) vs 1.0 — intent-based rule.**
The choice between 1.0 and 0.999 depends on whether the freed alpha is intended for exactly one hypothesis or could benefit multiple hypotheses.

**Use weight = 1.0 when:**
- **Only one other hypothesis is intended to receive alpha.** The rejecting hypothesis has a single clear destination with no ambiguity. Example: PFS-sub rejected → OS-sub is the only intended next test, so H1→H2 = 1.0.
- **Only one other hypothesis can possibly be left to test.** Gating or prior rejections guarantee a single recipient. Example: in step-down, H2 (PFS-ITT) can only be tested after H3 and H4 are both rejected. The only hypothesis that might still need alpha is H1. So H2→H1 = 1.0.
- **Always confirm with the user when proposing weight = 1.0.** Even when the rationale is clear, ask rather than silently assume. Present the reasoning and let the user confirm or adjust.

**Use weight = 0.999/0.001 (epsilon) when:**
- **Multiple hypotheses could benefit from the freed alpha.** The primary target gets 0.999, and the remaining 0.001 goes to alternates. This keeps the graph connected, avoids zero-denominator issues in the Maurer-Bretz update formula, and ensures alpha can eventually reach all hypotheses. Example: OS-ITT rejected → 0.999 to OS-sub (primary intent), 0.001 to PFS-sub (alternate).
- **In step-down designs:** PFS-sub rejection might send 0.001 to PFS-ITT (epsilon) and 0.999 to OS-sub, because while the primary intent is OS-sub, PFS-ITT is also a valid destination.

**Epsilon destination matters even for gated hypotheses.** In step-down designs, ITT hypotheses start at alpha = 0 and are gated. But the epsilon still matters: when gates open and hypotheses are rejected, the Maurer-Bretz cascade routes accumulated alpha through each hypothesis's transitions. The user may prefer routing epsilon to OS (priority endpoint) over PFS (same endpoint family) — always ask.

**Step-down vs alpha-split: different recycling dynamics.**
- **Step-down:** Rule 3 (no passing back through gates) heavily constrains the matrix. Many transitions are forced — e.g., if all other hypotheses must be rejected for H to be testable, H's outgoing transition has only one possible recipient (weight = 1.0). Fewer epsilon decisions, but the epsilon destinations that do exist still require user input.
- **Alpha-split:** All hypotheses are active from the start, no gating. More freedom in the transition matrix means more epsilon decisions. Rules 1, 2, 4, and 5 govern the design; Rule 3 does not apply.

### Example: Step-Down, 2 Populations, PFS+OS

Hypotheses:
- H1: PFS in subpopulation (alpha = 0.005)
- H2: PFS in ITT (alpha = 0, gated by H3 AND H4)
- H3: OS in subpopulation (alpha = 0.020)
- H4: OS in ITT (alpha = 0, gated by H3)

Gating: H4 requires H3 rejection. H2 requires both H3 AND H4 rejection (OS must be positive in both populations before PFS-ITT is tested, since OS positive = population positive).

Testing chain: H1 and H3 tested initially → H3 rejection opens H4 → H4 rejection opens H2.

Transition matrix:

| From \ To | H1 | H2 | H3 | H4 |
|-----------|----|----|----|----|
| H1 (PFS-sub) | — | 0 | 1.0 | 0 |
| H2 (PFS-ITT) | 1.0 | — | 0 | 0 |
| H3 (OS-sub) | 0 | 0 | — | 1.0 |
| H4 (OS-ITT) | 0.5 | 0.5 | 0 | — |

Rationale:
- H1→H3 (1.0): Rule 1. PFS→OS same population. **Confirm with user** — could also send epsilon to an ITT hypothesis (e.g., 0.999 to H3, 0.001 to H4). Even though H4 is gated, the epsilon will cascade through H4's transitions when the gate opens.
- H3→H4 (1.0): Rule 2. OS-sub→OS-ITT (step-down gate). **Confirm with user** — could send epsilon to H1 (0.999 to H4, 0.001 to H1).
- H4→H1 (0.5) + H4→H2 (0.5): Rule 4. OS-ITT rejected; H3 already rejected (gate). Split gives both PFS hypotheses a chance — H1 may not be rejected yet, H2 is now open. **Confirm split ratio with user.**
- H2→H1 (1.0): H3 and H4 already rejected (gates for H2). Only H1 might still need alpha. This is the one case where 1.0 is genuinely forced — but still confirm.
- NOT H4→H3: Rule 3. H3 already rejected (gate for H4).
- NOT H2→H4 or H2→H3: Rule 3. Both already rejected (gates for H2).

Note: If H1 is already rejected when H4 passes alpha to H1, the Maurer-Bretz procedure automatically cascades that alpha through H1's transition (H1→H3), and since H3 is also already rejected, it cascades further through H3→H4, etc., until it reaches a non-rejected hypothesis or is exhausted.

### Example: Alpha-Split, 2 Populations, PFS+OS

All 4 hypotheses tested from the start — no gating. Initial alpha (more to subpop per the alpha allocation guidance):
- H1: PFS-subpop (alpha = 0.003)
- H2: PFS-ITT (alpha = 0.002)
- H3: OS-subpop (alpha = 0.015)
- H4: OS-ITT (alpha = 0.005)

Transition matrix (uses epsilon weights per Rule 5 to avoid closed loops):

| From \ To | H1 | H2 | H3 | H4 |
|-----------|----|----|----|----|
| H1 (PFS-sub) | — | 0 | 1.0 | 0 |
| H2 (PFS-ITT) | 0 | — | 0 | 1.0 |
| H3 (OS-sub) | 0.001 | 0 | — | 0.999 |
| H4 (OS-ITT) | 0 | 0.001 | 0.999 | — |

Rationale:
- H1→H3 (1.0): Rule 1. PFS→OS same population. **Confirm with user** — could send epsilon to an ITT hypothesis instead of pure 1.0.
- H2→H4 (1.0): Rule 1. PFS→OS same population. **Confirm with user** — same consideration.
- H3→H4 (0.999): Rule 2. OS-sub→OS-ITT. Primary intent is OS-ITT, epsilon 0.001 to a PFS hypothesis.
- H4→H3 (0.999): OS priority — pass alpha to OS-sub. Epsilon 0.001 to a PFS hypothesis.
- PFS transitions use 1.0 because the intent is unambiguous — when PFS is rejected, the only goal is to boost OS in the same population, not to test PFS in another population.
- OS transitions use 0.999/0.001 because multiple hypotheses could benefit from the freed alpha, and the epsilon keeps the graph connected to prevent zero-denominator issues in the Maurer-Bretz update.

**Epsilon destination for OS hypotheses is a strategic choice — always ask the user.** When an OS hypothesis is rejected and the epsilon goes to a PFS hypothesis, there are two valid strategies:
- **Epsilon to PFS-sub (H1):** The subgroup has fewer events and benefits more from the alpha boost.
- **Epsilon to PFS-ITT (H2):** Prioritizes locking in both co-primary endpoints in ITT first (OS-ITT already positive, so boosting PFS-ITT claims full ITT success).
Do not assume one over the other — present both rationales and let the user decide.

### Transition Matrix Validation (mandatory for step-down designs)

The R design script **must** call `validate_transition_matrix()` immediately after defining the transition matrix. This function programmatically checks Rule 3 — it catches any transition that routes alpha back to a hypothesis that must already be rejected. See `examples.md` → "Transition Matrix Validation" for the implementation.

The function takes two inputs:
1. The transition matrix (rows = from, cols = to)
2. A named list of gate prerequisites for each hypothesis — which hypotheses must be rejected for it to be testable

If any violation is found, the script must **stop with an error**, not just warn. This prevents the mistake from propagating into boundaries, the JSON, or the report.

**When to skip:** Alpha-split designs have no gating, so all transitions are valid. Only enforce for step-down designs.

### Event Derivation from Prevalence

For nested populations, subgroup events are a fraction of overall events based on prevalence:

```
events_subgroup(t) = prevalence × calc_expected_events(t, lambdaC_sub, hr_sub, eta, gamma, R, ratio)
events_ITT(t)      = calc_expected_events(t, lambdaC_ITT, hr_ITT, eta, gamma, R, ratio)
```

The ITT events include all patients (including the subgroup). The subgroup events use subgroup-specific hazard rates and are scaled by prevalence (since only `prevalence × N` patients are in the subgroup).

For the design computation:
1. **Compute required events analytically** using Schoenfeld formula: `events = 4 × (z_α + z_β)² / log(HR)²` for each hypothesis that has a power target. Do NOT use `nSurv()` or `gsSurv()` — they couple enrollment and events in ways that can oversize subpopulation designs.
2. **Size enrollment** to ensure each subpopulation has enough patients: `min_patients = events / avg_competing_risk_factor`, then `total_N = max(min_patients_per_pop / prevalence)`.
3. **Use `gsDesign()` with pre-specified events** (`n.I`) for boundary computation.
4. **Use `calc_expected_events()` and `find_event_time()`** to determine analysis timing from the enrollment schedule.

For step-down designs, the study size is typically driven by OS in the subpopulation (which has the most alpha and a power target). For alpha-split, it may be driven by the broadest population.

---

## Key Formulas

| Quantity | Formula |
|----------|---------|
| Hazard from median | `lambda = log(2) / median_months` |
| Monthly dropout hazard from annual rate | `eta = -log(1 - annual_rate) / 12` |
| Experimental median from HR | `median_exp = median_ctrl / HR` |
| Daily rate from monthly | `daily = monthly / 30.4375` |

---

## Report Output

### Output Directory

Each design gets its own subfolder under `output/`. Name the subfolder descriptively based on the disease, endpoints, and date. Place ALL outputs in the subfolder: report, plots, verification log, and R scripts.

```r
# Create a design-specific subfolder
out_dir <- "output/gsd_1l_mnsclc_pfs_os_20260327"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
```

**Naming convention**: `gsd_{disease}_{endpoints}_{YYYYMMDD}` (e.g., `gsd_1l_mnsclc_pfs_os_20260327`, `gsd_adjrcc_dfs_os_20260401`)

Standard output files (all in the subfolder):
- `gsd_results.json` — Intermediate design results (R → Python bridge)
- `gsd_report.docx` — Word report (generated by Python)
- `multiplicity_diagram.png` — Maurer-Bretz diagram (generated by R via graphicalMCP)
- `gsd_verification_log.md` — Verification results
- `gsd_design.R` — R design script
- `gsd_report.py` — Python report generator
- `gsd_verification.R` — Verification simulation script
- `boundary_plot.png` — HR-scale boundary plot (optional)
- `enrollment_prediction.png`, `event_prediction.png` — Timeline plots (optional)

### Report Generation Pipeline

The report is generated in two steps:
1. **R script** (`gsd_design.R`) — computes the design, saves results to `gsd_results.json` and generates `multiplicity_diagram.png` via `graphicalMCP::graph_create()`
2. **Python script** (`gsd_report.py`) — reads the JSON and diagram, generates `gsd_report.docx` via `python-docx`

This split gives full control over Word formatting (headings, tables, numbering) via Python while keeping all statistical computation in R.

### Report Sections (in order)

Use flat numbering (1, 2, 3...) for sections. Use unnumbered subsection headings within a section. Title uses a plain formatted paragraph (no heading style) to avoid auto-numbering.

1. **Design Assumptions** — Two-column table (Parameter | Value) with all inputs
2. **Interim/Final Analysis Plan** — Brief description + table (Analysis | Endpoints Tested | Trigger | Timing | Purpose)
3. **Multiplicity Strategy** — Description, `multiplicity_diagram.png`, reallocation rules
4. **Efficacy and Futility Boundaries** — One subsection per endpoint:
   - **PFS** subsection — boundary table
   - **OS** subsection — boundary table
5. **Sample Size and Power Summary** — Narrative paragraph, sample size table, power table
6. **Design Assessment** — Critical evaluation of the design with three subsections:
   - **Strengths** — What works well (e.g., high power, alpha reallocation benefit, IA timing, futility flexibility)
   - **Limitations and Considerations** — Potential weaknesses (e.g., IAs too close together, overpowered endpoints, inert futility bounds, long enrollment)
   - **Potential Improvements** — Actionable suggestions to address the limitations

   The assessment MUST be fully data-driven. **Every number, alpha value, and improvement suggestion must be derived programmatically from `gsd_results.json`** — never hardcode specific alpha values, event counts, or improvement targets. When the design is revised (e.g., alpha reallocation), the assessment text must reflect the current state, not a previous iteration. Use conditional logic to decide which limitations and improvements to include (e.g., only suggest alpha reallocation if PFS power > 95%). Common things to check:
   - **IA spacing**: Are consecutive IAs far enough apart (>6 months) to justify separate data cuts?
   - **Power balance**: Is one endpoint overpowered relative to the other? Could alpha be redistributed? **Only suggest alpha reallocation for hypotheses that have initial alpha allocation.** Gated hypotheses (initial alpha = 0) have derived power and alpha — they do not own alpha that can be reallocated. Their high power is a consequence of the design (large event counts, full cascade alpha), not a tunable parameter. Do not flag gated hypotheses as "overpowered" or suggest reallocating from them.
   - **Futility utility**: Are the futility HR thresholds actionable, or so conservative they'll never be crossed?
   - **Enrollment duration**: Is enrollment a bottleneck? Would faster enrollment shift milestones meaningfully?
   - **Alpha reallocation impact**: How much does the cascade benefit the secondary endpoint?
   - **Do NOT suggest "later IA to improve OS IF"** when the IA is triggered by a different endpoint (e.g., PFS). The OS IF at the IA is a derived quantity — moving a PFS-triggered IA later doesn't meaningfully improve OS analysis, it just delays the PFS readout. This suggestion only makes sense when the IA is OS-triggered and the OS IF at that IA is a design choice.
   - **Do NOT report internal algorithmic artifacts as limitations.** Values like `estimate_min_N` (the rough N heuristic from Phase A) are intermediate computational steps, not design properties. If the final verified design meets all power targets, the fact that a rough estimate exceeded the feasibility cap is irrelevant — it just means the estimate was conservative. Only flag genuine weaknesses of the final, verified design (borderline power, long study duration, stringent IA boundaries, etc.).
   - **IA-before-enrollment**: Already flagged in the IA timing check, but note it here too if it applies
   - **Efficacy boundary stringency at IA**: Use these thresholds to characterize IA boundaries:
     - HR at boundary < 0.70 OR cumulative IA power < 50% → **stringent** (hard to cross, requires strong early signal)
     - HR at boundary 0.70–0.85 AND cumulative IA power 50–80% → **moderate** (reasonable chance of early success)
     - HR at boundary > 0.85 OR cumulative IA power > 80% → **lenient** (easy to cross early)
     Do NOT describe an IA boundary as "stringent" if the HR threshold is ≥ 0.70 and the cumulative power is ≥ 50%.
     **Only list IA boundary stringency as a limitation if it is actually stringent** (HR < 0.70 or cumulative IA power < 50%). Moderate or lenient boundaries are not a design weakness — do not flag them in the Limitations section.

     **In the Python report (`gsd_report.py`)**, classify stringency programmatically from the JSON:
     ```python
     def classify_ia_stringency(hr_at_bound, cum_power_at_ia):
         if hr_at_bound < 0.70 or cum_power_at_ia < 0.50:
             return "stringent"
         elif hr_at_bound > 0.85 or cum_power_at_ia > 0.80:
             return "lenient"
         else:
             return "moderate"
     ```
     Use this classification to decide whether to include IA stringency in the Limitations section. Only include it if the result is "stringent".

### Boundary Table Format

Each endpoint gets its own boundary table. Columns:

**Efficacy-only endpoint (e.g., PFS):**

| Analysis | IF | N | Events | Z boundary | p eff. (1-sided) | HR at boundary | Cum. power (H1) | Cum. alpha (H0) |

**Endpoint with futility (e.g., OS):**

| Analysis | IF | N | Events | Z eff. | Z fut. | p eff. (1-sided) | HR eff. | HR fut. | Cum. power (H1) | Cum. alpha (H0) |

- **IF**: Information fraction (events / total events for that endpoint)
- **N**: Sample size enrolled at the time of each analysis
- **Cum. power (H1)**: Cumulative probability of crossing efficacy bound under H1, from `cumsum(d$upper$prob[, 2])`
- **Cum. alpha (H0)**: Cumulative alpha spent, from the **spending function** directly (`sfLDOF(alpha, timing)$spend`), NOT from `cumsum(d$upper$prob[, 1])` — the latter accounts for futility stopping and will be less than nominal alpha for non-binding designs

### IA/FA Plan Table Format

Combine the analysis plan and event summary into a **single table**. Do not use separate tables for the plan and events.

| Analysis | Endpoints Tested | Trigger (run-time) | PFS Events | OS Events | OS IF | Timing (months) | Design-time Driver | Purpose |
|----------|-----------------|-------------------|------------|-----------|-------|-----------------|-------------------|---------|
| IA1 | PFS, OS | XXX PFS events | XXX | XXX | XX% | ~XX | Min follow-up / PFS IF / PFS power | First interim for PFS and OS efficacy |
| FA | OS | XXX OS events | — | XXX | 100% | ~XX | OS power | OS final analysis |

The **Trigger** column lists the operational event count that triggers the analysis (goes in the protocol). The **Design-time driver** column notes which constraint was binding when planning the analysis timing. If the driver differs from the triggering endpoint's IF target, add a footnote explaining the discrepancy (e.g., "584 PFS events exceeds the 80% IF target because minimum follow-up is binding").

### Sample Size and Power Summary

Include a narrative paragraph describing total N, per-arm N, enrollment schedule, enrollment duration, study duration, and minimum follow-up. Then two tables:

**Sample size table** (Parameter | Value):
- Total sample size, Patients per arm, Enrollment duration, Study duration (to FA), Minimum follow-up
- *(If multi-population)* Subgroup N and subgroup N per arm (= total N × prevalence). Include for each subpopulation.

**Power table** (per endpoint):

| Endpoint | Total Events | Allocated Alpha | Power at Allocated Alpha | Power at Full Alpha (0.025) |

### JSON Intermediate Format

The R script saves all design results to `gsd_results.json`. Key fields the Python report expects:
- Assumptions: `disease`, `endpoints`, `randomization`, `ctrl_median_pfs/os`, `hr_pfs/os`, `dropout_annual`, `enrollment`, `alpha_pfs/os`, `spending`, `futility`
- Sample size: `total_N`, `enroll_duration`, `study_duration`, `min_followup_os`
- Analysis plan: `ia1_time`, `ia2_time`, `fa_time`, `pfs_events_ia1/ia2`, `os_events_ia1/ia2/fa`
- PFS boundaries: `pfs_z_upper`, `pfs_p_upper`, `pfs_hr_upper`, `pfs_info_frac`, `pfs_N`, `pfs_cum_cross_h1`, `pfs_cum_cross_h0`, `pfs_power`, `pfs_power_full`
- OS boundaries: `os_z_upper`, `os_z_lower`, `os_p_upper`, `os_hr_upper`, `os_hr_lower`, `os_info_frac`, `os_N`, `os_cum_cross_h1`, `os_cum_cross_h0`, `os_power`, `os_power_full`

**JSON R-to-Python gotcha: named vectors become arrays.** R's `toJSON()` converts named vectors (e.g., `c(H1=0, H2=1, H3=0, H4=0)`) to JSON arrays `[0, 1, 0, 0]`, losing the names. In the Python report script, access these by position index (e.g., `tm['H1'][1]` for the H2 weight), not by name (e.g., `tm['H1']['H2']` will fail). Similarly, `fromJSON()` in R converts JSON lists-of-objects to data frames — access with `$column[row]` (e.g., `res$populations$prevalence[1]`), not `[[1]]$prevalence`. Always test JSON round-trip access patterns before building the report script.

---

## IA Timing Constraints

The calendar time of each analysis is determined by **multiple constraints**, not just one endpoint's information fraction. The analysis happens at whichever constraint is **latest** (most restrictive).

### Constraints for IA1 (first interim)
1. **Triggering endpoint's IF** — the IA1 trigger endpoint must reach its target event count (e.g., PFS at 80% IF)
2. **Minimum follow-up** — IA1 must occur at least X months after enrollment ends (user-specified, typically 3–6 months). This inherently covers data preparation time for the first analysis.
3. **Co-primary endpoint power** — if a non-triggering endpoint has a user-specified power target at this analysis, it may need more events than available at the triggering endpoint's target time, pushing the IA later

### Constraints for subsequent IAs and FA
1. **Triggering endpoint's IF** — same as above
2. **Minimum gap from previous analysis** — must be at least X months after the prior analysis (user-specified, typically 5–12 months). This inherently covers data preparation time — no separate buffer is needed.
3. **Co-primary endpoint power** — same as above (only at the endpoint's last look)

### Resolving constraints

After computing the raw analysis time from the triggering endpoint's IF:
1. Check minimum follow-up (IA1 only): `adjusted_time = max(raw_time, enroll_end + min_followup)`
2. Check minimum gap (all analyses after IA1): `adjusted_time = max(adjusted_time, prev_analysis_time + min_gap)`
3. Check co-primary power: compute non-triggering endpoint's events at `adjusted_time`. If power is below the user's target, find the time needed and set `adjusted_time = max(adjusted_time, power_driven_time)`

If any constraint pushes the IA later than the triggering endpoint's raw target, **report which constraint is binding** and the resulting IFs for all endpoints at the adjusted time. The triggering endpoint's actual IF will be higher than the target IF.

### Information fractions and triggers

An IF target (e.g., 80%) is only meaningful for the endpoint that **triggers** the analysis AND has multiple looks. For a single-look endpoint, IF is always 100% — there is no fraction. Do not ask for IFs of non-triggering endpoints or single-look endpoints; calculate their event counts from the shared timeline.

When the trigger endpoint changes (e.g., due to merging IAs), the old IF target no longer applies. Ask the user for a new IF target for the new triggering endpoint, unless the endpoint now has only one look (in which case IF is not applicable).

### Design-time driver vs run-time trigger

These are two distinct concepts — do not conflate them in the design report or when communicating with the user.

**Design-time driver (planning):** The constraint that determines the *planned calendar time* of an analysis. Multiple constraints are evaluated (triggering endpoint's IF, min follow-up, min gap, co-primary power), and the most restrictive one sets the planned time. This is an internal design consideration — it explains *why* the analysis is planned at a particular time.

**Run-time trigger (operational):** The specific event count that triggers the analysis in practice. This is what goes in the protocol and SAP — e.g., "the IA will be conducted when 609 PFS events are observed." The event count is computed from the planned calendar time.

**Example:** PFS power ≥ 90% requires 433 events (at ~37 months). Min follow-up requires IA at ~48 months. The min follow-up is the binding design-time driver. At 48 months, PFS has ~609 events. The run-time trigger is 609 PFS events. The protocol says "IA triggered by 609 PFS events" — it does NOT say "IA triggered by 3 months after enrollment."

**In the design report:**
- The IA/FA Plan table should list the **run-time trigger** (event count and triggering endpoint)
- The Design Assessment or narrative should note which **design-time constraint** was binding and why

**When a constraint other than the triggering endpoint's IF is binding:**
The actual event count at the analysis will exceed what the IF target alone would require. Report this clearly — e.g., "IA is triggered by 609 PFS events. This exceeds the 80% IF target (559 events) because the minimum follow-up constraint is binding."

---

## Handling Over-Powered Hypotheses

When a hypothesis has power substantially above the target (e.g., >95% vs 90% target), there are two options:

- **A) Increase assigned alpha** — More alpha → fewer events needed for the same power target. The extra alpha must come from another hypothesis. Best when the hypothesis is close to the power target and you need a modest reduction in events. Trade-off: the donor hypothesis gets less alpha.

- **B) Reduce target events (accept derived power)** — Don't target 90% power for this hypothesis. Let the analysis timing be driven by other hypotheses, and accept whatever power results from the available events. Best when the hypothesis has large excess power (e.g., 96%+) and the event count is driven by a shared timeline.

The choice depends on how much excess power exists:
- **Close to 90% (e.g., 91–93%)**: Option A is safer
- **Well above 90% (e.g., 95%+)**: Option B is cleaner
- **Both can be combined**: increase alpha modestly AND accept derived power

---

## Design Iteration Guardrails

When a user requests a structural change to the design, some parameters that were previously derived become free (or vice versa). Before re-running the design, identify these shifts and ask the user for input.

**Principle:** Do not silently re-derive a parameter that the user should have agency over. A structural change may look small but can shift which parameters are consequential.

### Scenario: Endpoint loses looks (e.g., merging IAs)

When merging analyses reduces an endpoint from multi-look to single-look:
- That endpoint's power was previously **derived** from the shared timeline (not a user input)
- With a single make-or-break analysis, power becomes a **consequential free parameter** — the user should decide whether the derived power is acceptable or set a target
- **Ask the user** for a power target before proceeding, with "let it be derived" as one of the options
- If the user sets a target, this may require adjusting alpha allocation, IA timing, or other parameters

**Example:** PFS tested at IA1 + IA2 (2 looks, power derived). User merges IA1 and IA2 → PFS now has 1 look. Ask: "PFS now has a single analysis. What power do you want for PFS?" Options: 80%, 85%, 90%, or let it be derived.

### Scenario: Trigger endpoint changes

When the trigger for an analysis changes (e.g., from PFS-triggered to OS-triggered), the event counts at that analysis shift for all endpoints. Re-confirm information fractions with the user — the original IF targets may no longer be appropriate.

### Scenario: Alpha reallocation structure changes

When the number of hypotheses changes (e.g., dropping PFS from the FA), the multiplicity graph changes. Re-confirm the alpha split and reallocation rules — do not assume the original split still applies.

---

## Common Failure Modes

**This section is a living document.** Add new failure modes when encountered.

### "over-powers" error from gsSurv
When enrollment is much larger than needed, `gsSurv()` may fail. **Fix**: Set `minfup` to a reasonable value (e.g., 12 months for OS) instead of leaving both `T` and `minfup` as NULL.

### gsBoundSummary() column name issues
Columns may have trailing spaces (e.g., `"Analysis "`). Use `trimws()` on column names or match by position.

### delta must be divided by 2 for power calculation
`delta = log(HR0/HR) / 2`, not `log(HR0/HR)`. Forgetting `/2` overestimates power to ~100%.

### NI hypotheses: HR0 is the NI margin, not 1.0
For NI tests (e.g., margin=1.2), use `HR0 = 1.2` in HR-at-boundary and power delta.

### Multiplicity diagram: label placement on crossing arrows
For 14+ hypotheses, place labels at 30% or 70% along arrows instead of 50% midpoint to avoid overlaps.

### gsSurv() vs gsDesign(): when to use which
`gsSurv()` computes events/sample size from survival assumptions. `gsDesign()` with `n.I` when events are already known.

### Schoenfeld vs nSurv with piecewise control hazards
When the control hazard is piecewise (e.g., `lambdaC = c(log(2)/4, log(2)/8), S = 3`) but the HR is constant (PH design), `nSurv()` can massively overestimate required events — e.g., 782 vs Schoenfeld's 477 for alpha=0.001, HR=0.67. The Lachin-Foulkes formula inside `nSurv()` interacts poorly with piecewise hazard specifications, producing inflated event counts.

**Why Schoenfeld is valid here:** With constant HR, the proportion of events from each arm is `1/(1+HR)` — invariant to the baseline hazard level. So the information per event is the same regardless of whether the control hazard is high (early period) or low (later period). The Schoenfeld approximation of D/4 variance per event holds.

**Fix:** For piecewise control hazard with constant HR, use the Schoenfeld formula `events = 4 × (z_α + z_β)² / log(HR)²` for required events. Verify with simulation. Reserve nSurv/Lachin-Foulkes for scenarios where the HR or allocation ratio varies over time.

### Do NOT use nSurv()/gsSurv() to size multi-population designs
`nSurv()` solves for enrollment duration to achieve target power, but it couples enrollment and events in ways that can oversize the design — especially for subpopulations where the effective enrollment rate is `prevalence × gamma`. The Lachin-Foulkes formula inside `nSurv()` may return substantially more events than the Schoenfeld approximation (e.g., 422 vs 324) depending on the follow-up/median ratio. **Fix**: For multi-population designs, compute required events analytically using the Schoenfeld formula `events = 4 × (z_α + z_β)² / log(HR)²`, then size enrollment to support those events. Use `gsDesign()` with pre-specified events for boundary computation.

### Sanity-check: events vs patient count
After computing required events for a subpopulation, verify that the events are achievable given the number of patients. The asymptotic maximum events from N patients (both arms, 1:1) is approximately `N × avg(λ_C/(λ_C+η), λ_E/(λ_E+η))` where η is the dropout hazard. If required events exceed ~95% of this maximum, the design is infeasible or will require an extremely long follow-up. Flag this immediately rather than proceeding with an impossible event target.

### High OS IF at IA: increasing N lowers the OS information fraction
When the OS IF at the IA is very high (>85%), it means the IA and FA provide nearly the same OS information — the FA adds very few incremental events. This is common for short-survival endpoints (e.g., 2L SCLC with median OS 8–10 months) where most OS events occur before the PFS-triggered IA.

**Increasing sample size lowers OS IF at the IA.** The mechanism:
1. More patients → PFS events accrue faster → IA moves earlier in calendar time
2. Earlier IA → fewer OS events at IA (lower numerator)
3. Larger risk set between IA and FA → incremental OS events accrue faster
4. Required OS events at FA stay the same (power-driven) → denominator unchanged or slightly higher
5. Net effect: OS IF drops, IA and FA are better separated, study duration may shorten

This is counterintuitive because one might expect more patients to generate proportionally more events at both analyses, leaving the IF unchanged. The key insight is that the IA is triggered by a **fixed PFS event count**, not a fraction. With more patients, that count is reached earlier, before OS has matured as much.

**When this occurs, run an N sensitivity analysis** exploring N values centered around the user's stated feasibility range (not from the computed minimum). Present a table showing how OS IF, IA timing, FA timing, and study duration change with N so the user can make an informed choice.

**Short-survival amplification**: In aggressive diseases (median OS 8–10 months), the effect is even more dramatic because most OS events occur in the first wave of enrolled patients. Example from 2L SCLC: +17% patients (520→610) cut FA by 27% (47.8→35.0 months). Always flag N-increase as the primary lever when FA timing is a concern in short-survival diseases — the user may accept slightly exceeding their feasibility limit when the timing improvement is large.

### N-First Design Algorithm

**N is a top-level design parameter.** All design results (IA timing, FA timing, events, power) depend on N. The algorithm has three phases.

**Why not let `gsSurv()` determine N?** `gsSurv()` requires an arbitrary `minfup` or `T` to anchor the enrollment solution. Different values give different N, silently baking in a sample size that may not match the user's intent. The N-first approach avoids this by making N an explicit choice.

**Phase A — Determine starting N:**

1. Compute required events per hypothesis via Schoenfeld formula: `events = 4 × (z_α + z_β)² / log(HR)²`
2. Estimate minimum N for each hypothesis:
   ```
   # Average event probability per patient at a given median follow-up
   avg_lambda <- (lambdaC + lambdaC * hr) / 2
   avg_event_prob <- avg_lambda / (avg_lambda + eta) * (1 - exp(-(avg_lambda + eta) * median_followup))
   N_min_h <- events_h / avg_event_prob / prevalence_h
   N_min <- max(N_min_h across hypotheses)  # bottleneck hypothesis
   ```
   Use `median_followup ≈ study_duration / 2` as a rough estimate (refine later). See `examples.md` → `estimate_min_N()` for the helper function.
3. Pick starting N from user's feasibility range (Q13b), close to N_min. If N_min falls outside the range, flag it.
4. Derive R from enrollment ramp: given rates `gamma = c(g1, g2, g3)` and period durations `R = c(d1, d2, K)`, solve `K = ceiling((N - g1*d1 - g2*d2) / g3)`. Actual N = sum(gamma × R).

**Phase B — Design at fixed N:**

All calculations use the fixed R/N. Use `gsSurv()` ONLY for boundary computation (with fixed R, `minfup=NULL, T=NULL`), NOT for enrollment sizing.

1. Find IA time (event-driven, e.g., PFS-triggered)
2. Compute all endpoint events at IA via `calc_expected_events()`
3. Derive OS IF at IA
4. Design OS boundaries: `gsSurv(gamma_sub, R_fixed, minfup=NULL, T=NULL)` — this computes required OS events and boundaries, using the fixed enrollment
5. Find FA time when OS reaches required events
6. Recompute all cross-endpoint events at final IA and FA times
7. Compute all boundaries

**Phase C — Evaluate and adjust N:**

After Phase B, check requirements:
- Power ≥ target for all lead hypotheses?
- FA timing acceptable?
- OS IF at IA reasonable (<85%)?
- N within user's feasibility range?

If any requirement fails, present N adjustment as an option alongside other levers (alpha reallocation, relaxed power target, faster enrollment). When running an N sensitivity analysis, iterate over K (last enrollment period duration) to produce achievable N values consistent with the enrollment ramp. Re-run Phase B with the new N.

### Beta spending futility and sample size (test.type=3 vs test.type=4)
**Binding futility (test.type=3):** Beta spending inflates the required events because the design accounts for trials that stop early for futility under H1, losing power. The more aggressive the futility (less negative `sflpar`), the larger the inflation:
- `sflpar=-2`: ~6% more events than no-futility design
- `sflpar=-6`: ~1% more events
- `sflpar=-20`: effectively zero inflation

**Non-binding futility (test.type=4):** No event inflation regardless of spending function or gamma. `gsSurv()` computes events and power **ignoring the futility boundary entirely** — it assumes the trial always continues. The beta spending function only determines where the futility boundary is placed, not the sample size. The required events match a `test.type=1` (efficacy-only) design exactly.

### nSurv() dimension error at arbitrary calendar times
`nSurv()` crashes with `"attempt to set 'rownames' on an object with no dimensions"` when called with `T < sum(R)` (calendar time during enrollment). It requires `T = sum(R) + minfup` exactly. **Fix**: Use the `calc_expected_events()` analytical helper (see `examples.md`) which works at any calendar time.

### lrsim() "accrualDuration must be provided" error
`lrsim()` requires `accrualDuration` as an explicit parameter. Unlike `gsSurv()`, it does not infer enrollment duration from `accrualTime` and `accrualIntensity`. Always pass `accrualDuration = <total enrollment months>`.

### lrsim() output is not a data frame
`lrsim()` returns an S3 object of class `"lrsim"` with two components: `$overview` (list of aggregated metrics) and `$sumdata` (data frame with per-iteration results). Do NOT index it like a data frame. Use `sim$overview$overallReject` for rejection rate, `sim$overview$numberOfEvents` for mean events per analysis, `sim$overview$analysisTime` for mean timing.

### gsDesign(k=1) and gsSurv(k=1) failure
`gsDesign(k=1)` throws `"input timing must be increasing strictly between 0 and 1"` because the timing parameter validation requires at least two values forming an increasing sequence ending at 1. `gsBoundSummary()` also requires k>=2. **This affects any single-look endpoint** — e.g., PFS tested only at the IA in a co-primary design.

**Fix**: Use `compute_single_look_boundary()` from `examples.md` → "Single-Look (k=1) Boundary Computation":
- Z boundary: `qnorm(1 - alpha)`
- HR at boundary: `exp(-Z * 2 / sqrt(events))`
- Power: `pnorm(delta * sqrt(events) - Z)` where `delta = log(1/hr) / 2`

Use `nSurv()` (not `gsSurv()`) to get the fixed-sample event count and enrollment schedule when k=1 is needed as a baseline.

---

## Co-Primary Shared-Timing: Iterative Design Workflow

When co-primary endpoints share calendar analysis times but different endpoints trigger different analyses (e.g., IA1→PFS, IA2→OS, FA→OS), the design is **iterative** — you cannot design both endpoints independently because their event counts are coupled through the shared timeline.

### Algorithm

**Step 1: Design the FA-triggering endpoint (OS) with a reduced number of looks.**
- Start with a **temporary** 2-look OS design (IA2 at 80% + FA) using `gsSurv()` at the OS alpha. This will be replaced in Step 5 once the IA1 information fraction is known.
- This gives: total OS events, OS calendar times, enrollment schedule, total N.

**Step 2: Compute PFS events at the OS-triggered IA2 calendar time.**
- Use `calc_expected_events()` (NOT `nSurv()`) with PFS hazard parameters at the OS IA2 calendar time.
- This gives: PFS events at IA2 (= PFS's "total" for the design).

**Step 3: Find IA1 calendar time (PFS-triggered).**
- IA1 occurs when PFS reaches X% of its events at IA2.
- Use `find_event_time()` binary search with `calc_expected_events()`.
- This gives: IA1 calendar time.

**Step 4: Compute OS events at IA1.**
- Use `calc_expected_events()` with OS hazard parameters at the IA1 calendar time.
- This gives: OS IF at IA1.

**Step 5: Re-design OS with all 3 looks.**
- Use `gsSurv()` with `timing = c(os_if_ia1, 0.80)` for 3 analyses.
- The total OS events and timeline may shift slightly from Step 1.

**Step 6: Recompute PFS events from the final OS timeline.**
- Recalculate PFS events at IA2 using the Step 5 timeline.
- Recalculate PFS events at IA1 (80% of updated IA2 events).

**Step 7: Design PFS boundaries.**
- Use `gsDesign()` (NOT `gsSurv()`) with the known PFS event counts from Step 6.
- Compute PFS power from `delta = log(1/hr_pfs) / 2`.

**Why this order?** OS power is a free parameter that drives the study size. PFS power is derived — it depends on how many PFS events have accrued by the time OS triggers the analyses.

See `examples.md` → "Co-Primary Shared-Timing Iterative Workflow" for the complete code.

### Variant: Single-Look Endpoint (Pattern 7)

When one endpoint (e.g., PFS) is tested at only one analysis (the IA), the workflow simplifies:

- Steps 1–4: Same (design OS first, compute cross-endpoint events)
- Step 5: Re-design OS with 2 looks (IA + FA) using the derived OS IF at IA
- Step 6: Recompute PFS events at IA from the final OS timeline
- Step 7: Instead of `gsDesign(k=2)`, use `compute_single_look_boundary()` for PFS — no spending function needed for a single look

Use `nSurv()` (not `gsSurv(k=1)`) if you need a k=1 baseline for the OS event count. See `examples.md` → "Co-Primary with Single-Look Endpoint" for the complete code.

---

## Analysis Framework

Whether interpreting an existing protocol/SAP or designing a new trial, always work through these five perspectives in order.

### 1. Hypotheses and Assumptions

- **Identify every primary hypothesis** (H1, H2, ...) — what endpoint, what comparison, what population, superiority or non-inferiority?
- **Map assumptions to each hypothesis**: control median, target HR, HR0 (1.0 for superiority, NI margin for non-inferiority), dropout rate
- **Note population structure**: nested subgroups, prevalences, how they affect expected events
- **Identify the randomization ratio and total sample size**

### 2. Multiplicity Strategy

- **Initial alpha allocation**: how is the overall 2.5% (one-sided) split?
- **Fixed-sequence chains**: which hypotheses are tested in order?
- **Cross-chain reallocation**: where does alpha flow upon rejection? What are the transition weights?
- **Generate the Maurer-Bretz graphical diagram**

### 3. Interim Analysis Plan

- **How many analyses** total? Which endpoints are tested at which analysis?
- **Trigger for each analysis**: event-driven, time-driven, or both?
- **Expected timing** of each analysis (months from study start)
- **Expected events at each analysis** for each endpoint × population combination
- **What decisions are made at each analysis**: efficacy stopping? futility monitoring?

### 4. Statistical Boundaries

- **Alpha spending function** and parameters for each hypothesis
- **Futility spending** if applicable (binding vs. non-binding)
- **Boundary values at each analysis**: Z, p-value, HR at boundary
- **For multi-hypothesis designs**: boundaries at initial alpha AND gated alpha. Also at full alpha=0.025 for reference.
- **Verify HR boundaries make clinical sense** — efficacy boundary HR > 1.0 means something is wrong

### 5. Sample Size and Power

- **Power for each hypothesis** at its allocated alpha level
- **Power at full alpha** (0.025) for reference
- **Total events required** at final analysis for each endpoint/population
- **Total sample size** and whether enrollment supports the required events
- **Sensitivity**: how does power change if the true HR is slightly worse?

### Applying the Framework

**Interpreting an existing protocol**: Extract information for each perspective. Reproduce boundary tables and multiplicity diagram. Flag discrepancies.

**Designing a new trial**: Walk user through perspective 1 (gather assumptions), then 2 (multiplicity strategy), then compute 3-5 and present the full design.

---

## NPH Evaluation: Design Under PH, Evaluate Under NPH

When a user specifies non-proportional hazards (piecewise control hazard and/or non-constant HR), do NOT attempt to size the trial directly under NPH. Instead:

1. **Design under PH** — use `gsSurv()` with constant hazards (Q6 median, Q7 HR) to determine the IA plan: events at each analysis, boundaries, enrollment, and timing.

2. **Evaluate under NPH** — with the PH event targets fixed, use `lrstat::lrpower()` to compute:
   - Expected calendar time to reach those events under NPH
   - Average HR at each analysis (the effective HR the log-rank test sees)
   - Power at each analysis using the PH boundaries

### What is AHR (Average Hazard Ratio)?

The AHR is the **effective HR that the log-rank test statistic reflects at a given analysis time** under non-proportional hazards. It is a weighted geometric mean of the piecewise HRs:

```
AHR(t) = exp( sum[ log(HR_j) × d_j(t) ] / D(t) )
       = product( HR_j ^ (d_j(t) / D(t)) )
```

where `HR_j` is the hazard ratio in period j, `d_j(t)` is the expected events in period j by calendar time t, and `D(t)` is total expected events. Periods with more events get more weight.

The AHR connects NPH assumptions to standard power formulas: `E[Z] ≈ -log(AHR) × sqrt(D/4)`. This means you can plug the AHR into Schoenfeld or `gs_power_npe()` as if it were a constant HR.

**Key properties:**
- Under PH (constant HR), AHR = HR at all times
- Under delayed effect (HR=1 early, HR<1 later), AHR starts near 1 and decreases over time
- High early control hazard amplifies the weight of the HR=1 period, pulling AHR toward 1
- Computed in R via `gsDesign2::ahr(total_duration=t)` or `gsDesign2::expected_time(target_event=D)`

### Why this approach works

The key insight: **boundaries and event counts from the PH design remain valid under NPH.** Alpha spending boundaries depend only on the information fraction (ratio of events at IA to events at FA) and the spending function — not on the underlying hazard model. If the trial targets 395 OS events at the IA and 478 at the FA, the same Z-boundaries and p-value thresholds apply regardless of whether events came from a constant or piecewise hazard distribution.

What changes under NPH:
- **Calendar timing** — events may arrive faster or slower depending on whether the NPH hazards are higher or lower than the PH assumption
- **Average HR** — the log-rank test statistic reflects a weighted average of the piecewise HRs, where the weights depend on how many events fall in each hazard period
- **Power** — because the average HR differs from the constant PH assumption, power at each analysis changes

What does NOT change:
- Event targets at each analysis (fixed from PH design)
- Z-boundaries and p-value thresholds (depend on events and spending, not hazard model)
- Enrollment structure and total N

### Piecewise hazard specification

The user provides breakpoints and values for both the control hazard and the HR. Combined, these define intervals where both are constant:

Example: control hazard = 0.05 (0–12 mo), 0.03 (12+ mo); HR = 0.8 (0–3 mo), 0.7 (3+ mo)

Combined breakpoints: 0, 3, 12
| Interval | Control hazard | HR | Experimental hazard |
|----------|---------------|----|---------------------|
| [0, 3) | 0.05 | 0.8 | 0.040 |
| [3, 12) | 0.05 | 0.7 | 0.035 |
| [12, +) | 0.03 | 0.7 | 0.021 |

### Computing implied control median under piecewise hazards

With piecewise exponential control hazard λ_j on intervals [τ_{j-1}, τ_j):
- S(t) = exp(-Σ λ_j × duration_j) for each completed interval, times the partial interval
- Find t where S(t) = 0.5

Example: λ = 0.05 for [0,12), 0.03 for [12,+)
- S(12) = exp(-0.05 × 12) = exp(-0.6) = 0.549
- Since S(12) > 0.5, median is after 12: t = 12 + (-log(0.5/0.549))/0.03 = 15.1 mo

### Two-step NPH evaluation

**Step A: Average HR and timing via `gsDesign2::expected_time()`** — For each PH event target, compute the expected calendar time and average HR (AHR) under NPH. `expected_time()` targets an exact event count and returns the AHR the log-rank test would observe at that time.

```r
library(gsDesign2)

enroll_rate <- define_enroll_rate(duration = c(3, 41), rate = c(5, 20))
fail_rate <- define_fail_rate(
  duration = c(3, Inf),
  fail_rate = c(0.05, 0.03),
  hr = c(1.0, 0.7),
  dropout_rate = rep(eta_os, 2)
)

nph_ia <- expected_time(enroll_rate = enroll_rate, fail_rate = fail_rate,
                        ratio = 1, target_event = 395)
nph_fa <- expected_time(enroll_rate = enroll_rate, fail_rate = fail_rate,
                        ratio = 1, target_event = 478)

# nph_ia$time  — calendar time to reach 395 events under NPH
# nph_ia$ahr   — average HR at 395 events under NPH
# nph_fa$time  — calendar time to reach 478 events under NPH
# nph_fa$ahr   — average HR at 478 events under NPH
```

**Do NOT use `lrsamplesize()` for AHR** — it computes its own event counts (not the PH targets), so the AHR is evaluated at the wrong events. `expected_time()` targets exact event counts.

**Note on `define_fail_rate()` breakpoints**: The `duration` parameter specifies the *length* of each interval, not the breakpoints. For control hazard 0.05 (0–3 mo), 0.03 (3+ mo) with HR 1.0 (0–3 mo), 0.7 (3+ mo), use `duration = c(3, Inf)`. If the control and HR breakpoints differ (e.g., control changes at 12 mo, HR changes at 3 mo), combine into unified intervals: `duration = c(3, 9, Inf)` with separate rates per interval.

**Step B: Analytical power via `gs_power_npe()`** — Use the AHR, info, and info0 from `expected_time()` with the PH efficacy boundaries to compute exact analytical power under NPH. No simulation needed for the primary result.

```r
library(gsDesign2)

nph_power <- gs_power_npe(
  theta = -log(c(nph_ia$ahr, nph_fa$ahr)),
  info = c(nph_ia$info, nph_fa$info),
  info0 = c(nph_ia$info0, nph_fa$info0),
  upper = gs_b, upar = c(2.23, 2.05),      # PH efficacy boundaries
  lower = gs_b, lpar = c(-Inf, -Inf)        # no futility (non-binding)
)
# nph_power$probability contains rejection prob at each analysis
```

### Power assessment rules

- **Power within 2 pp of PH target**: design is robust, proceed
- **Power drop 2–5 pp**: flag as a concern, present options (increase events, reallocate alpha)
- **Power drop > 5 pp**: the PH design is not appropriate for these NPH assumptions — significant redesign needed

### NPH verification via `lrsim()`

After computing analytical timing (from `expected_time()`) and power (from `gs_power_npe()`), verify BOTH with `lrsim()`. Run H1 and H0 simulations (no futility bounds for non-binding designs):

```r
library(lrstat)

# H1: NPH hazards, no futility (non-binding)
sim_nph_h1 <- lrsim(
  kMax = 2,
  criticalValues = c(2.23, 2.05),
  futilityBounds = rep(-6, 1),          # non-binding: always disable
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, 3), accrualIntensity = c(5, 20),
  accrualDuration = 44,
  piecewiseSurvivalTime = c(0, 3),
  lambda1 = c(0.05, 0.021),            # experimental hazards
  lambda2 = c(0.05, 0.03),             # control hazards
  gamma1 = eta_os, gamma2 = eta_os,
  plannedEvents = c(395, 478),
  maxNumberOfIterations = 10000, seed = 12345
)

# H0: both arms = NPH control, no futility
sim_nph_h0 <- lrsim(
  kMax = 2,
  criticalValues = c(2.23, 2.05),
  futilityBounds = rep(-6, 1),
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, 3), accrualIntensity = c(5, 20),
  accrualDuration = 44,
  piecewiseSurvivalTime = c(0, 3),
  lambda1 = c(0.05, 0.03),             # both arms = control (HR=1)
  lambda2 = c(0.05, 0.03),
  gamma1 = eta_os, gamma2 = eta_os,
  plannedEvents = c(395, 478),
  maxNumberOfIterations = 10000, seed = 67890
)
```

Verify against analyticals:
- Simulated timing (H1) matches `expected_time()` within ±1 month
- Simulated power (H1) matches `gs_power_npe()` within ±2 pp
- Simulated type I error (H0) within ±0.5 pp of alpha

Include both PH and NPH results in the verification log.

### Adding Looks for NPH Robustness

When NPH evaluation reveals low power for an endpoint (e.g., PFS power drops from 90% to 54% due to a delayed treatment effect), **adding an additional analysis for that endpoint** can substantially improve NPH robustness. This is distinct from the traditional reason for adding interims (early stopping) — here the goal is to give the endpoint a second chance at a later timepoint where the AHR has improved.

**Why it works:** Under NPH with delayed effect (HR=1 early, HR=0.65 later), the AHR improves over time as more events accumulate in the post-delay period. A second look at a later timepoint sees a better AHR and has more events, both of which increase power. With OBF-like spending, most alpha is reserved for the later look, providing a meaningful shot at rejection.

**Example:** PFS tested only at IA1 (30 mo) → 54% NPH power. Add PFS testing at IA2 (40 mo, OS-triggered) → 72% NPH power (+18 pp). The second look adds ~80 PFS events and the AHR improves from 0.747 to 0.732.

**When to suggest this:**
- NPH power drops > 10 pp from PH power
- There is a large gap between existing analyses (e.g., 20 months) that could accommodate an additional analysis
- The endpoint's AHR trajectory shows meaningful improvement over the gap period (check via `gsDesign2::ahr()` at multiple timepoints)

**Implementation:**
1. Add the endpoint to an existing or new analysis (e.g., test PFS at the OS-triggered IA2)
2. The endpoint now has 2+ looks and needs a spending function (sfLDOF is a good default — saves most alpha for the later look)
3. The additional analysis's timing is driven by the triggering endpoint (e.g., OS events), not the NPH endpoint
4. **Evaluate NPH power at each candidate timing** to ensure the second look is meaningful — PFS events at IA2 and PFS AHR at IA2 are both derived quantities that depend on the IA2 timing
5. Check that PFS IF at IA1 relative to IA2 is not too high (>95%), which would leave very little alpha for IA2

**Side benefits:**
- Breaks up a large analysis gap (e.g., 20 months → two ~10-month segments)
- PH power actually increases (second chance under favorable conditions too)
- Additional decision point for the trial

### Cross-Endpoint NPH Power as IA Timing Criterion

When an analysis is added specifically for NPH robustness, the timing should be informed by the **NPH endpoint's power**, not just the triggering endpoint's information fraction. When presenting IA2 timing options to the user, always compute and compare the NPH endpoint's:
- Events at each option
- AHR at each option (via `gsDesign2::ahr()`)
- NPH power at each option (via `gs_power_npe()`)

This ensures the timing choice is driven by the actual goal (NPH robustness) rather than just even spacing of the triggering endpoint's analyses.

---

## Reference Documents

Located in `references/` subfolder (bundled with this skill):

- `gsd-tech-manual-text.txt` — gsDesign Technical Manual (text extract).
- `kn426-text.txt` — KEYNOTE-426 (mRCC). Co-primary PFS+OS, alpha splitting, Maurer-Bretz, HSD spending.
- `kn564-text.txt` — KEYNOTE-564 (adjuvant RCC). Fixed-sequence DFS→OS, Lan-DeMets OBF, HSD futility.
- `kn407-text.txt` — KEYNOTE-407 (1L sq NSCLC). Co-primary PFS+OS+ORR, Maurer-Bretz, Lan-DeMets OBF. 3 IAs + FA.
- `kn048-text.txt` — KEYNOTE-048 (1L HNSCC). 3 arms, 3 populations, 14 hypotheses, NI testing. Most complex example.
- `gsDesign.pdf` — gsDesign R package documentation and vignettes.
- `gsDesign2.pdf` — gsDesign2 R package documentation (non-proportional hazards, weighted log-rank).
- `lrstat.pdf` — lrstat R package documentation (log-rank power, sample size, simulation).
- `eventPred.pdf` — eventPred R package documentation (enrollment and event prediction).
