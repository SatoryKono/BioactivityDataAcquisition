#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
for d in ".codex/skills" "docs/00-project/ai/skills/local" "docs/00-project/ai/skills/global"; do
  if [[ ! -d "$repo_root/$d" ]]; then
    echo "[FAIL] missing required skills directory: $d" >&2
    exit 1
  fi
done

echo "[OK] skills layout check passed"
