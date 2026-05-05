#!/usr/bin/env bash
# Pre-install R packages used by the benchmark-runner skill and group-sequential-design.
# Runs once during codespace creation (onCreateCommand). Captured by Prebuilds.
# Uses Posit PPM noble binaries — no source compiles.
set -euo pipefail

R_LIBS_USER="${R_LIBS_USER:-/workspaces/.R-library}"
mkdir -p "${R_LIBS_USER}"
export R_LIBS_USER

# Posit Public Package Manager — pre-built Linux binaries for Ubuntu 24.04 (noble).
PPM_URL="https://packagemanager.posit.co/cran/__linux__/noble/latest"

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
options(repos = c(CRAN = '${PPM_URL}'))
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
