#!/usr/bin/env bash
# setup_r_env.sh — Idempotent R environment bootstrap for benchmark-runner.
# Run once per session before Step 1 of SKILL.md.
# Exits non-zero on any failure so the caller can stop early.
set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Install R base if not present
# ---------------------------------------------------------------------------
if ! command -v R &>/dev/null; then
  echo "[setup] R not found — installing r-base..."
  sudo apt-get update -qq
  sudo apt-get install -y r-base
fi

R_VERSION=$(R --version | head -1 | awk '{print $3}')
echo "[setup] R ${R_VERSION} available."

# ---------------------------------------------------------------------------
# 2. Install required R packages via Posit Public Package Manager
#    (pre-compiled Linux binaries — much faster than building from source)
# ---------------------------------------------------------------------------
Rscript - <<'REOF'
options(
  repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/jammy/latest"),
  warn  = 1   # print warnings immediately
)

# Packages needed by benchmark-runner automation scripts
automation_pkgs <- c(
  "jsonlite",   # JSON parse/emit in R-based dispatcher helpers
  "digest"      # SHA hashing used by deduplication logic
)

# Packages needed by the group-sequential-design skill
# (pre-installing avoids mid-benchmark install delays that skew timing)
skill_pkgs <- c(
  "gsDesign",     # group sequential boundaries and sample size
  "gsDesign2",    # non-proportional hazards evaluation
  "lrstat",       # log-rank simulation for design verification
  "graphicalMCP", # Maurer-Bretz graphical multiplicity testing
  "eventPred",    # event prediction under non-proportional hazards
  "ggplot2"       # visualisation used in examples and outputs
)

all_pkgs  <- unique(c(automation_pkgs, skill_pkgs))
installed <- installed.packages()[, "Package"]
missing   <- all_pkgs[!all_pkgs %in% installed]

if (length(missing) > 0) {
  message("[setup] Installing missing packages: ", paste(missing, collapse = ", "))
  install.packages(missing, quiet = FALSE)
}

# Verify every package can actually be loaded
failed <- character(0)
for (pkg in all_pkgs) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    failed <- c(failed, pkg)
  }
}

if (length(failed) > 0) {
  stop("[setup] FAILED to load: ", paste(failed, collapse = ", "))
}

message("[setup] All ", length(all_pkgs), " R packages verified.")
REOF

echo "[setup] R environment ready."
