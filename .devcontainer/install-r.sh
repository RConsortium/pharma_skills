#!/usr/bin/env bash
# Install R from CRAN's apt repository on a Codespaces universal image.
#
# We do this ourselves instead of using the rocker-org r-apt devcontainer
# feature because that feature runs `apt-get update` which fails on the
# universal:2-linux base image: the image ships with a stale Yarn apt source
# (dl.yarnpkg.com) whose GPG key was rotated, returning NO_PUBKEY 62D54FD4003F6525
# and exit code 100. The feature treats that as fatal and aborts the build.
#
# This script removes the broken Yarn source, adds the signed CRAN repo, and
# installs r-base.
set -euo pipefail

if command -v R &>/dev/null; then
  echo "[install-r] R already installed: $(R --version | head -1)"
  exit 0
fi

echo "[install-r] Installing R from CRAN..."

# Workaround: drop the universal image's stale Yarn apt source so apt-get
# update returns success.
if [ -f /etc/apt/sources.list.d/yarn.list ]; then
  echo "[install-r] Removing stale /etc/apt/sources.list.d/yarn.list"
  sudo rm -f /etc/apt/sources.list.d/yarn.list
fi

# Detect Ubuntu codename (focal / jammy / noble) — universal:2-linux is focal
# today but the image's distro can change.
. /etc/os-release
CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
if [ -z "${CODENAME}" ]; then
  echo "[install-r] Cannot detect Ubuntu codename — aborting." >&2
  exit 1
fi
echo "[install-r] Detected Ubuntu ${VERSION_ID} (${CODENAME})"

# Apt resilience: configure aggressive retries + longer timeouts to
# survive transient mirror flakiness. (Originally added because focal
# mirrors were unreliable on universal:2-linux; harmless on noble, kept
# as defense-in-depth.)
sudo tee /etc/apt/apt.conf.d/80-codespaces-resilience > /dev/null <<'APTCONF'
Acquire::Retries "10";
Acquire::http::Timeout "30";
Acquire::https::Timeout "30";
Acquire::http::No-Cache "true";
APTCONF

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends --fix-missing \
  ca-certificates curl gnupg lsb-release

# CRAN signing key (Marutter / R Foundation). Stored in /etc/apt/keyrings.
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc \
  | sudo gpg --dearmor --yes -o /etc/apt/keyrings/cran-r.gpg

echo "deb [signed-by=/etc/apt/keyrings/cran-r.gpg] https://cloud.r-project.org/bin/linux/ubuntu ${CODENAME}-cran40/" \
  | sudo tee /etc/apt/sources.list.d/cran-r.list > /dev/null

sudo apt-get update -qq
# r-base + every system dep pak might detect as missing during R-package
# install. We pre-install all of them here so pak doesn't run its OWN
# apt-get update + apt-get install cycle (which would double the apt time
# on any slow mirror).
#
# - libuv1-dev:   fs (transitive dep of bslib -> rmarkdown -> gsDesign etc.)
# - pandoc:       knitr, rmarkdown
# - libnode-dev:  V8 (used by gt -> juicyjuice)
# - libxml2-dev .. libcairo2-dev: graphics + markup deps for ggplot2, gt, etc.
#
# Wrapped in a retry loop as defense-in-depth against transient apt mirror
# failures. The Acquire::Retries config above handles per-deb retries; this
# loop handles the case where apt as a whole returns non-zero.
APT_PKGS="r-base r-base-dev \
  pandoc libnode-dev libuv1-dev \
  libxml2-dev libfontconfig1-dev libfreetype-dev \
  libharfbuzz-dev libfribidi-dev libpng-dev libjpeg-dev libtiff-dev \
  libcairo2-dev"

for attempt in 1 2 3; do
  if sudo apt-get install -y --no-install-recommends --fix-missing ${APT_PKGS}; then
    break
  fi
  if [ "${attempt}" -eq 3 ]; then
    echo "[install-r] apt install failed after 3 attempts." >&2
    exit 1
  fi
  echo "[install-r] apt install failed (attempt ${attempt}/3) — retrying after 15s..."
  sleep 15
  sudo apt-get update -qq || true
done

R --version | head -1
echo "[install-r] R installation complete."
