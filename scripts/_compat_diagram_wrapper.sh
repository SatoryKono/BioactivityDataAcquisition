#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: _compat_diagram_wrapper.sh <script-name> [args...]" >&2
  exit 2
fi

name="$1"
shift

self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${self_dir}/diagrams/${name}"

if [[ ! -f "$target" ]]; then
  echo "[ERROR] Missing canonical script: $target" >&2
  exit 2
fi

echo "[DEPRECATED] Use scripts/diagrams/${name}" >&2
exec bash "$target" "$@"
