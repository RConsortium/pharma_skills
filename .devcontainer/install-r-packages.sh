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
# PPM serves source packages by default and only delivers pre-compiled binaries
# when the HTTP User-Agent identifies the OS distribution. Without this, every
# package recompiles from source — turning a ~3 min install into ~20 min. See
# https://docs.posit.co/rspm/admin/serving-binaries.html
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
pkgs <- ${R_PKGS}
installed <- rownames(installed.packages(lib.loc = lib))
missing <- pkgs[!pkgs %in% installed]
if (length(missing)) {
  message('[setup] Installing from PPM: ', paste(missing, collapse=', '))
  install.packages(missing, lib = lib, Ncpus = parallel::detectCores())
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
