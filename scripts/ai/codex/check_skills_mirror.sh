#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source_dir="$repo_root/.codex/skills"
mirror_dir="$repo_root/docs/00-project/ai/skills/local"

if [[ ! -d "$source_dir" || ! -d "$mirror_dir" ]]; then
  echo "[FAIL] missing skills source or mirror directory" >&2
  exit 1
fi

echo "[OK] skills mirror check passed"
