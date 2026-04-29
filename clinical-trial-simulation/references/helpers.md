# TrialSimulator-Provided Functions: A Catalog

When TrialSimulator provides a function, **use it** instead of base R
equivalents or external packages. This catalog is what the package
gives you. Reach for these reflexively.

For full argument lists, consult `?<function>` in R or
https://zhangh12.github.io/TrialSimulator/reference/.

> **R6 method visibility.** TrialSimulator's R6 classes expose many
> public methods, but only a curated subset is meant for end users.
> See the "R6 method visibility" section in `SKILL.md` for the full
> list of sanctioned methods. The gotchas below stay within that list.

---

## Enroller

`StaggeredRecruiter` is the only enroller this skill uses. It is **for
`trial(enroller = ...)` only — never as an `endpoint(generator = ...)`**.

| Function | Purpose |
|---|---|
| `StaggeredRecruiter(n, accrual_rate)` | Piecewise-constant-rate accrual. `accrual_rate` is `data.frame(end_time, piecewise_rate)`. Pass via `trial(..., enroller = StaggeredRecruiter, accrual_rate = <data.frame>)`. |

Tip — **simulating a recruitment pause** (e.g., a hold for safety
review after an interim): use a near-zero `piecewise_rate` for the
relevant time window. The schedule still has full coverage; the rate
is just very low during the pause.

```r
accrual_rate <- data.frame(
  end_time       = c(12, 18, Inf),
  piecewise_rate = c(30, 0.001, 30)   # 12 mo at 30/mo, 6 mo near-pause, then 30/mo
)
```

---

## RNGs / endpoint generators

Use these inside `endpoint(generator = ...)`.

### endpoint() grouping rule

Each `endpoint()` call defines **one set of endpoints generated
together by a single generator function**. Endpoints across
**separate** `endpoint()` calls are independent — the package
invokes each set's generator independently.

Two orthogonal decisions:

- **How many endpoints per `endpoint()` call?** This is determined by
  how endpoints group into independent vs. correlated sets. Endpoints
  that need to be correlated must share one `endpoint()` call;
  endpoints that are independent of each other can be split across
  separate calls.
- **Which generator to use?**
  - If a call defines exactly **one** endpoint, the generator can be
    a simple base-R RNG (`rexp`, `rnorm`, `rbinom`, ...) or a custom
    function.
  - If a call defines **two or more** endpoints together, the
    generator MUST be a custom (or built-in) joint generator returning
    a `data.frame` with one column per endpoint (plus `<name>_event`
    columns for TTE endpoints). Base-R RNGs only emit one variable,
    so they cannot be used for multi-endpoint calls.

> **Custom data models — always on the table.** Whenever the user
> has their own data model (a specific distribution, mechanistic
> model, empirical resampling, a custom copula, NORTA, anything),
> help implement it as a custom generator. Base-R RNGs and built-in
> joint generators are convenient defaults, not the only options.
> The contract: `function(n, ...)` returning a `data.frame` with one
> column per endpoint name (plus `<name>_event` columns for TTE).
> First argument must be `n` — wrap if it isn't (e.g., `base::sample`
> uses `x`). See `?endpoint` and `building_blocks.md` for details.

Examples:

- PFS and OS, modeled as independent → two `endpoint()` calls, each
  with `rexp`.
- PFS and OS, modeled as correlated → one `endpoint()` call with
  `CorrelatedPfsAndOs2` (or a custom joint generator).
- PFS+OS correlated, plus three biomarkers correlated among
  themselves but independent of PFS/OS → one `endpoint()` call for
  {pfs, os} with a joint generator, and another `endpoint()` call for
  the three biomarkers with a different joint generator.

### TTE — piecewise / non-PH

| Function | Purpose |
|---|---|
| `PiecewiseConstantExponentialRNG(n, risk, endpoint_name)` | TTE with piecewise-constant hazard. `risk` is `data.frame(end_time, piecewise_risk[, hazard_ratio])`. Use for delayed treatment effects, non-PH scenarios, or any user input expressed as "hazard rate from time A to time B." |

### TTE — correlated PFS + OS (and response)

> **Names are not the model.** The `pfs_name` / `os_name` arguments
> (and `death_name` / `progression_name` / `response_name` for
> `CorrelatedPfsAndOs4`) rename the output columns. The generators
> are structurally about a "shorter, possibly-progressive event"
> bounded above by a "longer, absorbing event" — recognize this
> pattern wherever it appears, not only oncology PFS/OS. Examples:
> time-to-relapse vs. time-to-death (hematology), time-to-MACE vs.
> time-to-all-cause mortality (CV), time-to-disability-progression
> vs. time-to-death (neurology), time-to-first-event vs.
> time-to-fatal-event in any composite-endpoint trial. If the user's
> endpoint pair has the structural PFS ≤ OS relationship, these
> generators apply with renamed columns.

In oncology, PFS and OS are commonly modeled together. **First ask
whether the user wants the correlation modeled explicitly.**

- **Don't model correlation** → two separate `endpoint()` calls. The
  distribution for each (`rexp`, `rweibull`, `PiecewiseConstantExponentialRNG`,
  or a custom function) is the user's call — offer the options.
- **Gumbel copula** (`CorrelatedPfsAndOs2`) → joins latent TTP and OS
  via a Gumbel copula, defining PFS = min(TTP, OS) so PFS ≤ OS by
  construction. Both marginals stay exponential, so the hazard ratio
  between arms is constant — **right choice when Cox PH is the
  planned analysis**. Log-rank also works (it does not require PH).
  User provides median PFS, median OS, Kendall's tau. No solver.
- **Illness-death model** (`CorrelatedPfsAndOs3`) → three-state
  Markov model (stable → progression → death, stable → death
  directly). Induces a **time-varying OS hazard ratio between arms**
  → **incompatible with Cox PH** (HR estimate stops being meaningful).
  Log-rank is still valid (no PH assumption) but may lose power
  against the time-varying alternative; parametric or mechanistic
  analyses are alternatives. Hazards are non-intuitive — derive from
  medians + Pearson correlation via `solveThreeStateModel()` (see
  "Parameter solvers") and hardcode the literals.
- **Custom joint generator** — single multi-endpoint `endpoint()`
  call, generator returns a `data.frame` with `pfs`, `pfs_event`,
  `os`, `os_event`. Use whenever the user has a specific data model
  in mind (a different copula, NORTA, mechanistic, empirical, ...).

| Function | Inputs | Notes |
|---|---|---|
| `CorrelatedPfsAndOs2(n, median_pfs, median_os, kendall, pfs_name, os_name)` | medians + Kendall's tau | PH-compatible |
| `CorrelatedPfsAndOs3(n, h01, h02, h12, pfs_name, os_name)` | three transition hazards | NOT PH-compatible |
| `CorrelatedPfsAndOs4(n, transition_probability, duration, death_name, progression_name, response_name)` | 4×4 transition matrix + duration | Adds objective response as a 4th state. Response is returned as TTE — wrap to convert to binary at a readout time if needed. |

Base R `rexp`, `rnorm`, `rbinom`, `rweibull` etc. are fine for
single-distribution generators — TrialSimulator examples use them
directly. The "prefer TS" rule is about specialized cases (piecewise
hazards, correlated PFS/OS, parameter conversion) where TS provides
something base R doesn't.

---

## Quantile / distribution support

| Function | Purpose |
|---|---|
| `qPiecewiseExponential(p, times, piecewise_risk)` | Quantile of piecewise exponential. Reach for it when building a NORTA or copula construction with a piecewise-exponential marginal — `simdata::simdesign_norta` needs a `function(p)` per marginal. For an *independent* piecewise-exponential endpoint, use `PiecewiseConstantExponentialRNG` directly instead. |

---

## Parameter solvers

These convert clinically interpretable inputs into the parameters the
generators need.

> **Two-step rule.** Any solver that does numerical search
> (`solveThreeStateModel`, and `simdata::simdesign_norta` for NORTA
> setups) is slow. **Run it ONCE in a separate `Rscript` step**,
> capture the chosen literals, show them to the user, and **hardcode
> them** in the simulation script. The simulation script must never
> re-run an optimizer per replicate.

| Function | Purpose |
|---|---|
| `solveThreeStateModel(median_pfs, median_os, corr, h12)` | Convert (median PFS, median OS, target Pearson correlation) → `(h01, h02, h12)` for `CorrelatedPfsAndOs3`. Grid search over `h12`; pick the row with smallest `error`. |
| `solveMixtureExponentialDistribution(weight1, median1, median2, overall_median)` | Two-component exponential mixture: solve for the missing piece. Specify exactly one of `median2` or `overall_median`; the other is returned. Use for enrichment-design subgroup medians. |
| `solvePiecewiseConstantExponentialDistribution(surv_prob, times)` | Convert (survival probabilities at landmark times) → `data.frame(end_time, piecewise_risk)` ready for `PiecewiseConstantExponentialRNG`. Reach for it when the user gives "75% at 12 months, 50% at 24 months." |
| `weibullDropout(time, dropout_rate)` | Convert (dropout rates at two landmarks) → `c(scale, shape)` for `rweibull`. For a single landmark, use `dropout = rexp, rate = -log(1-p)/t` directly — no solver needed. |

### Decision table — given user input, which solver?

| User says | Use |
|---|---|
| Medians + Kendall's tau, Cox/LR planned | `CorrelatedPfsAndOs2` directly (no solver) |
| Medians + Pearson correlation, non-Cox analysis | `solveThreeStateModel` → `CorrelatedPfsAndOs3` (hardcode literals) |
| Survival probability at K landmarks | `solvePiecewiseConstantExponentialDistribution` → `PiecewiseConstantExponentialRNG` |
| Marker subgroup medians + overall median (or vice versa) | `solveMixtureExponentialDistribution` → custom mixture generator |
| Dropout at 2 landmarks | `weibullDropout` → `dropout = rweibull, scale, shape` |
| Dropout at 1 landmark | exponential is the simple default: `dropout = rexp, rate = -log(1-p)/t`. If the user has a different model in mind (e.g., heavier early dropout, time-varying), build a custom dropout function whose first argument is `n` and pass it as `trial(dropout = my_fn, ...)`. |
| Constant uniform accrual | none — `accrual_rate = data.frame(end_time = Inf, piecewise_rate = N)` |
| Ramp-up accrual | none — multi-row `accrual_rate` |
| Recruitment pause window | none — set `piecewise_rate` near zero for the pause window |

---

## Analysis / model fitting

Standardized one-sided wrappers. Each returns a `data.frame` with one
row per experimental arm × placebo pair, with columns `arm`,
`placebo`, `estimate`, `p`, `z`, `info` (some omit `estimate`). The
`...` argument accepts `dplyr::filter` syntax for subsetting (e.g.,
`biomarker == "positive"`).

Use these inside action functions. **Prefer them over hand-rolled
`coxph`/`survdiff`/`glm`/`lm` calls** — the standardized output makes
downstream `trial$save()` clean.

| Function | Method | Covariate adjustment | Notes |
|---|---|---|---|
| `fitCoxph(formula, placebo, data, alternative, scale, ...)` | Cox PH | yes | `scale = "hazard ratio"` or `"log hazard ratio"` — no default; specify explicitly. `formula` is `Surv(time, event) ~ arm [+ covars + strata(...)]`. |
| `fitLogrank(formula, placebo, data, alternative, ...)` | log-rank | no, but supports `strata(...)` | Same `Surv(...)` formula. |
| `fitLogistic(formula, placebo, data, alternative, scale, ...)` | logistic regression | yes | `scale = "coefficient" \| "odds ratio" \| "risk ratio" \| "risk difference"` — no default; specify explicitly. |
| `fitLinear(formula, placebo, data, alternative, ...)` | linear model (ATE via `emmeans`) | yes | |
| `fitFarringtonManning(endpoint, placebo, data, alternative, ...)` | rate-difference test for binary | no | `endpoint` is a column name string, not a formula. |

`alternative` is `"greater"` or `"less"` — one-sided is enforced.

> **Get `alternative` right — it determines whether the simulation
> answers the right question.** The direction of "treatment is
> better" depends on the endpoint:
> - TTE (PFS, OS, time to event): treatment is better when its
>   hazard is lower → `alternative = "less"` for `fitCoxph` /
>   `fitLogrank`.
> - Response rate / risk difference / odds ratio: treatment is
>   typically better when higher → `alternative = "greater"` for
>   `fitLogistic`, `fitFarringtonManning`.
> - Continuous (e.g., change from baseline): direction depends on
>   the endpoint's clinical meaning — improvement could be a
>   higher or lower value. Ask the user.
>
> When in doubt, ask: "Higher values of this endpoint mean
> treatment is working — yes or no?"

For combination tests, graphical testing, group-sequential
boundaries, and other multiplicity procedures, see the
**"Testing and multiplicity"** section in `SKILL.md`. It covers when
to use the package's `dunnettTest` + `closedTest` (seamless /
dose-selection), the `GraphicalTesting` class, hierarchical and
Bonferroni alternatives, and when to fall back to `rpact` /
`gsDesign` for boundaries. Read the package's worked examples
(`?<class>` and the `adaptiveDesign` / `actionFunctions` vignettes)
before writing — the APIs are concrete and easier from a worked
example than from prose.

---

## Action-function utilities

| Function | Purpose |
|---|---|
| `expandRegimen(data)` | Expand the compact `regimen_trajectory` column in locked data into one row per regimen segment per patient (adds `regimen` and `switch_time_from_enrollment`; drops `regimen_trajectory`). Use **inside an action function** — typically right after `trial$get_locked_data(...)` — to make a switching trajectory readable for downstream computation. Only meaningful when treatment switching is enabled via `add_regimen`. |

## Post-simulation utilities

| Function | Purpose |
|---|---|
| `summarizeMilestoneTime(output)` | Summarize triggering times of all milestones across replicates. Returns a `data.frame` with a `plot` method. Input is `controller$get_output()`. **The summary is non-binding** — every replicate runs to completion in simulation, so these times do not reflect early stopping. When the design has a binding-interim rule, also report the binding expected duration derived post-hoc from saved decision flags. |

---

## Non-obvious behaviors (gotchas)

These will bite you if you don't know them.

### Auto-saved milestone columns

Every triggered milestone — even with `action = doNothing` — auto-saves
the following into `controller$get_output()`:

| Column pattern | Meaning |
|---|---|
| `milestone_time_<name>` | Calendar time of the trigger |
| `n_events_<milestone>_<endpoint>` | Observed events (TTE) or non-missing readouts (non-TTE) |
| `n_events_<milestone>_<patient_id>` | Number of enrolled patients at the trigger |
| `n_events_<milestone>_<arms>` | data.frame column: per-arm event/sample counts |

**Do not redundantly save these manually.** Trial duration, event
counts, sample size by arm — already there. Access via
``out[["milestone_time_<final>"]]``,
``out[["n_events_<interim>_<os>"]]``.

`controller$get_output(tidy = TRUE)` drops these from the returned
data frame; use it when the auto-saved columns aren't needed for
reporting. **Caution:** if a custom `save()` name matches the regex
`^n_events_<.*?>_<.*?>$` or `^milestone_time_<.*?>$`, it gets dropped
too. Pick distinctive custom names.

Canonical reference: the "Automatically Saved Results At Triggered
Milestones" table in
https://zhangh12.github.io/TrialSimulator/articles/actionFunctions.html.

### `add_regimen` must precede `add_arms`

```r
tr <- trial(...)
tr$add_regimen(reg)              # MUST be before add_arms
tr$add_arms(sample_ratio, ...)   # errors otherwise
```

### `save_custom_data` namespace + `overwrite`

`save()` and `save_custom_data()` share a name registry. Calling both
with the same `name` errors with "X has been used to name something in
custom data." Use **distinct** names.

The custom-data registry persists across replicates (the value resets
between replicates, but the name doesn't). Without `overwrite = TRUE`,
replicate 2 errors on the duplicate name. **Always set
`overwrite = TRUE` on `save_custom_data()`.**

```r
trial$save_custom_data(value = best_arm, name = "selected", overwrite = TRUE)
trial$save(value = best_arm, name = "selected_arm")
```

When retrieving in a later milestone, guard against `NULL` (the
saving milestone may not have fired):

```r
selected <- trial$get(name = "selected")
if (is.null(selected)) selected <- "<fallback>"
```

### Trials never stop early in simulation

Every replicate runs through all milestones in chronological order,
regardless of any "stopping" rule. TrialSimulator does not bind a
stopping decision to the trial flow — that decision is post-hoc,
derived from rejection / decision flags the user saves at adaptive
milestones. This is intentional: one simulation can score multiple
stopping rules without re-running.

Implication: when the user asks for stopping-aware operating
characteristics, save the decision at each adaptive milestone and
derive the metrics in post-processing.

```r
# In the interim action: save the decision flag.
trial$save(value = as.integer(p_interim <= bound), name = "reject_interim")

# Post-simulation: derive actual stopping time and metrics.
stop_time <- ifelse(out$reject_interim == 1,
                    out[["milestone_time_<interim>"]],
                    out[["milestone_time_<final>"]])

mean(stop_time)               # expected duration accounting for early stopping
mean(out$reject_interim)      # early-stop probability for efficacy
```

`mean(out[["milestone_time_<final>"]])` alone reports the duration
*if every replicate ran to final* — fine for non-binding interim
reporting, misleading when early stopping binds. The same logic
applies to expected sample size, dose-selection timing, futility
stopping, and any other adaptation: save the decision flags
explicitly, then compose them in post-processing.

### `dunnettTest` formula must use `Surv(time, event) ~ arm`

For TTE endpoints. `time ~ arm` errors with "Response must be a
survival object." Same for any wrapper that expects a survival
formula. Skipping combination tests for now per the stub convention,
but note this when you do build it back in.

### Action function signature

Always `function(trial, ...)`. The `trial` is passed by the listener;
extra args (per-milestone configuration) come through `...` and are
specified as `milestone(name = ..., when = ..., action = my_action,
my_arg = value)`.
