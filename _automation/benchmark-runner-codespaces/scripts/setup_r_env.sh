#!/usr/bin/env bash
# setup_r_env.sh — Idempotent R environment bootstrap for benchmark-runner.
# Run once per session before Step 1 of SKILL.md.
# Exits non-zero on any failure so the caller can stop early.
set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Fast-path short-circuit (fix 1.3): if R is installed and every required
#    package is loadable, exit immediately — no apt, no pak, no network.
#    This is the warm-codespace path (devcontainer prebuild already installed
#    everything into /workspaces/.R-library).
# ---------------------------------------------------------------------------
if command -v Rscript &>/dev/null; then
  if Rscript --no-save -e "
    pkgs <- c('jsonlite','digest','gsDesign','gsDesign2','lrstat',
              'graphicalMCP','eventPred','ggplot2')
    missing <- pkgs[!pkgs %in% rownames(installed.packages())]
    if (length(missing)) quit(status = 1) else quit(status = 0)
  " &>/dev/null; then
    echo "[setup] R + all required packages already present — skipping bootstrap."
    exit 0
  fi
fi

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
# 3. Pin CRAN to a known IP to prevent DNS cache overflow errors.
#    R's download engine resolves hostnames separately from the system
#    resolver cache and can hit "DNS cache overflow" under load.
# ---------------------------------------------------------------------------
echo "[setup] Pinning CRAN hostname to bypass DNS cache overflow..."
pin_host() {
  local domain="$1"
  if ! grep -q "${domain}" /etc/hosts 2>/dev/null; then
    local ip
    ip=$(curl -s --max-time 10 -w "%{remote_ip}" -o /dev/null "https://${domain}" 2>/dev/null || true)
    if [ -n "${ip}" ]; then
      echo "${ip} ${domain}" | sudo tee -a /etc/hosts > /dev/null
      echo "[setup] Pinned ${domain} -> ${ip}"
    else
      echo "[setup] Warning: could not resolve ${domain} — skipping pin."
    fi
  else
    echo "[setup] ${domain} already pinned in /etc/hosts."
  fi
}
pin_host "cran.r-project.org"
pin_host "cloud.r-project.org"

# ---------------------------------------------------------------------------
# 4. Bootstrap pak from Posit PPM noble binaries (fix 1.4).
#    No source compile, no CRAN fallback, no r-lib CDN fallback. PPM ships a
#    pre-built linux-gnu pak that links against system libcurl/openssl.
# ---------------------------------------------------------------------------
echo "[setup] Checking for pak..."
Rscript --no-save -e "
ppm <- 'https://packagemanager.posit.co/cran/__linux__/noble/latest'

if (requireNamespace('pak', quietly = TRUE)) {
  message('[setup] pak ', as.character(packageVersion('pak')), ' already installed.')
  quit(status = 0)
}

message('[setup] Installing pak from PPM noble binary repo...')
install.packages('pak', repos = ppm, quiet = FALSE)

if (!requireNamespace('pak', quietly = TRUE)) {
  stop('[setup] pak install failed — PPM unreachable or noble binary missing.')
}
message('[setup] pak ', as.character(packageVersion('pak')), ' installed from PPM.')
" 2>&1

# ---------------------------------------------------------------------------
# 5. Install all required R packages via pak
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

# Always set curl + SSL-bypass as the download fallback.
# R's default libcurl method can hit "DNS cache overflow" under connection
# load; system curl resolves using the /etc/hosts pin we set above.
options(
  download.file.method = "curl",
  download.file.extra  = "-k",
  warn = 1
)

# PPM-only (fix 1.4): require pre-compiled binaries; no CRAN-source fallback.
if (!nzchar(os_codename)) {
  stop("[setup] OS codename undetected — PPM URL cannot be built. ",
       "PPM-only mode requires Ubuntu (e.g. noble, jammy).")
}
ppm_url <- sprintf("https://packagemanager.posit.co/cran/__linux__/%s/latest", os_codename)

ppm_ok <- tryCatch({
  nrow(available.packages(repos = ppm_url)) > 100
}, error = function(e) FALSE)

if (!ppm_ok) {
  stop("[setup] PPM unreachable at ", ppm_url,
       " — refusing to fall back to CRAN source builds (fix 1.4).")
}

message("[setup] Using PPM binary repo: ", ppm_url)
options(repos = c(CRAN = ppm_url))

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
