#!/usr/bin/env bash
# Install Claude Code CLI during codespace creation.
# OAuth login cannot be automated — see notes printed at the end.
set -euo pipefail

if command -v claude &>/dev/null; then
  echo "[setup] Claude Code already installed: $(claude --version 2>&1 | head -1)"
  exit 0
fi

echo "[setup] Installing Claude Code CLI..."
curl -fsSL https://claude.ai/install.sh | bash

# The installer drops the binary in ~/.local/bin (already on PATH in Codespaces
# universal image). Re-export defensively for this shell.
export PATH="$HOME/.local/bin:$PATH"

if ! command -v claude &>/dev/null; then
  echo "[setup] WARNING: 'claude' not on PATH after install. Check ~/.local/bin." >&2
  exit 1
fi

echo "[setup] Claude Code installed: $(claude --version 2>&1 | head -1)"

cat <<'NOTES'

[setup] ---------------------------------------------------------------
[setup] Claude Code authentication (one-time, per codespace):
[setup]
[setup]   Option 1 (recommended) — Set ANTHROPIC_API_KEY as a Codespaces
[setup]   secret in repo Settings -> Secrets and variables -> Codespaces.
[setup]   It will be auto-injected on every codespace boot.
[setup]
[setup]   Option 2 — Run 'claude' once interactively and complete the
[setup]   browser OAuth flow. Credentials persist in ~/.claude/ for the
[setup]   life of this codespace.
[setup]
[setup] GitHub auth is already configured by Codespaces — 'gh' CLI is
[setup] authenticated to the host repo via the injected GITHUB_TOKEN.
[setup] For broader-scope ops, add a PAT as the GH_TOKEN Codespaces
[setup] secret.
[setup] ---------------------------------------------------------------
NOTES
