#!/usr/bin/env bash
set -euo pipefail

self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
name="$(basename "${BASH_SOURCE[0]}")"

echo "[DEPRECATED] Use scripts/diagrams/${name}" >&2
exec bash "${self_dir}/diagrams/${name}" "$@"
