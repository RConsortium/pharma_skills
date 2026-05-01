# Post-Design Procedures

Read this file after computing the design (step 6) and before delivering outputs. It covers IA timing checks, verification simulation, and the verification log template.

## Table of Contents

1. [IA Timing Checks](#ia-timing-checks)
   - Check 1: IA before enrollment end
   - Check 2: Data preparation time
   - Check 3: Late IA — alpha or sample size sub-optimality
2. [Verification](#verification)

---

## IA Timing Checks

After computing the design (step 6), perform ALL of the following timing checks. If any check fails, warn the user and present options before proceeding.

Use the user's answers from Q15 (minimum follow-up) and Q16 (minimum gap between analyses) as hard constraints. See `reference.md` → "IA Timing Constraints" for the full constraint resolution algorithm.

**Note on data preparation buffer:** The minimum follow-up (Q15) and minimum gap (Q16) constraints already cover data preparation time. Do NOT ask for a separate buffer — it is redundant. The min follow-up ensures adequate time after enrollment for the first analysis; the min gap ensures enough separation between consecutive analyses (including IA→FA) to accommodate data cleaning, database lock, and review.

**Checklist** (all must pass before proceeding):
- [ ] IA1 occurs at least [Q15 answer] months after enrollment ends (or user accepted with rationale)
- [ ] Consecutive analyses are at least [Q16 answer] months apart (or user accepted)
- [ ] Co-primary endpoint power at each analysis meets user's target (if specified)

### Check 1: IA before enrollment end

Compare each IA calendar time against the enrollment duration. If any IA occurs **before** enrollment completes:

1. **Automatically compute the minimum IF** using `min_if_past_enrollment()` from `examples.md` → "Minimum IF to Clear Enrollment".

2. **Warn the user**:

> "IA1 is estimated at ~X months, but enrollment doesn't complete until ~Y months.
> The minimum IF for [triggering endpoint] at IA1 to clear enrollment is **~Z%**.
>
> This is a concern because:
> 1. **Enrollment bias** — releasing efficacy results while enrollment is ongoing could influence investigators' and patients' willingness to enroll
> 2. **Incomplete sample** — not all planned patients contribute to the analysis
> 3. **Operational complexity** — managing data cuts and enrollment simultaneously
>
> Options:
> - A) **Raise the triggering endpoint's IF** to at least ~Z%
> - B) **Increase enrollment rate** — enrollment finishes faster
> - C) **Set a minimum time constraint** — IA cannot occur before enrollment completes
> - D) **Accept the current timing** — proceed as-is (document the rationale)"

### Check 2: Data preparation time (IA too close to enrollment end or to another IA)

After event targets are reached, studies typically need **3+ months** for data cleaning, database lock, and analysis preparation before the IA can actually be conducted. Check for:

1. **IA too close to enrollment end**: If any IA occurs within 3 months after enrollment end, the actual data cut will happen later than planned. This means more events will have accrued than the design assumed — the boundaries remain valid but the analysis is slightly conservative (actual IF > planned IF). Warn the user and offer to adjust the IA trigger to account for the lag.

2. **Consecutive IAs too close together**: If two consecutive analyses are less than 6 months apart, the data preparation windows overlap. It is operationally impractical to conduct two separate data cuts within 6 months — by the time one analysis is cleaned, locked, and reviewed, the next one is due. Warn the user and suggest merging the analyses or adjusting timing.

**Warning message for data preparation lag** (adapt to specific numbers):

> "The IA is estimated at ~X months, which is only ~Y months after enrollment ends at ~Z months. In practice, data cleaning, database lock, and analysis preparation typically take at least 3 months. By the time the IA is actually conducted (~X+3 months), more events will have accrued than planned:
> - [endpoint] events: planned NNN → actual ~NNN at month X+3
> - OS IF: planned XX% → actual ~XX% at month X+3
>
> The boundaries remain valid (testing at higher IF with OBF-like spending is conservative), but the planned event counts won't match the actual data cut.
>
> Options:
> - A) **Build in a 3-month buffer** — set the IA trigger to the event count expected at month X+3 instead of month X. The design uses the actual IA timing for boundary computation.
> - B) **Accept the mismatch** — keep the current trigger. The analysis will be slightly conservative.
> - C) **Specify a different buffer** — use a custom preparation time (e.g., 4 or 6 months)"

**Warning message for consecutive IAs too close** (adapt to specific numbers):

> "IA1 at ~X months and IA2 at ~Y months are only ~Z months apart. With 3+ months needed for data preparation per analysis, these two data cuts would overlap operationally.
>
> Options:
> - A) **Merge into a single IA** — combine the two analyses into one, timed at the later analysis point
> - B) **Increase the gap** — push one IA earlier or later to create at least 6 months of separation
> - C) **Accept the current timing** — proceed knowing the operational challenge"

Wait for the user to choose before proceeding. If they choose an adjustment, re-run the design with the updated parameters.

### Check 3: Late first IA relative to enrollment end — alpha or sample size sub-optimality

Compute the gap between IA1 and enrollment end:

```
late_ia_gap = IA1_calendar_time - enrollment_duration_months
```

If `late_ia_gap > 9` months, flag a potential design inefficiency. A large gap on the first IA means the study has finished enrolling and patients are simply waiting to have events before any interim look is possible. This often signals that the triggering endpoint's current alpha allocation requires more events than the study can efficiently collect given the enrollment pace.

The two levers that can pull IA1 earlier are:

**Lever 1 — Increase alpha for the IA1-triggering endpoint.** More alpha means a less stringent boundary (lower Z threshold), which requires fewer events to achieve the power target. Fewer required events → IA1 triggered earlier. The alpha must come from somewhere: either reallocate from another endpoint that is over-powered, or accept a lower power target for the donor endpoint.

**Lever 2 — Increase sample size.** More patients → faster event accrual at any given calendar time → IA1 triggered earlier. This lever is independent of the alpha split and does not affect any other endpoint's power.

Present both levers to the user when this check fires:

> "IA1 is estimated at month [X], which is [late_ia_gap] months after enrollment ends at month [Y]. The study has essentially finished enrolling and is waiting for events before the first interim look — this suggests the current design may be inefficient.
>
> Two ways to pull IA1 earlier:
>
> **Option A — Increase alpha for the IA1-triggering endpoint ([endpoint], currently α = [current_alpha])**
> Increasing its alpha reduces the number of events needed, moving IA1 earlier. This alpha must come from another endpoint.
>
> | Scenario | [endpoint] α | [donor endpoint] α | IA1 events | IA1 timing | [endpoint] power | [donor] power |
> |---|---|---|---|---|---|---|
> | Current | [α] | [α_donor] | [events] | Month [X] | [pwr]% | [pwr_donor]% |
> | +0.005 to [endpoint] | [α+0.005] | [α_donor−0.005] | [recalc] | Month [recalc] | [recalc]% | [recalc]% |
>
> **Option B — Increase sample size**
> More patients accelerate event accrual. Increasing N by ~[suggest increment] would move IA1 approximately [estimate] months earlier, with no change to alpha allocation.
>
> **Option C — Accept the current timing**
> Proceed as-is. The design is statistically valid; the late IA1 is an operational observation, not an error."

Compute the reallocation table and the N sensitivity row before presenting this check. The goal is to give the user concrete numbers, not just abstract options.

Only present this check when ALL of the following hold:
- `late_ia_gap > 9` months for IA1
- The IA1-triggering endpoint has initial α > 0 (if α = 0, the endpoint is gated and alpha reallocation requires a different conversation)
- At least one other endpoint or hypothesis has enough power headroom (> 3 pp above target) to donate alpha
- The design already passes Checks 1 and 2

This check is advisory — if the user prefers the current design, proceed without changes.

---

## Verification

Every new design MUST be verified by simulation before delivery. Use `lrstat::lrsim()` to independently confirm the calculated design features.

**Single-look (k=1) endpoints**: `lrsim()` works with `kMax=1`. Use `criticalValues = z_boundary` (single value), omit `futilityBounds`, and `plannedEvents = events` (single value). Same pass criteria apply.

### What to verify

| Feature | Source (calculated) | Source (simulated) | Pass criterion |
|---------|--------------------|--------------------|----------------|
| Events at each IA/FA | `gsSurv()` output `n.I` | `lrsim()` median events at each analysis | Within 5% of calculated |
| Calendar timing of IA/FA | `gsSurv()` output `T` | `lrsim()` median analysis times | Within 1 month of calculated |
| Power (boundary crossing under H1) | `gsSurv()` or `gsDesign()` cumulative upper crossing prob | `lrsim()` rejection rate under alternative | Within 2 percentage points |
| Type I error (under H0) | Alpha (e.g., 0.025) | `lrsim()` rejection rate under null (HR=1) | Within 0.5 percentage points of alpha |
| Efficacy boundaries (Z-scale) | `gsSurv()` output `upper$bound` | Fed into `lrsim()` as `criticalValues` | Exact match (input, not verified) |

### How to run

Write a separate verification script that:

1. **Simulates under H1** (alternative) — uses the design assumptions (enrollment rates, control hazard, experimental hazard, dropout) and the calculated boundaries as `criticalValues`. Run 10,000+ reps. Check:
   - Rejection rate ≈ target power
   - Median events at each analysis ≈ calculated events
   - Median analysis timing ≈ calculated calendar times

2. **Simulates under H0** (null) — same setup but with HR=1 (both arms have control hazard). Check:
   - Rejection rate ≈ alpha (one-sided)

**Batch strategy — run each scenario as a separate Bash call.** Do NOT combine H1 and H0 simulations (or multiple hypotheses) into a single sequential R script invocation. Each `lrsim()` call with 10,000 reps takes 30–120 seconds depending on design complexity; chaining them in one call risks shell timeout before the last scenario completes. Instead, write one `.R` file per scenario and invoke each independently:

```bash
Rscript verify_h1.R   # simulates under H1
Rscript verify_h0.R   # simulates under H0
# For multi-hypothesis designs, one script per hypothesis per scenario
Rscript verify_h1_pfs.R
Rscript verify_h0_pfs.R
Rscript verify_h1_os.R
Rscript verify_h0_os.R
```

Each script should print its results to stdout so you can read them without loading an `.rds` file.

Read `examples.md` → "Verification with lrsim()" for the simulation code.

### Definition of Done

The design is verified when ALL of the following hold:

- [ ] Simulated power under H1 is within 2 percentage points of calculated power
- [ ] Simulated type I error under H0 is within 0.5 percentage points of alpha
- [ ] Simulated median events at each analysis are within 5% of calculated events
- [ ] Simulated median analysis times are within 1 month of calculated times

If any check fails, investigate and fix the design before delivering.

**Non-binding futility (test.type=4) verification rule**: `gsDesign` computes both alpha AND power ignoring futility bounds. ALL `lrsim()` calls must match — disable futility bounds using `futilityBounds = rep(-6, k-1)` in BOTH H0 and H1 simulations. Including futility bounds gives "operational power" which does NOT match the analytical power and will cause verification to fail.

**Known acceptable discrepancy**:
- Timing estimates from `calc_expected_events()` may differ from simulation by up to ~0.5 months due to continuous vs discrete enrollment modeling. This is within the ±1 month tolerance.

### Verification Log

For every new design, save a verification log to the design's output subfolder as `gsd_verification_log.md`. The log should contain:

```markdown
# GSD Verification Log
**Design**: [endpoint, e.g., PFS co-primary]
**Date**: [YYYY-MM-DD]
**Script**: [path to verification R script]
**Simulations**: [number of reps, e.g., 10,000]

## Results

| Metric | Calculated | Simulated | Criterion | Pass? |
|--------|-----------|-----------|-----------|-------|
| Events at IA1 | xxx | xxx | ±5% | Y/N |
| Events at IA2 | xxx | xxx | ±5% | Y/N |
| Events at FA | xxx | xxx | ±5% | Y/N |
| Timing IA1 (mo) | xxx | xxx | ±1 mo | Y/N |
| Timing IA2 (mo) | xxx | xxx | ±1 mo | Y/N |
| Timing FA (mo) | xxx | xxx | ±1 mo | Y/N |
| Power (H1) | xxx% | xxx% | ±2 pp | Y/N |
| Type I error (H0) | xxx% | xxx% | ±0.5 pp | Y/N |

## Overall: PASS / FAIL
```

For co-primary endpoints, include a separate results table for each endpoint. Append to the log file if multiple endpoints are verified in the same design.

**Multi-population designs:** The verification script must simulate and report power AND type I error for ALL hypotheses — including gated hypotheses (H2, H4) at full alpha (0.025). Do not verify only the lead hypotheses (H1, H3) and skip the rest. Each hypothesis has its own boundary, event count, and enrollment subset, so each needs independent verification. The verification log must have a results table for every hypothesis in the design.

**NPH verification (when applicable):** If the design includes an NPH evaluation, the verification log must include a separate section for NPH with BOTH power AND type I error:

```markdown
## NPH Verification (delayed effect: HR=X for 0-Y mo, HR=Z thereafter)

| Metric | Analytical | Simulated | Criterion | Pass? |
|--------|-----------|-----------|-----------|-------|
| Power at FA (H1, NPH) | xxx% | xxx% | ±2 pp | Y/N |
| Type I error (H0, NPH) | xxx% | xxx% | ±0.5 pp | Y/N |
```

The NPH H0 simulation uses the NPH control hazard (piecewise if applicable) with HR=1 on both arms. This confirms that the boundaries designed under PH also control type I error under the NPH null. Do not skip the NPH type I error check — it is required for a complete verification.
