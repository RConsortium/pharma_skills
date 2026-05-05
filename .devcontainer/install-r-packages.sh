#!/usr/bin/env bash
# Pre-install R packages used by the benchmark-runner skill and group-sequential-design.
# Runs once during codespace creation (onCreateCommand). Captured by Prebuilds.
# Uses Posit PPM noble binaries — no source compiles.
set -euo pipefail

R_LIBS_USER="${R_LIBS_USER:-/workspaces/.R-library}"
mkdir -p "${R_LIBS_USER}"
export R_LIBS_USER

# Posit Public Package Manager — pre-built Linux binaries.
# Codename is detected from the running container so this works on focal
# (universal:2-linux today), jammy, or noble.
. /etc/os-release
CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-noble}}"
PPM_URL="https://packagemanager.posit.co/cran/__linux__/${CODENAME}/latest"
echo "[setup] Using PPM repo for ${CODENAME}: ${PPM_URL}"

REQUIRED_PKGS=(
  jsonlite
  digest
  gsDesign
  gsDesign2
  lrstat
  graphicalMCP
  eventPred
  ggplot2
)

# Build R-side c("a","b",...) literal
R_PKGS=$(printf '"%s",' "${REQUIRED_PKGS[@]}")
R_PKGS="c(${R_PKGS%,})"

Rscript --no-save -e "
# HTTPUserAgent is needed so PPM serves pre-compiled binaries (instead of
# source) for the pak bootstrap install. Once pak itself is installed, it
# handles PPM binary detection on its own.
options(
  repos          = c(CRAN = '${PPM_URL}'),
  HTTPUserAgent  = sprintf(
    'R/%s R (%s)',
    getRversion(),
    paste(getRversion(), R.version\$platform, R.version\$arch, R.version\$os)
  )
)
lib <- Sys.getenv('R_LIBS_USER')
.libPaths(c(lib, .libPaths()))

# Bootstrap pak. Installs as a pre-built PPM binary thanks to the
# HTTPUserAgent option above.
if (!requireNamespace('pak', quietly = TRUE)) {
  message('[setup] Bootstrapping pak from PPM...')
  install.packages('pak', lib = lib)
}

pkgs <- ${R_PKGS}
installed <- rownames(installed.packages(lib.loc = lib))
missing <- pkgs[!pkgs %in% installed]

if (length(missing)) {
  message('[setup] Installing via pak: ', paste(missing, collapse = ', '))
  # pak: parallel downloads, PPM-aware binary delivery, automatic apt sysreqs
  # detection (e.g. libuv1-dev for fs). install-r.sh already pre-installs the
  # common -dev packages so this normally short-circuits the apt step.
  pak::pkg_install(missing, lib = lib, ask = FALSE)
} else {
  message('[setup] All packages already present in ', lib)
}

for (p in pkgs) {
  if (!requireNamespace(p, quietly = TRUE, lib.loc = lib)) {
    stop('[setup] Failed to load: ', p)
  }
}
message('[setup] Verified ', length(pkgs), ' R packages.')
"
