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

# Detect OS codename for the correct PPM binary URL (e.g. noble, jammy, focal)
OS_CODENAME=$(. /etc/os-release 2>/dev/null && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" || true)
if [ -z "${OS_CODENAME}" ] && command -v lsb_release &>/dev/null; then
  OS_CODENAME=$(lsb_release -cs 2>/dev/null || true)
fi

if [ -n "${OS_CODENAME}" ]; then
  PPM_URL="https://packagemanager.posit.co/cran/__linux__/${OS_CODENAME}/latest"
  echo "[setup] Detected OS codename '${OS_CODENAME}' — using PPM URL: ${PPM_URL}"
else
  PPM_URL="https://cloud.r-project.org"
  echo "[setup] Could not detect OS codename — falling back to CRAN: ${PPM_URL}"
fi

Rscript --no-save - "${PPM_URL}" <<'REOF'
ppm_url <- commandArgs(trailingOnly = TRUE)[1]

# Verify the PPM URL is reachable and has packages; fall back to CRAN if not
ppm_ok <- tryCatch({
  av <- available.packages(repos = ppm_url)
  nrow(av) > 100
}, error = function(e) FALSE)

repo_url <- if (ppm_ok) ppm_url else {
  message("[setup] PPM URL unreachable — falling back to CRAN")
  "https://cloud.r-project.org"
}

options(
  repos = c(CRAN = repo_url),
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
  install.packages(missing, quiet = FALSE, dependencies = TRUE)
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
