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

# Apt resilience: focal's archive.ubuntu.com mirrors are unreliable
# (the distro is EOL and traffic gets deprioritized — see the connection
# timeouts in the previous build log). Configure aggressive retries +
# longer timeouts before the first fetch.
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
# r-base + system deps that R packages with C/C++ extensions need at install time.
# libuv1-dev is required by the `fs` package (which is a transitive dep of fs ->
# sass -> bslib -> rmarkdown -> ... -> gsDesign etc.). Without it the install
# of `fs` fails and cascades to ~13 other packages.
#
# Wrapped in a retry loop because focal's apt mirrors drop connections
# mid-download intermittently. The Acquire::Retries config above handles
# per-deb retries; this loop handles the case where apt as a whole returns
# non-zero after exhausting them.
APT_PKGS="r-base r-base-dev \
  libuv1-dev libxml2-dev libfontconfig1-dev libfreetype6-dev \
  libharfbuzz-dev libfribidi-dev libpng-dev libjpeg-dev libtiff5-dev \
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
