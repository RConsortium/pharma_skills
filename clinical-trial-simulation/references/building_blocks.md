# TrialSimulator Building Blocks API Reference

## endpoint()

```r
endpoint(name, type, readout = NULL, generator, ...)
```

| Arg | Type | Required | Notes |
|-----|------|----------|-------|
| `name` | character vector | yes | One or more endpoint names; must match generator output column names exactly |
| `type` | character vector | yes | `"tte"` or `"non-tte"` per name |
| `readout` | named numeric vector | if non-tte | `c(ep_name = time_value)`; omit or NULL if all TTE |
| `generator` | function(n, ...) | yes | First argument must be `n`; returns data.frame with one row per patient |
| `...` | named values | no | Passed to `generator` at call time |

**Rules:**

- Time units in `readout`, `dropout`, and trial `duration` must be consistent throughout.
- Custom TTE generators must include a `<name>_event` column (1 = event, 0 = censored). Built-in generators (e.g., `rexp`, `PiecewiseConstantExponentialRNG`) handle this automatically for a single TTE endpoint.
- Any function whose first argument is not `n` must be wrapped before passing as `generator` (e.g., `sample()` must be wrapped; `rbinom`, `rnorm` do not).
- `...` can be used to share one generator across arms with different parameter values (e.g., `hr = 0.7`); arms can also use completely independent generators — both are valid.
- All patient-level variables — endpoints, covariates, biomarkers, subgroup flags — must go through `endpoint()`. Baseline variables use `readout = 0` and `type = "non-tte"`; pass their names to `stratification_factors` in `trial()` for stratified randomization.
- Multiple endpoints/variables can be defined in a single `endpoint()` call or across multiple calls — choose based on readability. A single call with a combined generator is convenient when many endpoints share one generator. Separate calls (e.g., `ep1 = endpoint(..., generator = rexp); ep2 = endpoint(..., generator = rnorm)`) are often cleaner when each endpoint has its own simple generator. Pass all resulting objects to `arm$add_endpoints(ep1, ep2, ...)`.
- Repeated measurements of one endpoint: define each visit as a separate name in `name`, with its assessment time in `readout`. The generator returns all visits jointly (one column per visit), allowing correlation across time.

**Generator selection guide:**

| Situation | Generator |
|-----------|-----------|
| TTE, constant hazard | Any parametric distribution; ask the user |
| TTE, piecewise-constant hazard | `PiecewiseConstantExponentialRNG` (recommended built-in) |
| Correlated PFS + OS — Gumbel copula, PH-compatible | `CorrelatedPfsAndOs2`: takes `median_pfs`, `median_os`, `kendall` (Kendall's tau) directly; exponential margins; safe with Cox model |
| Correlated PFS + OS — 3-state illness-death model | `CorrelatedPfsAndOs3`: takes `h01`, `h02`, `h12` derived via `solveThreeStateModel()`; Pearson correlation; may produce time-varying HR — **not safe with Cox model** |
| Correlated PFS + OS + tumor response — 4-state Markov model | `CorrelatedPfsAndOs4` (built-in); response is TTE — wrap to convert to binary if needed |
| Independent non-TTE (binary, continuous, categorical) | Custom function using standard distributions (`rbinom`, `rnorm`, etc.) |
| Correlated endpoints of any type | NORTA via `simdata`: `simdesign_norta(dist, cor_target_final)` + `simulate_data()`; works for any combination of TTE, continuous, binary, categorical as long as a quantile function exists for each marginal; returns matrix — wrap with `as.data.frame()`; add `<name>_event = 1L` for each TTE |
| — TTE marginal + NORTA, piecewise exponential | Must use built-in `qPiecewiseExponential(p, times, piecewise_risk)`; other distributions use standard quantile functions (e.g., `qexp`, `qweibull`) |
| — NORTA correlation feasibility | Target correlation in `cor_target_final` may not be achievable for all marginal combinations (e.g., binary variables have bounded correlation range); `simdesign_norta()` will error if infeasible — inform the user and ask to adjust |
| Repeated measures of one endpoint | Custom function returning one column per visit |
| Baseline variable (covariate, biomarker, subgroup) | Custom function with `readout = 0`; wrap if first argument is not `n` |

**Examples:**

```r
# --- TTE endpoints ---

# Single TTE: pass built-in distribution directly (no _event column needed)
ep_ctrl <- endpoint(name = "os", type = "tte", generator = rexp, rate = log(2) / 12)
ep_exp  <- endpoint(name = "os", type = "tte", generator = rexp, rate = log(2) / 12 * 0.7)

# Shared custom generator across arms via ...
gen_os  <- function(n, median_os, ...) { ... }  # returns: data.frame(os, os_event)
ep_ctrl <- endpoint(name = "os", type = "tte", generator = gen_os, median_os = 12)
ep_exp  <- endpoint(name = "os", type = "tte", generator = gen_os, median_os = 17)

# Independent generators per arm
ep_ctrl <- endpoint(name = "os", type = "tte", generator = gen_control)
ep_exp  <- endpoint(name = "os", type = "tte", generator = gen_experimental)

# Piecewise-constant hazard
risk <- data.frame(end_time = c(...), piecewise_risk = c(...))
ep   <- endpoint(name = "pfs", type = "tte",
                 generator = PiecewiseConstantExponentialRNG,
                 risk = risk, endpoint_name = "pfs")

# Correlated PFS + OS — CorrelatedPfsAndOs2 (Gumbel copula, PH-compatible)
# Use when Cox model or log-rank test is planned. Takes medians and Kendall's tau directly.
ep_ctrl <- endpoint(
  name       = c("pfs", "os"),
  type       = c("tte", "tte"),
  generator  = CorrelatedPfsAndOs2,
  median_pfs = 8,  median_os = 18, kendall = 0.6,
  pfs_name   = "pfs", os_name = "os"
)
ep_exp <- endpoint(
  name       = c("pfs", "os"),
  type       = c("tte", "tte"),
  generator  = CorrelatedPfsAndOs2,
  median_pfs = 12, median_os = 24, kendall = 0.6,
  pfs_name   = "pfs", os_name = "os"
)

# Correlated PFS + OS — CorrelatedPfsAndOs3 (3-state illness-death model, Pearson correlation)
# WARNING: produces time-varying HR between arms — NOT compatible with Cox PH model.
# Use solveThreeStateModel() to derive h01/h02/h12 from medians + target Pearson corr; run per arm.
pars_ctrl <- solveThreeStateModel(
  median_pfs = 8,  median_os = 18,
  corr = seq(0.55, 0.65, by = 0.01), h12 = seq(0.01, 0.50, length.out = 100)
)
best_ctrl <- pars_ctrl[which.min(pars_ctrl$error), ]

pars_exp <- solveThreeStateModel(
  median_pfs = 12, median_os = 24,
  corr = seq(0.55, 0.65, by = 0.01), h12 = seq(0.01, 0.50, length.out = 100)
)
best_exp <- pars_exp[which.min(pars_exp$error), ]

ep_ctrl <- endpoint(
  name      = c("pfs", "os"), type = c("tte", "tte"),
  generator = CorrelatedPfsAndOs3,
  h01 = best_ctrl$h01, h02 = best_ctrl$h02, h12 = best_ctrl$h12,
  pfs_name  = "pfs", os_name = "os"
)
ep_exp <- endpoint(
  name      = c("pfs", "os"), type = c("tte", "tte"),
  generator = CorrelatedPfsAndOs3,
  h01 = best_exp$h01, h02 = best_exp$h02, h12 = best_exp$h12,
  pfs_name  = "pfs", os_name = "os"
)

# Correlated PFS + OS + response — 4-state Markov model
# States: stable -> response / progression / death (absorbing)
# Returns 6 columns: <death_name>, <death_name>_event,
#                    <progression_name>, <progression_name>_event,
#                    <response_name>, <response_name>_event  (response is TTE, not binary)
ep <- endpoint(
  name      = c("os", "pfs", "response"),
  type      = c("tte", "tte", "tte"),
  generator = CorrelatedPfsAndOs4,
  transition_probability = <4x4_matrix>,
  duration               = <large_integer>,  # set larger than trial duration
  death_name             = "os",
  progression_name       = "pfs",
  response_name          = "response"
)

# 4-state model with binary response: wrap to convert time-to-response to binary status
gen_4state_binary <- function(n, readout_time, ...) {
  df <- CorrelatedPfsAndOs4(n = n, ...)
  df$response <- as.integer(df$response <= readout_time)  # overwrite TTE with binary at readout
  df
}
ep <- endpoint(
  name      = c("os", "pfs", "response"),
  type      = c("tte", "tte", "non-tte"),
  readout   = c(response = <readout_time>),
  generator = gen_4state_binary,
  readout_time           = <readout_time>,
  transition_probability = <4x4_matrix>,
  duration               = <large_integer>,
  death_name             = "os",
  progression_name       = "pfs",
  response_name          = "response"
)

# --- Non-TTE endpoints ---

# Binary response at a fixed readout time
gen_resp <- function(n, p, ...) { ... }  # returns: data.frame(response)
ep_ctrl  <- endpoint(name = "response", type = "non-tte",
                     readout = c(response = 8), generator = gen_resp, p = 0.20)
ep_exp   <- endpoint(name = "response", type = "non-tte",
                     readout = c(response = 8), generator = gen_resp, p = 0.40)

# Baseline variable — wrap if first argument is not n (e.g., sample())
gen_stage <- function(n, ...) { ... }  # returns: data.frame(stage)
ep_stage  <- endpoint(name = "stage", type = "non-tte",
                      readout = c(stage = 0), generator = gen_stage)

# --- Repeated measures ---

# Each visit is a separate name; generator returns all visits jointly
ep_visits <- endpoint(
  name      = c("baseline", "visit1", "visit2", "visit3"),
  type      = c("non-tte", "non-tte", "non-tte", "non-tte"),
  readout   = c(baseline = 0, visit1 = 6, visit2 = 12, visit3 = 24),
  generator = gen_visits  # returns: data.frame(baseline, visit1, visit2, visit3)
)

# --- Correlated endpoints — NORTA (simdata package) ---
# Works for any combination of TTE, continuous, binary, categorical.
# simdesign_norta(dist, cor_target_final): dist = list of quantile functions (one per variable)
# Build ONCE outside the generator — runs numerical optimization; capture via closure.
# simulate_data(generator, n) returns a matrix; convert with as.data.frame().
# Add <name>_event = 1L for each TTE variable; tte/non-tte is declared in endpoint(), not here.
# If piecewise exponential marginal: use qPiecewiseExponential(p, times, piecewise_risk).
# Always validate after defining the endpoint — see validation/validate.md.

Sigma <- matrix(c(
  1.00, 0.30, 0.20, 0.10,
  0.30, 1.00, 0.25, 0.15,
  0.20, 0.25, 1.00, 0.10,
  0.10, 0.15, 0.10, 1.00
), nrow = 4, byrow = TRUE)

design <- simdesign_norta(
  dist = list(
    function(p) qexp(p, rate = log(2) / 12),              # os (TTE, exponential)
    function(p) qnorm(p, mean = <mean_sec>, sd = <sd>),   # secondary (continuous)
    function(p) qbinom(p, size = 1, prob = <prev>),        # baseline binary
    function(p) qunif(p, min = 0, max = 1)                 # baseline uniform
  ),
  cor_target_final = Sigma
)

gen_norta <- function(n, ...) {
  df <- as.data.frame(simulate_data(generator = design, n = n))
  colnames(df) <- c("os", "secondary", "baseline_bin", "baseline_unif")
  df$os_event <- 1L  # censoring handled by trial(dropout = ...)
  df
}

ep <- endpoint(
  name      = c("os", "secondary", "baseline_bin", "baseline_unif"),
  type      = c("tte", "non-tte", "non-tte", "non-tte"),
  readout   = c(secondary = 10, baseline_bin = 0, baseline_unif = 0),
  generator = gen_norta
)

# --- Multiple endpoints on one arm — choose based on readability ---

# Separate calls: clean when each endpoint has its own simple generator
ep_os       <- endpoint(name = "os",       type = "tte",     generator = rexp, rate = log(2) / 12)
ep_response <- endpoint(name = "response", type = "non-tte", readout = c(response = 8),
                        generator = rbinom, size = 1, prob = 0.4)
ep_baseline <- endpoint(name = "stage",    type = "non-tte", readout = c(stage = 0),
                        generator = gen_stage)
ctrl$add_endpoints(ep_os, ep_response, ep_baseline)

# Single call: convenient when many endpoints share one combined generator
ep_all <- endpoint(
  name      = c("os", "response", "stage"),
  type      = c("tte", "non-tte", "non-tte"),
  readout   = c(response = 8, stage = 0),
  generator = gen_all  # returns: data.frame(os, os_event, response, stage)
)
ctrl$add_endpoints(ep_all)
```

---

## arm()

```r
arm(name, ...)
```

| Arg | Type | Required | Notes |
|-----|------|----------|-------|
| `name` | character | yes | Arm identifier; used in `get_locked_data()` and analysis formulas |
| `...` | filter conditions | no | `dplyr::filter`-compatible; subset of generator output to use as trial data; omit to use all output |

**Post-construction:** `arm_obj$add_endpoints(ep1, ep2, ...)` — accepts one or more endpoint objects in a single call.

**Example:**
```r
ctrl <- arm(name = "control")
ctrl$add_endpoints(ep_primary, ep_secondary, ep_baselines)

# With subset filter (e.g., biomarker-positive patients only)
exp1 <- arm(name = "experimental", biomarker == "positive")
exp1$add_endpoints(ep_primary, ep_secondary, ep_baselines)
```

---

## trial()

```r
trial(name, n_patients, duration, description = name, seed = NULL,
      enroller, dropout = NULL, stratification_factors = NULL, silent = FALSE, ...)
```

| Arg | Type | Required | Notes |
|-----|------|----------|-------|
| `name` | character | yes | Trial identifier |
| `n_patients` | integer | yes | Initial max enrollment; adjustable via `$resize()` |
| `duration` | numeric | yes | Trial timeframe; adjustable via `$set_duration()` |
| `seed` | numeric/NULL | no | NULL = auto per-replicate |
| `enroller` | function | yes | Returns enrollment time vector of length n; see built-in `StaggeredRecruiter` |
| `dropout` | function | no | Returns dropout time vector of length n |
| `stratification_factors` | character | no | Names of baseline endpoints (`readout = 0`); enables stratified randomization |
| `silent` | logical | no | Suppress messages |
| `...` | any | no | Passed to `enroller` and `dropout` |

**Rules:**
- Units of `duration`, `dropout`, and non-tte `readout` must be consistent.
- Baseline covariates are assumed to have the same distribution across arms.
- `StaggeredRecruiter(n, accrual_rate)` is the standard built-in enroller. `accrual_rate` is a data.frame with columns `end_time` and `piecewise_rate`; pass it via `...`.

**Example:**
```r
accrual <- data.frame(end_time = c(6, 36), piecewise_rate = c(10, 20))

tr <- trial(
  name         = "my_trial",
  n_patients   = 300,
  duration     = 36,
  enroller     = StaggeredRecruiter,
  accrual_rate = accrual,
  dropout      = rexp,
  rate         = -log(0.95) / 12     # 5% dropout by month 12
)
tr$add_arms(sample_ratio = c(1, 1), ctrl, exp1)

l <- listener()
l$add_milestones(m_interim, m_final)
ctr <- controller(trial = tr, listener = l)
ctr$run(n = 1000)
out <- ctr$get_output()
```

---

## Triggering Conditions

Used as the `when` argument in `milestone()`. All return a `Condition` object.
Conditions can be combined: `|` (whichever comes first), `&` (both must be met).

### calendarTime(time)

```r
calendarTime(time)
```

| Arg | Type | Notes |
|-----|------|-------|
| `time` | numeric | Calendar time since first patient enrolled |

```r
milestone(name = "end", when = calendarTime(time = 36))  # triggers at month 36
```

### enrollment(n, ..., arms = NULL, min_treatment_duration = 0)

```r
enrollment(n, ..., arms = NULL, min_treatment_duration = 0)
```

| Arg | Type | Notes |
|-----|------|-------|
| `n` | integer | Number of randomized patients |
| `...` | filter conditions | `dplyr::filter`-compatible; count only matching patients |
| `arms` | character vector | Arms to count; NULL = all active arms |
| `min_treatment_duration` | numeric | Trigger only after patients have been on treatment for at least this long |

```r
enrollment(n = 100)                                             # 100 patients total
enrollment(n = 100, biomarker == "positive")                    # 100 biomarker+ patients
enrollment(n = 1000, arms = c("high dose", "placebo"))          # 1000 in specific arms
enrollment(n = 500, min_treatment_duration = 2)                 # 500 patients with ≥2 months treatment
```

### eventNumber(endpoint, n, ..., arms = NULL)

```r
eventNumber(endpoint, n, ..., arms = NULL)
```

| Arg | Type | Notes |
|-----|------|-------|
| `endpoint` | character | Endpoint name matching `endpoint(name = ...)` |
| `n` | integer | Target event count (TTE) or observation count (non-TTE) |
| `...` | filter conditions | Count only matching subset |
| `arms` | character vector | Arms to count; NULL = all active arms |

```r
eventNumber(endpoint = "os", n = 150)                           # 150 OS events
eventNumber(endpoint = "os", n = 100, arms = c("exp", "ctrl"))  # 100 events in specific arms
```

**Combining conditions:**
```r
when = eventNumber(endpoint = "os", n = 150) | calendarTime(time = 36)  # whichever comes first
```

---

## milestone()

```r
milestone(name, when, action = doNothing, ...)
```

| Arg | Type | Required | Notes |
|-----|------|----------|-------|
| `name` | character | yes | Identifier; used in `get_locked_data(milestone_name)` |
| `when` | Condition | yes | From `calendarTime()`, `enrollment()`, `eventNumber()`, or combinations |
| `action` | function(trial, ...) | no | Defaults to `doNothing`; receives Trials R6 object as first arg |
| `...` | any | no | Extra args passed to `action` |

**Example:**
```r
action_interim <- function(trial, ...) {
  data <- trial$get_locked_data(milestone_name = "interim")
  # ... analysis and adaptations ...
  trial$save(value = <result>, name = "metric")
}

m <- milestone(name = "interim", when = eventNumber(endpoint = "os", n = 75), action = action_interim)
```

---

## listener()

```r
listener(silent = FALSE)
```

| Arg | Type | Notes |
|-----|------|-------|
| `silent` | logical | Suppress console messages |

Monitors the trial and executes action functions when milestone conditions are met.
**Milestones are attached to the listener, not to the trial:** `l$add_milestones(m1, m2, ...)`.

---

## controller()

```r
controller(trial, listener)
```

| Arg | Type | Notes |
|-----|------|-------|
| `trial` | Trial object | From `trial()` |
| `listener` | Listener object | From `listener()` |

```r
l   <- listener()
l$add_milestones(m_interim, m_final)   # attach milestones to listener
ctr <- controller(trial = tr, listener = l)
ctr$run(n = 1000)                       # n = number of replicates (not n_trials)
out <- ctr$get_output()                 # data.frame; one row per replicate
```

---

## regimen()

```r
regimen(what, when, how)
```

| Arg | Type | Notes |
|-----|------|-------|
| `what` | function(patient_data) | Returns data.frame(patient_id, new_treatment); NA rows = skip patient |
| `when` | function(patient_data) | Returns data.frame(patient_id, switch_time); no NAs allowed |
| `how` | function(patient_data) | Returns modified columns + patient_id; NA = unchanged |

All three can be lists of functions executed sequentially.

```r
reg <- regimen(what = fn_who_switches, when = fn_when_to_switch, how = fn_update_data)
tr$add_regimen(reg)
```
