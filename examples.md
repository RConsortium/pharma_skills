# Group Sequential Design — Code Examples

Read this file when you need R code for a specific design pattern. Each section is self-contained.

---

## Enrollment Sufficiency Check

Before calling `gsSurv()`, verify that total enrollment exceeds the approximate required events:

```r
z_alpha <- qnorm(1 - alpha); z_beta <- qnorm(1 - beta)
approx_events <- ceiling(4 * (z_alpha + z_beta)^2 / log(hr)^2)
total_enrollment <- sum(gamma * R)
if (total_enrollment < approx_events * 1.15)
  warning("Enrollment may be insufficient — need total > ~1.15 * required events.")
```

---

## Single-Endpoint Design with `gsSurv()`

```r
library(gsDesign)

x <- gsSurv(
  k         = 3,                    # 2 IAs + final
  test.type = 4,                    # Non-binding futility
  alpha     = 0.025,
  beta      = 0.1,                  # 90% power
  timing    = c(0.50, 0.75),        # IAs at 50% and 75% of events
  sfu       = sfHSD, sfupar = -4,   # Efficacy spending
  sfl       = sfHSD, sflpar = -2,   # Futility spending
  lambdaC   = log(2) / 12,          # Control hazard (median 12 months)
  hr        = 0.75,                 # Target HR
  hr0       = 1,                    # Null HR
  eta       = -log(1 - 0.05) / 12,  # Monthly dropout hazard from 5% annual
  gamma     = c(5, 10, 15, 15),     # Enrollment rates/month per period
  R         = c(3, 3, 6, 12),       # Period durations (months)
  T         = NULL,                 # NULL: let gsSurv compute study duration
  minfup    = NULL,                 # NULL: let gsSurv compute min follow-up
  ratio     = 1                     # 1:1 randomization
)
```

### Key Outputs

```r
ceiling(max(x$n.I))     # Total events at final analysis
ceiling(x$n.I)           # Events at each analysis
sum(x$gamma * x$R)       # Total sample size (DO NOT use ceiling(x$N) — it errors on gsSurv objects)
round(x$T, 1)            # Calendar time of each analysis (months)
x$upper$bound            # Z-scale efficacy boundaries
x$lower$bound            # Z-scale futility boundaries
```

**Important**: `x$N` does not exist on `gsSurv` objects. Always use `sum(x$gamma * x$R)` for total sample size.

### Boundary Summary Table

```r
tab <- gsBoundSummary(x,
  deltaname = "HR",
  logdelta  = TRUE,
  Nname     = "Events",
  digits    = 4,
  ddigits   = 4,
  tdigits   = 1
)
print(tab)
```

### Extracting HR Boundaries from gsBoundSummary

```r
tab_df <- as.data.frame(tab)
hr_rows <- which(grepl("HR at bound", tab_df$Value))
hr_eff <- as.numeric(as.character(tab_df$Efficacy[hr_rows]))
hr_fut <- as.numeric(as.character(tab_df$Futility[hr_rows]))
```

Do NOT try to compute HR boundaries manually from Z-values — the approximation `exp(-Z/sqrt(n.I/4))` is inaccurate. Always parse from `gsBoundSummary()`.

---

## Event-Driven Design with Pre-Specified Events using `gsDesign()`

When the number of events at each analysis is already known (e.g., from a protocol or from expected event calculations across subpopulations), use `gsDesign()` directly instead of `gsSurv()`.

```r
# Efficacy-only design (no futility) with known events
d <- gsDesign(
  k         = 3,                    # Number of analyses
  test.type = 1,                    # One-sided efficacy only
  alpha     = 0.007,                # Allocated alpha for this hypothesis
  sfu       = sfHSD,
  sfupar    = -4,
  n.I       = c(171, 205, 222),     # Events at each analysis
  maxn.IPlan = 222                  # Planned final events
)

# Extract boundaries
d$upper$bound          # Z-scale efficacy boundaries
pnorm(-d$upper$bound)  # One-sided p-values
```

**HR at boundary** — compute from Z boundaries and events:
```r
# For superiority (HR0 = 1): HR_bound = exp(-Z * 2 / sqrt(events))
# For non-inferiority (HR0 != 1): HR_bound = HR0 * exp(-Z * 2 / sqrt(events))
hr_at_bound <- hr0 * exp(-d$upper$bound * 2 / sqrt(d$n.I))
```

**Power calculation** — critical to get right:

```r
# CORRECT: delta = log(HR0/HR) / 2
# The factor of 2 accounts for the variance of log(HR) being 4/d
delta_correct <- log(hr0 / hr) / 2

d_power <- gsDesign(
  k = k, test.type = 1,
  alpha = alpha,
  sfu = sfHSD, sfupar = -4,
  n.I = events,
  maxn.IPlan = events[k],
  delta = delta_correct,
  delta1 = delta_correct,
  delta0 = 0
)
power <- sum(d_power$upper$prob[, 2])
```

**Why `/2`?** The drift of the log-rank Z statistic at analysis j is `log(HR0/HR) * sqrt(d_j / 4)` = `log(HR0/HR) / 2 * sqrt(d_j)`. Since `gsDesign()` computes drift as `delta * sqrt(n.I[j])`, we need `delta = log(HR0/HR) / 2`.

**Common mistake**: Using `delta = log(HR0/HR)` (without `/2`) will massively overestimate power — often showing 100% for everything. Always divide by 2.

---

## Co-Primary Endpoints: Fixed-Sequence Testing (KN564 pattern)

Test DFS first at full alpha=2.5%. Only if DFS is rejected, test OS at alpha=2.5%.

```r
# Design DFS at full alpha
x_dfs <- gsSurv(
  k = 2, test.type = 4,
  alpha = 0.025, beta = 0.05,
  timing = 0.80,
  sfu = sfLDOF,
  sfl = sfHSD, sflpar = -6,
  lambdaC = log(2) / 45, hr = 0.67, eta = -log(1 - 0.02) / 12,
  gamma = c(20, 35, 40), R = c(9, 9, 9),
  T = NULL, minfup = NULL, ratio = 1
)

# Design OS at full alpha (conditional on DFS rejection)
x_os <- gsSurv(
  k = 4, test.type = 4,
  alpha = 0.025, beta = 0.21,
  timing = c(0.47, 0.66, 0.86),
  sfu = sfLDOF,
  sfl = sfHSD, sflpar = -6,
  lambdaC = log(2) / 145, hr = 0.67, eta = -log(1 - 0.01) / 12,
  gamma = c(20, 35, 40), R = c(9, 9, 9),
  T = NULL, minfup = NULL, ratio = 1
)
```

---

## Co-Primary Endpoints: Alpha Splitting with Graphical Method (KN426 pattern)

Split alpha across endpoints with reallocation upon rejection.

```r
# PFS at initial alpha = 0.002
x_pfs <- gsSurv(
  k = 2, test.type = 4,
  alpha = 0.002, beta = 0.01,
  timing = 0.75,
  sfu = sfHSD, sfupar = -2,
  sfl = sfHSD, sflpar = -6,
  lambdaC = log(2) / 13, hr = 0.60, eta = -log(1 - 0.10) / 12,
  gamma = c(60), R = c(15),
  T = NULL, minfup = NULL, ratio = 1
)

# OS at initial alpha = 0.023
x_os <- gsSurv(
  k = 3, test.type = 4,
  alpha = 0.023, beta = 0.20,
  timing = c(0.48, 0.74),
  sfu = sfHSD, sfupar = -4,
  sfl = sfHSD, sflpar = -6,
  lambdaC = log(2) / 33, hr = 0.75, eta = -log(1 - 0.01) / 12,
  gamma = c(60), R = c(15),
  T = NULL, minfup = NULL, ratio = 1
)
```

Document the Maurer-Bretz graphical reallocation rules: when one hypothesis is rejected, its alpha flows to the other endpoint(s) per predefined weights.

---

## Complex Graphical Multiplicity with Many Hypotheses (KN048 pattern)

Helper function for multi-hypothesis event-driven designs:

```r
compute_gsd_boundaries <- function(events, alpha, hr, hr0 = 1.0,
                                    sfu = sfHSD, sfupar = -4) {
  k <- length(events)
  if (alpha < 1e-10) return(NULL)  # Gated hypothesis with no alpha

  d <- gsDesign(
    k = k, test.type = 1,
    alpha = alpha,
    sfu = sfu, sfupar = sfupar,
    n.I = events, maxn.IPlan = events[k]
  )

  z_bound <- d$upper$bound
  p_bound <- pnorm(-z_bound)
  hr_bound <- hr0 * exp(-z_bound * 2 / sqrt(events))

  # Power under the alternative
  delta <- log(hr0 / hr) / 2   # MUST divide by 2
  d_pwr <- gsDesign(
    k = k, test.type = 1,
    alpha = alpha,
    sfu = sfu, sfupar = sfupar,
    n.I = events, maxn.IPlan = events[k],
    delta = delta, delta1 = delta, delta0 = 0
  )
  power <- sum(d_pwr$upper$prob[, 2])

  list(z = z_bound, p = p_bound, hr = hr_bound, power = power, design = d)
}
```

**Gated hypotheses**: In a fixed-sequence chain like H1→H2→H3, H2 starts with alpha=0 but receives H1's alpha when H1 is rejected:

```r
# H1 starts with alpha = 0.0019
res_H1 <- compute_gsd_boundaries(c(211, 237), alpha = 0.0019, hr = 0.58)

# H2 is gated by H1 — compute at H1's alpha (same alpha flows through)
res_H2 <- compute_gsd_boundaries(c(337, 378), alpha = 0.0019, hr = 0.59)

# H3 is gated by H1 and H2 — same alpha flows through the chain
res_H3 <- compute_gsd_boundaries(c(423, 474), alpha = 0.0019, hr = 0.60)
```

**Cross-chain alpha reallocation**: When alpha flows between chains (e.g., PFS→OS), the receiving hypothesis may accumulate alpha from multiple sources. Compute boundaries at each possible alpha level the hypothesis could receive.

---

## Non-Inferiority Testing within Group Sequential Framework

For non-inferiority hypotheses (e.g., OS NI with margin=1.2), the null hypothesis is HR ≥ HR0 (not HR ≥ 1):

```r
# NI test: H0: HR >= 1.2, H1: HR = 0.85
events_ni <- c(352, 421, 455)
hr0_ni <- 1.2    # NI margin
hr_ni  <- 0.85   # Expected HR under alternative

# Boundaries are the same Z-values (alpha spending doesn't depend on HR0)
d_ni <- gsDesign(
  k = 3, test.type = 1,
  alpha = 0.007,
  sfu = sfHSD, sfupar = -4,
  n.I = events_ni, maxn.IPlan = 455
)

# HR at boundary accounts for HR0
hr_bound_ni <- hr0_ni * exp(-d_ni$upper$bound * 2 / sqrt(events_ni))
# e.g., at FA: 1.2 * exp(-2.56 * 2/sqrt(455)) ≈ 0.9435

# Power: delta uses log(HR0/HR), not log(1/HR)
delta_ni <- log(hr0_ni / hr_ni) / 2   # log(1.2/0.85)/2 = 0.1726
d_pwr_ni <- gsDesign(
  k = 3, test.type = 1,
  alpha = 0.007,
  sfu = sfHSD, sfupar = -4,
  n.I = events_ni, maxn.IPlan = 455,
  delta = delta_ni, delta1 = delta_ni, delta0 = 0
)
power_ni <- sum(d_pwr_ni$upper$prob[, 2])
```

---

## Multi-Population (Subgroup) Designs

When testing across nested populations (e.g., CPS≥20 ⊂ CPS≥1 ⊂ All subjects), events differ by population based on prevalence:

```r
# 3-arm trial: 825 subjects, 1:1:1 randomization => 275/arm
# Each pairwise comparison (exp vs control): 275 + 275 = 550 subjects
total_N <- 825
n_per_comparison <- total_N * 2 / 3   # 550

# Events scale with prevalence
# CPS>=20 (50%): ~550 * 0.50 = 275 subjects in comparison
# CPS>=1  (80%): ~550 * 0.80 = 440 subjects in comparison
# All    (100%): ~550 subjects in comparison
```

Define expected events as a list:

```r
expected_events <- list(
  PFS_CPS20 = c(211, 237),       # IA1, IA2/FA
  PFS_CPS1  = c(337, 378),
  PFS_All   = c(423, 474),
  OS_CPS20  = c(171, 205, 222),  # IA1, IA2, FA
  OS_CPS1   = c(278, 332, 359),
  OS_All    = c(352, 421, 455)
)
```

Then compute boundaries for each hypothesis using `gsDesign()` with the appropriate events and alpha.

---

## NPH Evaluation with `lrstat`

When the user specifies non-proportional hazards, **do not design directly under NPH**. Instead, design under PH first (using constant hazards from Q6/Q7), then evaluate the PH design under NPH assumptions using `lrstat::lrpower()`.

### Step 1: Complete the PH design

Design using `gsSurv()` as usual with constant hazards. This gives events at each analysis, boundaries, enrollment, and timing.

```r
# Example: PH design gives these results
# OS events: IA=395, FA=478
# Z boundaries: efficacy = c(2.2271, 2.0485), futility = c(0.2470)
# Enrollment: 5/mo x 3 mo, then 20/mo x 41 mo = 44 mo total, N=835
```

### Step 2: Combine piecewise breakpoints

The control hazard and HR may have different breakpoints. Combine them into a unified set of intervals where both are constant:

```r
# User input:
#   Control hazard: 0.05 (0-12 mo), 0.03 (12+ mo)
#   HR: 0.8 (0-3 mo), 0.7 (3+ mo)
# Combined breakpoints: 0, 3, 12
pw_breaks  <- c(0, 3, 12)     # breakpoints
ctrl_haz   <- c(0.05, 0.05, 0.03)  # control hazard in each interval
hr_pw      <- c(0.80, 0.70, 0.70)  # HR in each interval
exp_haz    <- ctrl_haz * hr_pw      # experimental hazard: c(0.040, 0.035, 0.021)
```

### Step 3: Compute AHR and timing via `gsDesign2::expected_time()`

Use `expected_time()` to find the calendar time and average HR (AHR) at each PH event target under NPH. This targets the exact event count — do NOT use `lrsamplesize()` which computes its own events.

```r
library(gsDesign2)

# PH design outputs (fixed)
ph_events   <- c(395, 478)
ph_z_upper  <- c(2.2271, 2.0485)
ph_z_lower  <- c(0.2470)
accrual_dur <- 44
gamma       <- c(5, 20)
eta_os      <- -log(1 - 0.02) / 12

# NPH enrollment and failure rates
enroll_rate <- define_enroll_rate(duration = c(3, accrual_dur - 3), rate = gamma)
fail_rate   <- define_fail_rate(
  duration = c(3, Inf),
  fail_rate = ctrl_haz,        # e.g., c(0.05, 0.03)
  hr = hr_pw,                  # e.g., c(1.0, 0.7)
  dropout_rate = rep(eta_os, 2)
)

# AHR at each PH event target
nph_ia <- expected_time(enroll_rate = enroll_rate, fail_rate = fail_rate,
                        ratio = 1, target_event = ph_events[1])
nph_fa <- expected_time(enroll_rate = enroll_rate, fail_rate = fail_rate,
                        ratio = 1, target_event = ph_events[2])

cat(sprintf("At %d events (IA): time=%.1f mo, AHR=%.4f\n",
    ph_events[1], nph_ia$time, nph_ia$ahr))
cat(sprintf("At %d events (FA): time=%.1f mo, AHR=%.4f\n",
    ph_events[2], nph_fa$time, nph_fa$ahr))
```

### Step 4: Analytical power via `gs_power_npe()`

Use the AHR, info, and info0 from `expected_time()` with the PH boundaries. This is the primary power result.

```r
nph_power <- gs_power_npe(
  theta = -log(c(nph_ia$ahr, nph_fa$ahr)),
  info = c(nph_ia$info, nph_fa$info),
  info0 = c(nph_ia$info0, nph_fa$info0),
  upper = gs_b, upar = ph_z_upper,
  lower = gs_b, lpar = c(-Inf, -Inf)       # non-binding: no futility
)

# IMPORTANT: probability is CUMULATIVE per row — total power is the LAST upper row,
# NOT the sum (summing gives > 100%)
upper_probs <- nph_power$probability[nph_power$bound == "upper"]
ana_power_ia <- upper_probs[1]                  # cumulative at IA
ana_power_fa <- upper_probs[length(upper_probs)] # cumulative at FA = total power

cat(sprintf("NPH analytical power: IA=%.1f%%, Total=%.1f%%\n",
    ana_power_ia * 100, ana_power_fa * 100))
```

### Step 5: Verify analyticals via `lrsim()`

Simulation confirms the analytical timing AND power. Note: `lrsim` uses `piecewiseSurvivalTime` as breakpoints and separate `lambda1`/`lambda2` vectors (not `define_fail_rate()`).

```r
library(lrstat)

sim_nph_h1 <- lrsim(
  kMax = 2,
  criticalValues = ph_z_upper,
  futilityBounds = rep(-6, 1),           # non-binding: always disable
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, 3),
  accrualIntensity = gamma,
  accrualDuration = accrual_dur,
  piecewiseSurvivalTime = c(0, 3),         # breakpoints
  lambda1 = ctrl_haz * hr_pw,              # experimental hazards per interval
  lambda2 = ctrl_haz,                      # control hazards per interval
  gamma1 = eta_os, gamma2 = eta_os,
  plannedEvents = ph_events,
  maxNumberOfIterations = 10000, seed = 12345
)

cat(sprintf("NPH power: %.1f%%\n", sim_nph_h1$overview$overallReject * 100))
cat(sprintf("NPH timing: IA=%.1f mo, FA=%.1f mo\n",
    sim_nph_h1$overview$analysisTime[1], sim_nph_h1$overview$analysisTime[2]))
```

### Step 5: Verify NPH analyticals via `lrsim()`

The NPH evaluation is not complete until simulation confirms the analytical results. Run H1 and H0 simulations, then check against `expected_time()` outputs.

```r
# H1 simulation
sim_nph_h1 <- lrsim(
  kMax = 2,
  criticalValues = ph_z_upper,
  futilityBounds = rep(-6, 1),           # non-binding: omit futility for statistical power
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, 3), accrualIntensity = gamma,
  accrualDuration = accrual_dur,
  piecewiseSurvivalTime = c(0, 3),
  lambda1 = ctrl_haz * hr_pw,
  lambda2 = ctrl_haz,
  gamma1 = eta_os, gamma2 = eta_os,
  plannedEvents = ph_events,
  maxNumberOfIterations = 10000, seed = 12345
)

# H0 simulation (both arms = NPH control, futility disabled for non-binding)
sim_nph_h0 <- lrsim(
  kMax = 2,
  criticalValues = ph_z_upper,
  futilityBounds = rep(-6, 1),
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, 3), accrualIntensity = gamma,
  accrualDuration = accrual_dur,
  piecewiseSurvivalTime = c(0, 3),
  lambda1 = ctrl_haz,
  lambda2 = ctrl_haz,
  gamma1 = eta_os, gamma2 = eta_os,
  plannedEvents = ph_events,
  maxNumberOfIterations = 10000, seed = 67890
)

# --- Verification checks ---
# Analytical values from expected_time() (Step 3)
ana_ia_time <- nph_ia$time
ana_fa_time <- nph_fa$time
# Analytical power from gs_power_ahr() or computed from AHR (Step 3)

sim_ia_time <- sim_nph_h1$overview$analysisTime[1]
sim_fa_time <- sim_nph_h1$overview$analysisTime[2]
sim_power   <- sim_nph_h1$overview$overallReject
sim_alpha   <- sim_nph_h0$overview$overallReject

check <- function(name, analytical, simulated, tol) {
  pass <- abs(simulated - analytical) <= tol
  cat(sprintf("  %-15s analytical=%-8.2f simulated=%-8.2f diff=%-6.2f %s\n",
      name, analytical, simulated, simulated - analytical,
      ifelse(pass, "PASS", "FAIL")))
  pass
}

cat("NPH Verification:\n")
all_pass <- c(
  check("IA time (mo)", ana_ia_time, sim_ia_time, 1.0),
  check("FA time (mo)", ana_fa_time, sim_fa_time, 1.0),
  # For power, compare sim vs analytical power (replace ana_power with your value)
  # check("Power (%)", ana_power * 100, sim_power * 100, 2.0),
  TRUE  # placeholder
)
cat(sprintf("  Type I error: %.4f (target: %.3f) %s\n",
    sim_alpha, alpha_os,
    ifelse(abs(sim_alpha - alpha_os) <= 0.005, "PASS", "FAIL")))
cat(sprintf("  Overall: %s\n", ifelse(all(all_pass), "PASS", "FAIL")))
```

### Note on `gsDesign2::gs_design_ahr()`

`gs_design_ahr()` designs trials directly under NPH by sizing enrollment to achieve target power with piecewise failure rates. **Do NOT use this for NPH evaluation.** It changes the event counts and enrollment, which defeats the purpose of evaluating the PH design under NPH. Use it only if you need a standalone NPH-sized design (rare — the PH-first approach is preferred because it preserves the IA plan).

---

## Log-Rank Power with `lrstat`

### Power calculation

```r
library(lrstat)

power_result <- lrpower(
  kMax = 3,                          # Number of analyses
  informationRates = c(0.5, 0.75, 1),
  alpha = 0.025,
  typeAlphaSpending = "sfHSD",
  parameterAlphaSpending = -4,
  typeBetaSpending = "sfHSD",
  parameterBetaSpending = -2,
  allocationRatioPlanned = 1,
  accrualTime = c(0, 3, 6, 12),
  accrualIntensity = c(5, 10, 15, 15),
  piecewiseSurvivalTime = 0,
  lambda1 = log(2) / 16,            # Experimental hazard
  lambda2 = log(2) / 12,            # Control hazard
  gamma1 = 0.001, gamma2 = 0.001,   # Dropout hazards
  typeOfComputation = "direct"
)
```

### Sample size calculation

```r
ss_result <- lrsamplesize(
  beta = 0.1,                        # 90% power
  kMax = 3,
  informationRates = c(0.5, 0.75, 1),
  alpha = 0.025,
  typeAlphaSpending = "sfHSD",
  parameterAlphaSpending = -4,
  typeBetaSpending = "sfHSD",
  parameterBetaSpending = -2,
  allocationRatioPlanned = 1,
  accrualTime = c(0, 3, 6, 12),
  accrualIntensity = c(5, 10, 15),   # Rates (last extended)
  piecewiseSurvivalTime = 0,
  lambda1 = log(2) / 16,
  lambda2 = log(2) / 12,
  gamma1 = 0.001, gamma2 = 0.001,
  accrualDuration = NA,              # To be solved
  followupTime = NA                  # To be solved
)
```

---

## Event and Enrollment Prediction with `eventPred`

```r
library(eventPred)

# Enrollment prediction
set.seed(12345)
enroll_pred <- predictEnrollment(
  df = NULL,
  target_n = ceiling(x$N),
  enroll_fit = list(
    model = "piecewise poisson",
    theta = log(daily_rates),
    vtheta = diag(length(daily_rates)) * 1e-8,
    accrualTime = accrualTime
  ),
  ngroups = 2, alloc = c(1, 1),
  pilevel = 0.90, nreps = 500,
  showplot = FALSE, showsummary = TRUE
)

# Event prediction (2-arm)
event_pred <- predictEvent(
  df = NULL,
  target_d = ceiling(max(x$n.I)),  # Target events from gsSurv
  newSubjects = enroll_pred$newSubjects,
  event_fit = list(
    list(model = "exponential", theta = log(log(2) / (ctrl_median * 30.4375)),
         vtheta = matrix(1e-8)),
    list(model = "exponential", theta = log(log(2) / (exp_median * 30.4375)),
         vtheta = matrix(1e-8))
  ),
  dropout_fit = list(drop_fit, drop_fit),
  by_treatment = TRUE,
  pilevel = 0.90, nreps = 500,
  showplot = FALSE, showsummary = TRUE
)
```

eventPred uses **days** as its time unit. Convert: `daily_rate = monthly_rate / 30.4375`.

Important: `predictEvent()` does NOT accept `ngroups` or `alloc` — those belong only to `predictEnrollment()`. The treatment structure comes from `newSubjects` and the list-of-lists structure in `event_fit`.

---

## Multiplicity Strategy Diagram with `graphicalMCP`

Use `graphicalMCP::graph_create()` to create the graph object and `plot()` to render it. The plot uses base R graphics (via igraph), not ggplot2.

### Key `plot()` parameters

| Parameter | Default | Recommendation | Purpose |
|-----------|---------|----------------|---------|
| `vertex.size` | 20 | **40** | Circle radius — default is too small, labels overflow |
| `vertex.label` | auto | Custom (see below) | Override to avoid scientific notation (e.g., `6e-04`) |
| `vertex.label.cex` | 1 | **1.2** | Label font size inside circles |
| `edge.label.cex` | 1 | **1.1** | Edge weight label font size |
| `edge.arrow.size` | 1 | **1.2** | Arrow head size |
| `eps` | NULL | **0.001** | Renders 0.001 as ε and 0.999 as 1−ε |
| `layout` | "grid" | Custom matrix for 4+ hypotheses | Controls node positions |
| `nrow`, `ncol` | auto | Set for grid layout | Grid dimensions |

### Recommended `png()` dimensions

| Hypotheses | `width` | `height` | Notes |
|-----------|---------|----------|-------|
| 2 | 8 | 4 | Wide landscape — nodes side by side |
| 3 | 7 | 5 | Slight landscape |
| 4 | 10 | 8 | 2×2 grid with room for edge labels |
| 6+ | 12 | 9 | Large, allow room for edge labels |

### Avoiding scientific notation in vertex labels

By default, `plot()` uses `round(alpha, precision)` which can produce `6e-04` for small values. Override with custom `vertex.label`:

```r
v_labels <- paste0(hyp_names, "\n", format(alphas, scientific = FALSE))
plot(g, vertex.label = v_labels, ...)
```

### 2-hypothesis bidirectional (PFS + OS alpha split)

```r
library(graphicalMCP)

g <- graph_create(
  hypotheses = c(0.005, 0.020),
  transitions = matrix(c(0, 1,
                          1, 0), nrow = 2, byrow = TRUE),
  hyp_names = c("H1: PFS", "H2: OS")
)

png("multiplicity_diagram.png", width = 8, height = 4, units = "in", res = 300)
plot(g, vertex.size = 40, vertex.label.cex = 1.2,
     edge.label.cex = 1.1, edge.arrow.size = 1.2)
dev.off()
```

### 2-hypothesis fixed-sequence (DFS → OS)

```r
g <- graph_create(
  hypotheses = c(0.025, 0.000),
  transitions = matrix(c(0, 1,
                          0, 0), nrow = 2, byrow = TRUE),
  hyp_names = c("H1: DFS", "H2: OS")
)

png("multiplicity_diagram.png", width = 8, height = 4, units = "in", res = 300)
plot(g, vertex.size = 40, vertex.label.cex = 1.2,
     edge.label.cex = 1.1, edge.arrow.size = 1.2)
dev.off()
```

### 4-hypothesis alpha-split (PFS + OS × 2 populations)

```r
g <- graph_create(
  hypotheses = c(0.0079, 0.015, 0.0006, 0.0015),
  transitions = matrix(c(
    0,     1,     0,     0,
    0.001, 0,     0,     0.999,
    0,     0,     0,     1,
    0.001, 0.999, 0,     0
  ), nrow = 4, byrow = TRUE),
  hyp_names = c("H1: PFS-sub", "H2: OS-sub", "H3: PFS-ITT", "H4: OS-ITT")
)

# Layout: 2x2 grid — PFS top, OS bottom; subgroup left, ITT right
layout <- matrix(c(
  1, 2,  # H1 top-left
  1, 1,  # H2 bottom-left
  2, 2,  # H3 top-right
  2, 1   # H4 bottom-right
), nrow = 4, byrow = TRUE)

# Custom labels to avoid scientific notation
v_labels <- c("H1: PFS-sub\n0.0079", "H2: OS-sub\n0.015",
              "H3: PFS-ITT\n0.0006", "H4: OS-ITT\n0.0015")

png("multiplicity_diagram.png", width = 10, height = 8, units = "in", res = 300)
plot(g, layout = layout, eps = 0.001,
     vertex.size = 40, vertex.label = v_labels,
     vertex.label.cex = 1.2, edge.label.cex = 1.1,
     edge.arrow.size = 1.2)
dev.off()
```

### 4-hypothesis step-down (PFS + OS × 2 populations)

```r
g <- graph_create(
  hypotheses = c(0.01, 0.015, 0, 0),
  transitions = matrix(c(
    0,     0.999, 0,   0.001,
    0.001, 0,     0,   0.999,
    1,     0,     0,   0,
    0.5,   0,     0.5, 0
  ), nrow = 4, byrow = TRUE),
  hyp_names = c("H1: PFS-sub", "H2: OS-sub", "H3: PFS-ITT", "H4: OS-ITT")
)

layout <- matrix(c(
  1, 2,  # H1 top-left
  1, 1,  # H2 bottom-left
  2, 2,  # H3 top-right
  2, 1   # H4 bottom-right
), nrow = 4, byrow = TRUE)

v_labels <- c("H1: PFS-sub\n0.01", "H2: OS-sub\n0.015",
              "H3: PFS-ITT\n0", "H4: OS-ITT\n0")

png("multiplicity_diagram.png", width = 10, height = 8, units = "in", res = 300)
plot(g, layout = layout, eps = 0.001,
     vertex.size = 40, vertex.label = v_labels,
     vertex.label.cex = 1.2, edge.label.cex = 1.1,
     edge.arrow.size = 1.2)
dev.off()
```

Note: In this step-down example, all transition weights were confirmed with the user. Key decisions:
- H1→H2 (0.999) with epsilon 0.001 to H4: user chose OS-ITT over PFS-ITT for the epsilon
- H2→H4 (0.999) with epsilon 0.001 to H1: keeps graph connected to subgroup
- H3→H1 (1.0): forced — H2 and H4 already rejected (gates for H3), H1 is the only possible recipient
- H4→H1/H3 (0.5/0.5): user chose equal split between both PFS hypotheses

Include the diagram in the Word report via `body_add_img(mult_plot_path, width = 5, height = 4)` (adjust height proportionally based on the width/height ratio used in `png()`).

---

## Boundary Plot (HR Scale)

```r
library(ggplot2)

tab <- gsBoundSummary(x, deltaname = "HR", logdelta = TRUE, Nname = "Events")
tab_df <- as.data.frame(tab)
hr_rows <- which(grepl("HR at bound", tab_df$Value))
hr_efficacy <- as.numeric(as.character(tab_df$Efficacy[hr_rows]))
hr_futility <- as.numeric(as.character(tab_df$Futility[hr_rows]))

info_frac <- x$timing
plot_df <- data.frame(
  IF = rep(info_frac, 2),
  HR = c(hr_efficacy, hr_futility),
  Boundary = rep(c("Efficacy", "Futility"), each = length(info_frac))
)

p <- ggplot(plot_df, aes(x = IF, y = HR, color = Boundary)) +
  geom_line(linewidth = 1.2) +
  geom_point(size = 3) +
  geom_hline(yintercept = 1, linetype = "dashed", color = "grey50") +
  scale_color_manual(values = c("Efficacy" = "darkgreen", "Futility" = "darkred")) +
  labs(x = "Information Fraction",
       y = "Hazard Ratio at Boundary",
       title = "Group Sequential Boundaries (HR Scale)") +
  theme_minimal()

ggsave("boundary_plot.png", p, width = 8, height = 5, dpi = 300)
```

---

## Spending Function Plot

```r
info_seq <- seq(0.01, 1, by = 0.01)
eff_spend <- sfLDOF(alpha, info_seq, 0)$spend      # or sfHSD(alpha, info_seq, gamma)$spend
fut_spend <- sfHSD(beta, info_seq, sflpar)$spend

spend_df <- data.frame(
  IF = rep(info_seq, 2),
  Spend = c(eff_spend, fut_spend),
  Type = rep(c("Efficacy", "Futility"), each = length(info_seq))
)
ggplot(spend_df, aes(x = IF, y = Spend, color = Type)) +
  geom_line(linewidth = 1) +
  labs(x = "Information Fraction", y = "Cumulative Spending") +
  theme_minimal()
```

---

## Saving Design Results to JSON (R)

At the end of the R design script, save all results to JSON for the Python report generator. Include assumptions, analysis plan, boundaries, crossing probabilities, information fractions, and sample sizes at each analysis.

```r
library(jsonlite)

results <- list(
  # Assumptions
  disease = "1L metastatic NSCLC",
  endpoints = "Co-primary PFS + OS",
  randomization = "1:1",
  ctrl_median_pfs = ctrl_median_pfs,
  ctrl_median_os = ctrl_median_os,
  hr_pfs = hr_pfs, hr_os = hr_os,
  dropout_annual = dropout_annual,
  enrollment = "5/mo x 3 mo, then 20/mo",
  alpha_pfs = alpha_pfs, alpha_os = alpha_os,
  spending = "Lan-DeMets O'Brien-Fleming (both)",
  futility = "Non-binding, OS only",

  # Sample size
  total_N = total_N_final,
  enroll_duration = sum(x_os$R),
  study_duration = x_os$T[3],
  min_followup_os = x_os$T[3] - sum(x_os$R),

  # Analysis plan
  ia1_time = ia1_time, ia2_time = x_os$T[2], fa_time = x_os$T[3],
  pfs_events_ia1 = pfs_events[1], pfs_events_ia2 = pfs_events[2],
  os_events_ia1 = os_events[1], os_events_ia2 = os_events[2], os_events_fa = os_events[3],

  # PFS boundaries + crossing probs
  pfs_z_upper = d_pfs$upper$bound,
  pfs_p_upper = pnorm(-d_pfs$upper$bound),
  pfs_hr_upper = as.numeric(hr_bound_pfs),
  pfs_info_frac = pfs_events / pfs_events[2],
  pfs_N = pfs_sample_sizes,  # N enrolled at each PFS analysis
  pfs_cum_cross_h1 = cumsum(d_pfs_power$upper$prob[, 2]),
  pfs_cum_cross_h0 = sfLDOF(alpha_pfs, d_pfs$timing)$spend,  # from spending function
  pfs_power = pfs_power, pfs_power_full = pfs_power_full,

  # OS boundaries + crossing probs
  os_z_upper = x_os$upper$bound, os_z_lower = x_os$lower$bound,
  os_p_upper = pnorm(-x_os$upper$bound),
  os_hr_upper = as.numeric(hr_eff_os), os_hr_lower = as.numeric(hr_fut_os),
  os_info_frac = os_events / os_events[3],
  os_N = os_sample_sizes,  # N enrolled at each OS analysis
  os_cum_cross_h1 = cumsum(x_os$upper$prob[, 2]),
  os_cum_cross_h0 = sfLDOF(alpha_os, x_os$timing)$spend,  # from spending function
  os_power = 0.90, os_power_full = os_power_full
)

write_json(results, file.path(out_dir, "gsd_results.json"), pretty = TRUE, auto_unbox = TRUE)
```

**Key points**:
- Cumulative alpha (H0) uses `sfLDOF(alpha, timing)$spend` — the spending function directly — NOT `cumsum(d$upper$prob[, 1])`, which accounts for futility stopping and will be less than nominal alpha for non-binding designs.
- Cumulative power (H1) uses `cumsum(d$upper$prob[, 2])`.
- Adapt field names for your specific design (single endpoint, co-primary, etc.).

---

## Generating Word Report with Python

Use `python-docx` for full control over formatting. Read the JSON saved by R and the multiplicity diagram PNG.

```python
# gsd_report.py — run as: python gsd_report.py <path_to_gsd_results.json>
import json, sys, os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True; run.font.size = Pt(9); run.font.name = "Calibri"
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Light blue header
        shd = cell._element.get_or_add_tcPr().makeelement(
            qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "D6E4F0"})
        cell._element.get_or_add_tcPr().append(shd)
    for i, row_data in enumerate(rows):
        for j, val in enumerate(row_data):
            cell = table.rows[i+1].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(9); run.font.name = "Calibri"
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

def add_heading(doc, number, title):
    h = doc.add_heading(level=1)
    run = h.add_run(f"{number}. {title}")
    run.font.size = Pt(14); run.font.name = "Calibri"
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

def add_subheading(doc, title):
    h = doc.add_heading(level=2)
    run = h.add_run(title)
    run.font.size = Pt(12); run.font.name = "Calibri"
    run.font.color.rgb = RGBColor(0x2E, 0x4A, 0x6E)

def add_body(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(10); run.font.name = "Calibri"
```

Then build sections in order: 1. Design Assumptions, 2. IA/FA Plan, 3. Multiplicity Strategy (with diagram), 4. Efficacy and Futility Boundaries (subsection per endpoint), 5. Sample Size and Power Summary. See `reference.md` → "Report Sections" for the full format spec.

---

## Analytical Expected Events Calculator

`nSurv()` crashes when `T < sum(R)` (calendar time during enrollment). Use this analytical function instead, which works at any calendar time by integrating event probability over the enrollment schedule.

```r
# Compute expected events at calendar time T_cal
# Works at ANY calendar time, including during enrollment
#
# Key formula: For a patient with follow-up time f, the probability of observing
# an event (not censored by dropout) is:
#   P(event by f) = lambda/(lambda+eta) * (1 - exp(-(lambda+eta)*f))
#
# The lambda/(lambda+eta) factor is the COMPETING RISK ADJUSTMENT for dropout.
# Without it, dropouts are counted as events, overestimating the event rate
# and underestimating the time to reach a target number of events.
calc_expected_events <- function(T_cal, lambdaC, hr, eta, gamma_vec, R_vec, ratio_val) {
  lambda_exp <- lambdaC * hr
  enroll_starts <- c(0, cumsum(R_vec[-length(R_vec)]))
  enroll_ends   <- cumsum(R_vec)

  total_events <- 0
  for (i in seq_along(gamma_vec)) {
    s_start <- enroll_starts[i]
    s_end   <- min(enroll_ends[i], T_cal)
    if (s_start >= T_cal) next

    rate <- gamma_vec[i]
    dur <- s_end - s_start
    fup_end   <- T_cal - s_end
    fup_start <- T_cal - s_start

    # Control arm: competing risk adjustment lambda/(lambda+eta)
    haz_ctrl <- lambdaC + eta
    cr_ctrl  <- lambdaC / haz_ctrl
    int_ctrl <- dur - (exp(-haz_ctrl * fup_end) - exp(-haz_ctrl * fup_start)) / haz_ctrl
    events_ctrl <- rate * (1 / (1 + ratio_val)) * cr_ctrl * int_ctrl

    # Experimental arm: competing risk adjustment
    haz_exp <- lambda_exp + eta
    cr_exp  <- lambda_exp / haz_exp
    int_exp <- dur - (exp(-haz_exp * fup_end) - exp(-haz_exp * fup_start)) / haz_exp
    events_exp <- rate * (ratio_val / (1 + ratio_val)) * cr_exp * int_exp

    total_events <- total_events + events_ctrl + events_exp
  }
  total_events
}

# Find calendar time when target_events have occurred (binary search)
find_event_time <- function(target_events, lambdaC, hr, eta, gamma_vec, R_vec, ratio_val) {
  lo <- 1; hi <- sum(R_vec) + 120
  for (i in 1:100) {
    mid <- (lo + hi) / 2
    d <- calc_expected_events(mid, lambdaC, hr, eta, gamma_vec, R_vec, ratio_val)
    if (d < target_events) lo <- mid else hi <- mid
    if (abs(hi - lo) < 0.01) break
  }
  mid
}
```

**When to use**: Any time you need to compute expected events at a calendar time that might be during enrollment (e.g., finding when a fast endpoint like PFS triggers an IA while enrollment is still ongoing). Also useful for computing a non-triggering endpoint's events at a specific calendar time.

**Verified**: With the competing risk adjustment, timing estimates match `lrsim()` simulation within 0.5 months across all analyses (verified on a co-primary PFS+OS design with 10,000 simulations).

---

## Single-Look (k=1) Boundary Computation

`gsDesign(k=1)` and `gsSurv(k=1)` both fail — use this helper for any endpoint with a single analysis.

```r
# Boundary computation for a single-look (k=1) endpoint
# gsDesign(k=1) FAILS with "input timing must be increasing strictly between 0 and 1"
# Use this function instead.
compute_single_look_boundary <- function(events, alpha, hr, hr0 = 1.0) {
  z <- qnorm(1 - alpha)
  hr_bound <- hr0 * exp(-z * 2 / sqrt(events))
  delta <- log(hr0 / hr) / 2
  power <- pnorm(delta * sqrt(events) - z)
  list(z = z, p = alpha, hr = hr_bound, power = power, events = events)
}

# Example usage:
b <- compute_single_look_boundary(events = 540, alpha = 0.002, hr = 0.69)
cat(sprintf("Z=%.3f, p=%.4f, HR boundary=%.3f, power=%.1f%%\n",
    b$z, b$p, b$hr, b$power * 100))
```

**When to use**: Any endpoint tested at exactly one analysis (e.g., PFS tested only at the IA in a co-primary design). Also useful for computing power at full alpha (alpha=0.025) for reference.

---

## Minimum IF to Clear Enrollment

Computes the minimum information fraction at an IA such that the IA occurs after enrollment completes. Uses `calc_expected_events()` to find how many events have accrued by the end of enrollment, then divides by the total events at the analysis where the IF is defined.

```r
# Returns the minimum IF (as a proportion) for the triggering endpoint
# such that the IA occurs no earlier than enrollment completion.
#
# Arguments:
#   lambdaC     - control arm hazard for the triggering endpoint
#   hr          - hazard ratio for the triggering endpoint
#   eta         - monthly dropout hazard for the triggering endpoint
#   gamma_vec   - enrollment rates per period
#   R_vec       - enrollment period durations (from gsSurv output)
#   ratio_val   - randomization ratio
#   total_events_at_ref - total events for the triggering endpoint at the
#                         reference analysis (e.g., PFS events at IA2, or
#                         OS events at FA). The IF is relative to this number.
#
# Returns: minimum IF (proportion). If events at enrollment end >= total_events_at_ref,
#          returns 1.0 (IA cannot be pushed past enrollment — all events occur before
#          enrollment ends).

min_if_past_enrollment <- function(lambdaC, hr, eta, gamma_vec, R_vec, ratio_val,
                                    total_events_at_ref) {
  enroll_dur <- sum(R_vec)
  events_at_enroll_end <- calc_expected_events(
    T_cal = enroll_dur, lambdaC = lambdaC, hr = hr, eta = eta,
    gamma_vec = gamma_vec, R_vec = R_vec, ratio_val = ratio_val
  )
  min_if <- ceiling(events_at_enroll_end) / total_events_at_ref
  min(min_if, 1.0)
}
```

**Example usage** (co-primary PFS+OS, IA1 triggered by PFS):
```r
# After computing the design, check whether IA1 occurs during enrollment
min_pfs_if <- min_if_past_enrollment(
  lambdaC = log(2) / ctrl_median_pfs,
  hr = hr_pfs,
  eta = eta_pfs,
  gamma_vec = x_os$gamma,
  R_vec = x_os$R,
  ratio_val = ratio,
  total_events_at_ref = pfs_events_ia2_final  # PFS events at IA2
)
cat("Minimum PFS IF at IA1 to clear enrollment:", round(min_pfs_if * 100), "%\n")
# If the user's chosen IF (e.g., 80%) < min_pfs_if, warn them
```

**When to use**: During the "IA Timing vs Enrollment Check" step. Automatically compute and report this value whenever an IA occurs before enrollment ends, so the user knows exactly what IF would fix the issue.

---

## Co-Primary Shared-Timing Iterative Workflow

Complete code for designing co-primary PFS + OS where different endpoints trigger different analyses (e.g., IA1→PFS, IA2→OS, FA→OS). See `reference.md` → "Co-Primary Shared-Timing: Iterative Design Workflow" for the algorithm.

```r
library(gsDesign)

# --- Assumptions (fill in from user inputs) ---
ctrl_median_pfs <- 8; ctrl_median_os <- 20
hr_pfs <- 0.69; hr_os <- 0.74
eta <- -log(1 - 0.05) / 12
gamma <- c(5, 20); R <- c(3, Inf)  # Inf = gsSurv determines duration
alpha_pfs <- 0.005; alpha_os <- 0.02
ratio <- 1

# Define calc_expected_events() and find_event_time() here (see above)

# --- Step 1: Design OS (2-look: IA2 + FA) ---
x_os_2look <- gsSurv(
  k = 2, test.type = 4, alpha = alpha_os, beta = 0.10,
  timing = 0.80, sfu = sfLDOF, sfl = sfHSD, sflpar = -2,
  lambdaC = log(2) / ctrl_median_os, hr = hr_os, hr0 = 1, eta = eta,
  gamma = gamma, R = c(3, 100), T = NULL, minfup = 12, ratio = ratio
)

# --- Step 2: PFS events at IA2 calendar time ---
pfs_events_ia2 <- ceiling(calc_expected_events(
  T_cal = x_os_2look$T[1],  # IA2 timing from 2-look OS
  lambdaC = log(2) / ctrl_median_pfs, hr = hr_pfs, eta = eta,
  gamma_vec = x_os_2look$gamma, R_vec = x_os_2look$R, ratio_val = ratio
))

# --- Step 3: IA1 calendar time (PFS-triggered) ---
pfs_events_ia1 <- ceiling(0.80 * pfs_events_ia2)  # 80% IF for PFS at IA1
ia1_time <- find_event_time(
  target_events = pfs_events_ia1,
  lambdaC = log(2) / ctrl_median_pfs, hr = hr_pfs, eta = eta,
  gamma_vec = x_os_2look$gamma, R_vec = x_os_2look$R, ratio_val = ratio
)

# --- Step 4: OS events at IA1 ---
os_events_ia1 <- ceiling(calc_expected_events(
  T_cal = ia1_time,
  lambdaC = log(2) / ctrl_median_os, hr = hr_os, eta = eta,
  gamma_vec = x_os_2look$gamma, R_vec = x_os_2look$R, ratio_val = ratio
))
os_events_total <- ceiling(max(x_os_2look$n.I))
os_if_ia1 <- os_events_ia1 / os_events_total

# --- Step 5: Re-design OS with 3 looks ---
x_os <- gsSurv(
  k = 3, test.type = 4, alpha = alpha_os, beta = 0.10,
  timing = c(os_if_ia1, 0.80), sfu = sfLDOF, sfl = sfHSD, sflpar = -2,
  lambdaC = log(2) / ctrl_median_os, hr = hr_os, hr0 = 1, eta = eta,
  gamma = gamma, R = c(3, 100), T = NULL, minfup = 12, ratio = ratio
)

# --- Step 6: Recompute PFS events from final OS timeline ---
pfs_events_ia2_final <- ceiling(calc_expected_events(
  T_cal = x_os$T[2],  # IA2 timing from 3-look OS
  lambdaC = log(2) / ctrl_median_pfs, hr = hr_pfs, eta = eta,
  gamma_vec = x_os$gamma, R_vec = x_os$R, ratio_val = ratio
))
pfs_events_ia1_final <- ceiling(0.80 * pfs_events_ia2_final)
pfs_events <- c(pfs_events_ia1_final, pfs_events_ia2_final)

# --- Step 7: Design PFS boundaries ---
d_pfs <- gsDesign(
  k = 2, test.type = 1, alpha = alpha_pfs, sfu = sfLDOF,
  n.I = pfs_events, maxn.IPlan = pfs_events[2]
)

# PFS HR at boundary
hr_bound_pfs <- exp(-d_pfs$upper$bound * 2 / sqrt(pfs_events))

# PFS power (derived, not a free parameter)
delta_pfs <- log(1 / hr_pfs) / 2
d_pfs_power <- gsDesign(
  k = 2, test.type = 1, alpha = alpha_pfs, sfu = sfLDOF,
  n.I = pfs_events, maxn.IPlan = pfs_events[2],
  delta = delta_pfs, delta1 = delta_pfs, delta0 = 0
)
pfs_power <- sum(d_pfs_power$upper$prob[, 2])
```

**Key points**:
- Design OS first (Step 1) because OS power drives the study size
- Use `calc_expected_events()` (NOT `nSurv()`) for Steps 2, 3, 4, 6 — nSurv crashes at arbitrary T
- Use `gsDesign()` (NOT `gsSurv()`) for PFS (Step 7) because PFS events are already known
- PFS power is derived from the OS-driven timeline, not a user input
- The 2-look → 3-look OS re-design (Steps 1→5) is needed because OS IF at IA1 depends on the PFS-driven IA1 timing

---

## Common Design Patterns (Quick Reference)

### Pattern 1: Single Primary OS, 1 IA + FA, OBF-like efficacy
```r
x <- gsSurv(
  k = 2, test.type = 4,
  alpha = 0.025, beta = 0.1,
  timing = 0.6,
  sfu = sfLDOF,
  sfl = sfHSD, sflpar = -2,
  lambdaC = log(2)/12, hr = 0.75, eta = 0.001,
  gamma = c(5, 10, 15), R = c(3, 3, 18),
  T = NULL, minfup = NULL, ratio = 1
)
```

### Pattern 2: Co-primary PFS + OS, alpha splitting (KN426 style)
Design each endpoint separately at its allocated alpha using `gsSurv()`. Document the Maurer-Bretz reallocation graph. See "Co-Primary Endpoints: Alpha Splitting" section above.

### Pattern 3: Fixed-sequence DFS → OS (KN564 style)
Design DFS at full alpha. Design OS at full alpha (conditional on DFS success). See "Co-Primary Endpoints: Fixed-Sequence Testing" section above.

### Pattern 4: Non-proportional hazards (IO trial with delayed effect)
Use `gsDesign2::gs_design_ahr()` with piecewise failure rates. See "Non-Proportional Hazards" section above.

### Pattern 5: Multi-population, multi-endpoint, multi-arm (KN048 style)
Use `gsDesign()` with pre-specified events, `test.type = 1`, and `delta = log(HR0/HR) / 2` for power. See "Complex Graphical Multiplicity" and "Non-Inferiority Testing" sections above. Reference: `references/kn048-text.txt`.

### Pattern 6: Co-primary PFS + OS, shared-timing with cross-endpoint triggers
When different endpoints trigger different analyses (e.g., IA1→PFS, IA2→OS, FA→OS), use the iterative workflow: design OS first with `gsSurv()`, compute cross-endpoint events with `calc_expected_events()`, re-design OS with derived IFs, design PFS with `gsDesign()` using known events. See "Co-Primary Shared-Timing Iterative Workflow" section above.

### Pattern 7: Co-primary with single-look endpoint (e.g., PFS at IA only, OS at IA+FA)
When one endpoint is tested at only one analysis (k=1). `gsDesign(k=1)` fails — compute boundaries manually via `compute_single_look_boundary()`. Design the multi-look endpoint (OS) with `gsSurv(k=2)`, use `nSurv()` for the k=1 baseline if needed, derive the single-look endpoint's events from the shared timeline via `calc_expected_events()`. See "Co-Primary with Single-Look Endpoint" section below.

---

## Co-Primary with Single-Look Endpoint (Pattern 7)

When one endpoint is tested at only one analysis (e.g., PFS at IA only) and the other has a standard GSD (e.g., OS at IA + FA). The single-look endpoint is a fixed-sample design — `gsDesign(k=1)` will fail, so boundaries must be computed manually.

```r
library(gsDesign)

# --- Assumptions ---
ctrl_median_pfs <- 8; ctrl_median_os <- 20
hr_pfs <- 0.69; hr_os <- 0.74
eta_pfs <- -log(1 - 0.05) / 12
eta_os  <- -log(1 - 0.02) / 12
alpha_pfs <- 0.002; alpha_os <- 0.023
gamma <- c(5, 20); R_init <- c(3, 100); ratio <- 1

# Define calc_expected_events(), find_event_time(), compute_single_look_boundary() here

# --- Step 1: OS baseline via nSurv() ---
# nSurv() works for k=1 (unlike gsSurv which fails)
n_os_base <- nSurv(
  lambdaC = log(2) / ctrl_median_os, hr = hr_os, hr0 = 1, eta = eta_os,
  gamma = gamma, R = R_init, T = NULL, minfup = 12, ratio = ratio,
  alpha = alpha_os, beta = 0.10, sided = 1
)

# --- Step 2: IA timing (PFS-triggered, at enrollment end + data prep buffer) ---
data_prep_months <- 3
enroll_dur <- sum(n_os_base$R)
ia_target_time <- enroll_dur + data_prep_months

pfs_events_ia <- ceiling(calc_expected_events(
  T_cal = ia_target_time, lambdaC = log(2) / ctrl_median_pfs, hr = hr_pfs,
  eta = eta_pfs, gamma_vec = n_os_base$gamma, R_vec = n_os_base$R, ratio_val = ratio
))

# --- Step 3: OS events at IA → derive OS IF ---
os_events_ia <- ceiling(calc_expected_events(
  T_cal = ia_target_time, lambdaC = log(2) / ctrl_median_os, hr = hr_os,
  eta = eta_os, gamma_vec = n_os_base$gamma, R_vec = n_os_base$R, ratio_val = ratio
))
os_if_ia <- os_events_ia / ceiling(n_os_base$n)

# --- Step 4: Design OS with 2 looks (IA + FA) ---
x_os <- gsSurv(
  k = 2, test.type = 4, alpha = alpha_os, beta = 0.10,
  timing = os_if_ia, sfu = sfLDOF, sfl = sfHSD, sflpar = -20,
  lambdaC = log(2) / ctrl_median_os, hr = hr_os, hr0 = 1, eta = eta_os,
  gamma = gamma, R = R_init, T = NULL, minfup = 12, ratio = ratio
)

# --- Step 5: PFS boundary (single look, manual computation) ---
# Recompute PFS events from final OS timeline
enroll_dur_final <- sum(x_os$R)
pfs_events_final <- ceiling(calc_expected_events(
  T_cal = enroll_dur_final + data_prep_months,
  lambdaC = log(2) / ctrl_median_pfs, hr = hr_pfs, eta = eta_pfs,
  gamma_vec = x_os$gamma, R_vec = x_os$R, ratio_val = ratio
))

# gsDesign(k=1) FAILS -- use manual computation
b_pfs <- compute_single_look_boundary(pfs_events_final, alpha_pfs, hr_pfs)
cat(sprintf("PFS: %d events, Z=%.3f, HR boundary=%.3f, power=%.1f%%\n",
    b_pfs$events, b_pfs$z, b_pfs$hr, b_pfs$power * 100))
```

**Key differences from Pattern 6:**
- PFS has k=1 (single look) — no `gsDesign()` or `gsSurv()` call for PFS boundaries
- Use `compute_single_look_boundary()` instead of `gsDesign()`
- Use `nSurv()` (not `gsSurv(k=1)`) for the fixed-sample baseline
- No `gsBoundSummary()` call for PFS — format the single-row boundary table manually
- PFS power is derived from the OS-driven study size and timeline
- Includes data preparation buffer in IA timing

---

## Verification with `lrsim()`

Use `lrstat::lrsim()` to simulate the trial and verify the calculated design. Run two simulations: one under H1 (alternative) and one under H0 (null).

### Simulation under H1 (verify power, events, timing)

```r
library(lrstat)

# Use design parameters and calculated boundaries
# IMPORTANT: accrualDuration is REQUIRED — lrsim will error without it
sim_h1 <- lrsim(
  kMax = k,                              # Number of analyses
  criticalValues = z_upper,              # Efficacy Z-boundaries from gsSurv
  futilityBounds = rep(-6, k - 1),      # Non-binding: disable futility for statistical power
  allocation1 = 1, allocation2 = 1,     # Randomization ratio
  accrualTime = c(0, cumsum(R[-length(R)])),  # Enrollment period start times
  accrualIntensity = gamma,             # Enrollment rates per period
  accrualDuration = sum(R),             # REQUIRED: total enrollment duration
  piecewiseSurvivalTime = 0,
  lambda1 = log(2) / median_exp,        # Experimental hazard
  lambda2 = log(2) / median_ctrl,       # Control hazard
  gamma1 = eta, gamma2 = eta,           # Dropout hazards
  plannedEvents = ceiling(n.I),         # Target events at each analysis
  maxNumberOfIterations = 10000,
  seed = 12345
)
```

### Simulation under H0 (verify type I error)

```r
# Same setup but both arms have control hazard (HR = 1)
# IMPORTANT: For non-binding futility (test.type=4), REMOVE futility bounds
# in the H0 simulation. gsDesign computes alpha as if futility doesn't exist,
# so the simulation must match. Use rep(-6, k-1) to effectively disable futility.
sim_h0 <- lrsim(
  kMax = k,
  criticalValues = z_upper,
  futilityBounds = rep(-6, k - 1),     # No futility for non-binding H0 check
  allocation1 = 1, allocation2 = 1,
  accrualTime = c(0, cumsum(R[-length(R)])),
  accrualIntensity = gamma,
  accrualDuration = sum(R),             # REQUIRED
  piecewiseSurvivalTime = 0,
  lambda1 = log(2) / median_ctrl,       # SAME as control (HR=1)
  lambda2 = log(2) / median_ctrl,
  gamma1 = eta, gamma2 = eta,
  plannedEvents = ceiling(n.I),
  maxNumberOfIterations = 10000,
  seed = 67890
)
```

### Extracting results

```r
# lrsim() returns an S3 object with two components:
#   $overview  — list of aggregated metrics (mean events, timing, rejection rates)
#   $sumdata   — data frame with per-iteration results
# Do NOT index it like a flat data frame.

# Overall rejection rate (power or type I error)
rejection_rate <- sim_h1$overview$overallReject

# Mean events at each analysis (vector, one per analysis)
mean_events <- sim_h1$overview$numberOfEvents

# Mean calendar time at each analysis (vector, one per analysis)
mean_time <- sim_h1$overview$analysisTime

# Rejection rate per stage (vector)
reject_per_stage <- sim_h1$overview$rejectPerStage

# Per-iteration data (data frame with columns: iterationNumber, stageNumber,
#   analysisTime, totalEvents, logRankStatistic, rejectPerStage, futilityPerStage, etc.)
# Useful for custom summaries:
median_events <- tapply(sim_h1$sumdata$totalEvents, sim_h1$sumdata$stageNumber, median)
median_time <- tapply(sim_h1$sumdata$analysisTime, sim_h1$sumdata$stageNumber, median)
```

**Non-binding futility (test.type=4) verification rule**: `gsDesign` computes both alpha AND power ignoring futility. ALL `lrsim()` calls must match — use `futilityBounds = rep(-6, k-1)` in BOTH H0 and H1 simulations. Including futility bounds gives "operational power" which does NOT match the analytical power.

### Verification pass/fail checks and log generation

```r
# Helper: check one metric
check <- function(name, calc, sim, tol) {
  diff <- abs(sim - calc)
  pass <- diff <= tol
  cat(sprintf("%-30s Calc=%-10.2f Sim=%-10.2f Diff=%-8.2f Tol=%-8.2f %s\n",
              name, calc, sim, diff, tol, ifelse(pass, "PASS", "FAIL")))
  pass
}

results <- c()
# Power
results <- c(results, check("Power (%)", 90.0, sim_h1$overview$overallReject * 100, 2.0))
# Type I error
results <- c(results, check("Type I Error (%)", alpha * 100, sim_h0$overview$overallReject * 100, 0.5))
# Events at each analysis (±5%)
for (i in seq_along(planned_events)) {
  results <- c(results, check(
    sprintf("Events at analysis %d", i),
    planned_events[i], sim_h1$overview$numberOfEvents[i], planned_events[i] * 0.05))
}
# Timing at each analysis (±1 month)
for (i in seq_along(calc_times)) {
  results <- c(results, check(
    sprintf("Timing analysis %d (mo)", i),
    calc_times[i], sim_h1$overview$analysisTime[i], 1.0))
}

cat(sprintf("\nOverall: %s (%d/%d passed)\n",
            ifelse(all(results), "PASS", "FAIL"), sum(results), length(results)))

# Write verification log to output subfolder
log_lines <- c(
  "# GSD Verification Log",
  sprintf("**Design**: %s", endpoint_name),
  sprintf("**Date**: %s", Sys.Date()),
  sprintf("**Simulations**: %d reps", nreps),
  "",
  "| Metric | Calculated | Simulated | Criterion | Pass? |",
  "|--------|-----------|-----------|-----------|-------|"
)
# Append rows for each check...
writeLines(log_lines, file.path(out_dir, "gsd_verification_log.md"))
```
