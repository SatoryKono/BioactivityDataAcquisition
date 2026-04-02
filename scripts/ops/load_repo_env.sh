#!/usr/bin/env bash

load_repo_env_if_present() {
  if [[ "${BIOETL_REPO_ENV_LOADED:-0}" == "1" ]]; then
    return 0
  fi

  local script_dir repo_root env_file python_bin
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(cd -- "${script_dir}/../.." && pwd)"
  env_file="${BIOETL_ENV_FILE:-${repo_root}/.env}"

  if [[ ! -f "${env_file}" ]]; then
    export BIOETL_REPO_ENV_LOADED=1
    return 0
  fi

  python_bin="$(command -v python3 || command -v python || true)"
  if [[ -z "${python_bin}" ]]; then
    printf "[WARN] Python executable not found; skipping .env auto-load.\n" >&2
    export BIOETL_REPO_ENV_LOADED=1
    return 0
  fi

  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    if [[ -z "${!key+x}" || -z "${!key}" ]]; then
      printf -v "${key}" '%s' "${value}"
      export "${key}"
    fi
  done < <(
    "${python_bin}" - "${env_file}" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

env_path = Path(sys.argv[1])

for raw in env_path.read_text(encoding="utf-8").splitlines():
    stripped = raw.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw:
        continue

    key, value = raw.split("=", 1)
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        continue

    value = value.strip()
    if not value:
        parsed = ""
    elif len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        parsed = value[1:-1]
    else:
        parsed = re.sub(r"\s+#.*$", "", value).rstrip()

    sys.stdout.write(key)
    sys.stdout.write("\0")
    sys.stdout.write(parsed)
    sys.stdout.write("\0")
PY
  )

  export BIOETL_REPO_ENV_LOADED=1
}
