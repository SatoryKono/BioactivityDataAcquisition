#!/usr/bin/env bash
set -euo pipefail

ROUTER_MODULE="scripts.docs"
ROUTER_COMMAND="build-site"

run_router() {
  local python_bin="$1"
  shift
  "$python_bin" -m "$ROUTER_MODULE" "$ROUTER_COMMAND" "$@"
  return $?
}

run_windows_router_via_cmd() {
  local win_python="$1"
  shift
  local win_repo_root
  local escaped_args=()
  local arg

  win_repo_root="$(wslpath -w "$PWD")"
  for arg in "$@"; do
    arg="${arg//\\/\\\\}"
    arg="${arg//\"/\\\"}"
    escaped_args+=("\"$arg\"")
  done

  cmd.exe /c "cd /d \"$win_repo_root\" && ${win_python} -m $ROUTER_MODULE $ROUTER_COMMAND ${escaped_args[*]}"
  return $?
}

run_windows_python() {
  local python_bin="$1"
  shift
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    local win_python="${python_bin#./}"
    win_python="${win_python//\//\\}"
    run_windows_router_via_cmd "$win_python" "$@"
    return $?
  fi
  run_router "$python_bin" "$@"
}

if command -v python >/dev/null 2>&1 && python -c "import mkdocs" >/dev/null 2>&1; then
  run_router python "$@"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import mkdocs" >/dev/null 2>&1; then
  run_router python3 "$@"
elif [[ -x "./.venv/bin/python" ]]; then
  run_router ./.venv/bin/python "$@"
elif [[ -x "./.venv-win/Scripts/python.exe" ]] && ./.venv-win/Scripts/python.exe -c "import mkdocs" >/dev/null 2>&1; then
  run_router ./.venv-win/Scripts/python.exe "$@"
elif [[ -x "./.venv/Scripts/python.exe" ]]; then
  # WSL can fail executing Windows binaries directly depending on interop policy.
  run_windows_python ./.venv/Scripts/python.exe "$@"
elif [[ -x "./.venv-win/Scripts/python.exe" ]] && ./.venv-win/Scripts/python.exe -c "import mkdocs" >/dev/null 2>&1; then
  run_windows_python ./.venv-win/Scripts/python.exe "$@"
else
  echo "No MkDocs-capable Python interpreter found for scripts.docs build-site" >&2
  exit 1
fi
