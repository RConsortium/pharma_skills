#!/usr/bin/env bash
# setup_r_env.sh — Idempotent R environment bootstrap for benchmark-runner.
# Run once per session before Step 1 of SKILL.md.
# Exits non-zero on any failure so the caller can stop early.
set -euo pipefail

can_run_elevated() {
  if [ "$(id -u)" -eq 0 ]; then
    return 0
  fi
  command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1
}

run_elevated() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

choose_writable_r_lib() {
  local candidate
  for candidate in \
    "${PHARMA_SKILLS_R_LIB:-}" \
    "${R_LIBS_USER:-}" \
    "${PWD}/.cache/pharma_r_lib" \
    "${TMPDIR:-/tmp}/pharma_r_lib" \
    "/private/tmp/pharma_r_lib"
  do
    [ -n "${candidate}" ] || continue
    if mkdir -p "${candidate}" 2>/dev/null && [ -w "${candidate}" ]; then
      export R_LIBS_USER="${candidate}"
      echo "[setup] Using writable R library: ${R_LIBS_USER}"
      return 0
    fi
  done

  echo "[setup] ERROR: could not find a writable R package library. Set PHARMA_SKILLS_R_LIB or R_LIBS_USER." >&2
  exit 1
}

choose_writable_r_lib

# ---------------------------------------------------------------------------
# 1. Install R base if not present
# ---------------------------------------------------------------------------
if ! command -v R &>/dev/null; then
  if command -v apt-get &>/dev/null && can_run_elevated; then
    echo "[setup] R not found — installing r-base via apt-get..."
    run_elevated apt-get update -qq
    run_elevated apt-get install -y r-base
  else
    echo "[setup] ERROR: R is not installed and this environment cannot install it automatically." >&2
    echo "[setup] Install R manually or run in an environment with apt-get + sudo/root." >&2
    exit 1
  fi
fi

R_VERSION=$(R --version | head -1 | awk '{print $3}')
echo "[setup] R ${R_VERSION} available."

# ---------------------------------------------------------------------------
# 2. Pre-install system libraries required by R packages
#    Doing this up front via apt is faster than letting pak discover them at
#    install time, and avoids restarting the R session mid-install.
# ---------------------------------------------------------------------------
if command -v apt-get &>/dev/null && can_run_elevated; then
  echo "[setup] Installing system build dependencies..."
  run_elevated apt-get install -y --no-install-recommends \
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
else
  echo "[setup] Skipping apt system dependencies — apt-get or sudo/root unavailable."
fi

# ---------------------------------------------------------------------------
# 3. Pin CRAN to a known IP to prevent DNS cache overflow errors.
#    R's download engine resolves hostnames separately from the system
#    resolver cache and can hit "DNS cache overflow" under load.
# ---------------------------------------------------------------------------
echo "[setup] Pinning CRAN hostname to bypass DNS cache overflow..."
pin_host() {
  local domain="$1"
  if [ ! -w /etc/hosts ] && ! can_run_elevated; then
    echo "[setup] Skipping /etc/hosts pin for ${domain} — no write access."
    return 0
  fi
  if ! grep -q "${domain}" /etc/hosts 2>/dev/null; then
    local ip
    ip=$(curl -s --max-time 10 -w "%{remote_ip}" -o /dev/null "https://${domain}" 2>/dev/null || true)
    if [ -n "${ip}" ]; then
      printf '%s %s\n' "${ip}" "${domain}" | run_elevated tee -a /etc/hosts > /dev/null
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
# 4. Bootstrap pak — the fast parallel package manager for R.
#    pak: parallel downloads, automatic system-dep detection, binary packages.
#
#    Install strategy (in order of preference):
#      a) Already installed AND built for linux-gnu → skip.
#         A pre-existing linux-musl build (from the r-lib CDN) is treated
#         as unusable here because its statically-linked libcurl ships with
#         a vendored CA bundle and ignores CURL_CA_BUNDLE / SSL_CERT_FILE.
#         In sandboxes behind a TLS-intercepting egress proxy that signs
#         with a custom root CA, that build fails every CRAN/Bioc fetch
#         with "self signed certificate in certificate chain". We remove it
#         and reinstall from source.
#      b) Install from source via CRAN. The resulting pak links against
#         system libcurl/openssl (libcurl4-openssl-dev + libssl-dev from
#         Step 2), which honor the system CA bundle and any proxy CAs in
#         /etc/ssl/certs/ca-certificates.crt.
#      c) r-lib CDN pre-built binary as a last resort. Faster on
#         unrestricted networks but may fail at runtime in proxied
#         sandboxes (see strategy a).
# ---------------------------------------------------------------------------
echo "[setup] Checking for pak..."
Rscript --no-save -e "
pak_platform_ok <- function() {
  sitrep <- utils::capture.output(pak::pak_sitrep())
  any(grepl('pak platform:.*linux-gnu', sitrep))
}

if (requireNamespace('pak', quietly = TRUE)) {
  if (isTRUE(try(pak_platform_ok(), silent = TRUE))) {
    message('[setup] pak ', as.character(packageVersion('pak')),
            ' (linux-gnu) already installed.')
    quit(status = 0)
  }
  message('[setup] Existing pak is not a linux-gnu build — removing and ',
          'reinstalling from source so it uses system libcurl/openssl.')
  try(utils::remove.packages('pak'), silent = TRUE)
}

message('[setup] Installing pak from source (links against system ',
        'libcurl/openssl so the system CA bundle is honored)...')

# Strategy (b): source install from CRAN. Requires libcurl4-openssl-dev +
# libssl-dev, which Step 2 already installs.
ok <- tryCatch({
  install.packages(
    'pak',
    type  = 'source',
    repos = 'https://cloud.r-project.org',
    quiet = FALSE
  )
  requireNamespace('pak', quietly = TRUE)
}, error = function(e) FALSE, warning = function(w) FALSE)

if (ok) {
  message('[setup] pak ', as.character(packageVersion('pak')),
          ' installed from CRAN source.')
  quit(status = 0)
}

# Strategy (c): pak CDN binary fallback — may not work behind a
# TLS-intercepting proxy, but works on unrestricted networks.
message('[setup] CRAN source build failed — trying r-lib CDN binary...')
cdn_url <- sprintf(
  'https://r-lib.github.io/p/pak/stable/%s/%s/%s',
  .Platform\$pkgType, R.Version()\$os, R.Version()\$arch
)
tryCatch({
  install.packages('pak', repos = cdn_url, quiet = FALSE)
}, error = function(e) stop('[setup] Failed to install pak: ',
                            conditionMessage(e)))

if (!requireNamespace('pak', quietly = TRUE)) {
  stop('[setup] pak installed but cannot be loaded.')
}
message('[setup] pak ', as.character(packageVersion('pak')),
        ' installed from r-lib CDN.')
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

# Choose repository: PPM for pre-compiled binaries, CRAN as fallback.
ppm_url <- if (nzchar(os_codename)) {
  sprintf("https://packagemanager.posit.co/cran/__linux__/%s/latest", os_codename)
} else {
  NULL
}

ppm_ok <- !is.null(ppm_url) && tryCatch({
  nrow(available.packages(repos = ppm_url)) > 100
}, error = function(e) FALSE)

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
