#!/usr/bin/env bash
# Pre-install Python packages used by skills that ship Python report builders
# (group-sequential-design's gsd_report.py uses python-docx). Runs once during
# codespace creation. Without this, agents loop on `pip install` retries
# (PEP668-protected system python) before the report step.
set -euo pipefail

PKGS=(
  python-docx   # used by gsd_report.py to emit gsd_report.docx
)

# System python on Ubuntu 24.04 is PEP668-marked (externally-managed). The
# devcontainer Python feature provides /usr/local/bin/python which is not
# externally-managed; prefer that. Fall back to system python with the override.
if command -v /usr/local/bin/python &>/dev/null; then
  PIP=(/usr/local/bin/python -m pip install)
else
  PIP=(python3 -m pip install --break-system-packages)
fi

echo "[setup] Installing Python packages: ${PKGS[*]}"
"${PIP[@]}" "${PKGS[@]}"

# Verify each loads
python3 - <<'PYEOF'
import importlib, sys
mods = {"python-docx": "docx"}
failed = [pkg for pkg, mod in mods.items() if (importlib.util.find_spec(mod) is None)]
if failed:
    print(f"[setup] FAILED to import: {failed}", file=sys.stderr)
    sys.exit(1)
print(f"[setup] Verified {len(mods)} Python packages.")
PYEOF
