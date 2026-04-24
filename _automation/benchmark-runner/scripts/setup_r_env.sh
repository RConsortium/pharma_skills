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
# 2. Pre-install system libraries required by R packages
#    Doing this up front via apt is faster than letting pak discover them at
#    install time, and avoids restarting the R session mid-install.
# ---------------------------------------------------------------------------
echo "[setup] Installing system build dependencies..."
sudo apt-get install -y --no-install-recommends \
  libcurl4-openssl-dev \
  libssl-dev \
  libxml2-dev \
  libfontconfig1-dev \
  libfreetype-dev \
  libharfbuzz-dev \
  libfribidi-dev \
  libpng-dev \
  libjpeg-dev \
  libuv1-dev \
  2>/dev/null || echo "[setup] Some system packages failed — continuing."

# ---------------------------------------------------------------------------
# 3. Bootstrap pak — the fast parallel package manager for R.
#    pak: parallel downloads, automatic system-dep detection, binary packages.
#    Install strategy (in order of preference):
#      a) Already installed → skip.
#      b) pak's own r-lib CDN (independent of CRAN, pre-built binaries).
#      c) CRAN with curl retry + SSL-bypass fallback.
# ---------------------------------------------------------------------------
echo "[setup] Checking for pak..."
Rscript --no-save -e "
if (requireNamespace('pak', quietly = TRUE)) {
  message('[setup] pak ', as.character(packageVersion('pak')), ' already installed.')
  quit(status = 0)
}
message('[setup] Installing pak...')

# Strategy (a): pak CDN — pre-built binaries, no CRAN dependency
cdn_url <- sprintf(
  'https://r-lib.github.io/p/pak/stable/%s/%s/%s',
  .Platform\$pkgType, R.Version()\$os, R.Version()\$arch
)
ok <- tryCatch({
  install.packages('pak', repos = cdn_url, quiet = TRUE)
  requireNamespace('pak', quietly = TRUE)
}, error = function(e) FALSE, warning = function(w) FALSE)

if (ok) {
  message('[setup] pak installed from r-lib CDN.')
  quit(status = 0)
}

# Strategy (b): CRAN with curl retry + SSL bypass
message('[setup] r-lib CDN failed — trying CRAN...')
options(download.file.method = 'curl', download.file.extra = '-k --retry 5 --retry-delay 3 --retry-all-errors')
tryCatch({
  install.packages('pak', repos = 'https://cran.r-project.org', quiet = FALSE)
}, error = function(e) stop('[setup] Failed to install pak: ', conditionMessage(e)))

if (!requireNamespace('pak', quietly = TRUE)) {
  stop('[setup] pak installed but cannot be loaded.')
}
message('[setup] pak ', as.character(packageVersion('pak')), ' installed from CRAN.')
" 2>&1

# ---------------------------------------------------------------------------
# 4. Install all required R packages via pak
#    pak resolves and installs in parallel, detects missing system libraries,
#    and prefers pre-compiled binaries when a PPM repo is configured.
# ---------------------------------------------------------------------------

# Detect OS codename for PPM binary URL (e.g. noble, jammy)
OS_CODENAME=$(. /etc/os-release 2>/dev/null && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" || true)
if [ -z "${OS_CODENAME}" ] && command -v lsb_release &>/dev/null; then
  OS_CODENAME=$(lsb_release -cs 2>/dev/null || true)
fi

echo "[setup] Installing R packages via pak..."
Rscript --no-save - "${OS_CODENAME:-}" <<'REOF'
os_codename <- commandArgs(trailingOnly = TRUE)[1]

# Use system curl (respects OS DNS, follows CDN re-routing on retry)
# rather than R's libcurl which has its own resolver cache.
# --retry-all-errors retries on 503/transient failures; --retry-delay
# gives overloaded edge nodes time to recover between attempts.
options(
  download.file.method = "curl",
  download.file.extra  = "-k --retry 5 --retry-delay 3 --retry-all-errors",
  warn = 1
)

# Choose repository: PPM for pre-compiled binaries, CRAN as fallback.
# Probe PPM up to 3 times — a single 503 from an edge node should not
# send the whole install to slower CRAN source builds.
ppm_url <- if (nzchar(os_codename)) {
  sprintf("https://packagemanager.posit.co/cran/__linux__/%s/latest", os_codename)
} else {
  NULL
}

ppm_ok <- FALSE
if (!is.null(ppm_url)) {
  for (attempt in 1:3) {
    ppm_ok <- tryCatch({
      nrow(available.packages(repos = ppm_url)) > 100
    }, error = function(e) FALSE)
    if (ppm_ok) break
    if (attempt < 3) {
      message("[setup] PPM probe attempt ", attempt, " failed — retrying in 5s...")
      Sys.sleep(5)
    }
  }
}

repo_url <- if (ppm_ok) {
  message("[setup] Using PPM binary repo: ", ppm_url)
  ppm_url
} else {
  message("[setup] PPM unavailable — using CRAN.")
  "https://cran.r-project.org"
}

options(repos = c(CRAN = repo_url))

# Packages required by benchmark-runner automation scripts
automation_pkgs <- c(
  "jsonlite",   # JSON parse/emit in R-based dispatcher helpers
  "digest"      # SHA hashing used by deduplication logic
)

# Packages required by the group-sequential-design skill.
# Pre-installing avoids mid-benchmark install delays that skew timing.
skill_pkgs <- c(
  "gsDesign",     # group sequential boundaries and sample size
  "gsDesign2",    # non-proportional hazards evaluation
  "lrstat",       # log-rank simulation for design verification
  "graphicalMCP", # Maurer-Bretz graphical multiplicity testing
  "eventPred",    # event prediction under non-proportional hazards
  "ggplot2"       # visualisation used in skill outputs
)

all_pkgs  <- unique(c(automation_pkgs, skill_pkgs))
installed <- installed.packages()[, "Package"]
missing   <- all_pkgs[!all_pkgs %in% installed]

if (length(missing) == 0) {
  message("[setup] All packages already installed — skipping.")
} else {
  message("[setup] Installing via pak: ", paste(missing, collapse = ", "))
  # pak installs in parallel, handles system requirements, prefers binaries.
  # sysreqs = TRUE lets pak install any missing system libraries via apt.
  pak::pak(missing, upgrade = FALSE, ask = FALSE)
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
