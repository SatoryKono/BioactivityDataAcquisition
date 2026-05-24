#!/usr/bin/env bash
# setup_plugins.sh - Configure development plugins for BioETL.
# Usage:
#   bash scripts/ops/launchers/codex/setup_plugins.sh
#   bash scripts/ops/launchers/codex/setup_plugins.sh --pytest-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$REPO_ROOT"

PYTEST_ONLY=false
if [[ "${1:-}" == "--pytest-only" ]]; then
    PYTEST_ONLY=true
elif [[ -n "${1:-}" ]]; then
    echo "[setup-plugins][error] Unknown argument: $1" >&2
    echo "[setup-plugins][hint] Supported arguments: --pytest-only" >&2
    exit 2
fi

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'
POSIX_VENV_PYTHON=".venv/bin/python"
WINDOWS_LOCAL_VENV_PYTHON=".venv/Scripts/python.exe"
WINDOWS_REPO_VENV_PYTHON=".venv-win/Scripts/python.exe"
PYTHON_KIND_POSIX_VENV="posix-venv"
PYTHON_KIND_WINDOWS_VENV="windows-venv"

BIOETL_WSL_VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"
PYTEST_RUNTIME_ENV_FILE="$REPO_ROOT/.pytest_cache/setup_plugins_runtime.sh"
TEMP_PYTEST_VENV_DIR="/tmp/$(basename "$REPO_ROOT")-pytest-runtime-venv"

requires_full_test_capabilities() {
    [[ "${BIOETL_REQUIRE_TEST_CAPABILITIES:-0}" == "1" ]]
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[setup-plugins]${NC} ${message}"
    return 0
}

log_ok() {
    local message="${1:-}"
    echo -e "${GREEN}[setup-plugins]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[setup-plugins]${NC} ${message}"
    return 0
}

USE_UV=false
PYTHON_BIN=""
PYTHON_KIND=""
IS_WSL=false

if [[ -n "${WSL_INTEROP:-}" ]]; then
    IS_WSL=true
fi

to_windows_path() {
    local path="$1"

    if [[ "$path" =~ ^[A-Za-z]:\\ ]]; then
        printf '%s\n' "$path"
        return 0
    fi

    if command -v wslpath >/dev/null 2>&1; then
        wslpath -w "$path"
        return 0
    fi

    if [[ "$path" =~ ^/mnt/([a-zA-Z])/(.*)$ ]]; then
        local drive="${BASH_REMATCH[1]}"
        local rest="${BASH_REMATCH[2]}"
        rest="${rest//\//\\}"
        printf '%s:\\%s\n' "${drive^^}" "$rest"
        return 0
    fi

    if [[ "$path" =~ ^/([a-zA-Z])/(.*)$ ]]; then
        local drive="${BASH_REMATCH[1]}"
        local rest="${BASH_REMATCH[2]}"
        rest="${rest//\//\\}"
        printf '%s:\\%s\n' "${drive^^}" "$rest"
        return 0
    fi

    return 1
}

if [[ "$IS_WSL" == true ]]; then
    if [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]]; then
        PYTHON_BIN="$BIOETL_WSL_VENV_DIR/bin/python"
        PYTHON_KIND="$PYTHON_KIND_POSIX_VENV"
    elif [[ -x "$POSIX_VENV_PYTHON" ]]; then
        PYTHON_BIN="$POSIX_VENV_PYTHON"
        PYTHON_KIND="$PYTHON_KIND_POSIX_VENV"
    elif command -v uv >/dev/null 2>&1; then
        USE_UV=true
        PYTHON_KIND="uv"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
        PYTHON_KIND="system-python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
        PYTHON_KIND="system-python"
    elif [[ -x "$WINDOWS_REPO_VENV_PYTHON" ]]; then
        PYTHON_BIN="$WINDOWS_REPO_VENV_PYTHON"
        PYTHON_KIND="$PYTHON_KIND_WINDOWS_VENV"
    elif [[ -x "$WINDOWS_LOCAL_VENV_PYTHON" ]]; then
        PYTHON_BIN="$WINDOWS_LOCAL_VENV_PYTHON"
        PYTHON_KIND="$PYTHON_KIND_WINDOWS_VENV"
    else
        log_warn "Python runtime not found."
        log_warn "Install uv or activate a Python environment, then rerun:"
        echo "  uv sync --extra dev --extra tests --extra tests_full --extra tracing"
        exit 1
    fi
elif [[ -x "$WINDOWS_REPO_VENV_PYTHON" ]]; then
    PYTHON_BIN="$WINDOWS_REPO_VENV_PYTHON"
    PYTHON_KIND="$PYTHON_KIND_WINDOWS_VENV"
elif [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]]; then
    PYTHON_BIN="$BIOETL_WSL_VENV_DIR/bin/python"
    PYTHON_KIND="$PYTHON_KIND_POSIX_VENV"
elif [[ -x "$WINDOWS_LOCAL_VENV_PYTHON" ]]; then
    PYTHON_BIN="$WINDOWS_LOCAL_VENV_PYTHON"
    PYTHON_KIND="$PYTHON_KIND_WINDOWS_VENV"
elif [[ -x "$POSIX_VENV_PYTHON" ]]; then
    PYTHON_BIN="$POSIX_VENV_PYTHON"
    PYTHON_KIND="$PYTHON_KIND_POSIX_VENV"
elif command -v uv >/dev/null 2>&1; then
    USE_UV=true
    PYTHON_KIND="uv"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    PYTHON_KIND="system-python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    PYTHON_KIND="system-python3"
else
    log_warn "Python runtime not found."
    log_warn "Install uv or activate a Python environment, then rerun:"
    echo "  uv sync --extra dev --extra tests --extra tests_full --extra tracing"
    exit 1
fi

run_python() {
    if [[ "$USE_UV" == true ]]; then
        uv run python "$@"
    else
        "$PYTHON_BIN" "$@"
    fi
    return 0
}

pytest_only_stamp_file() {
    printf '%s\n' "$REPO_ROOT/.pytest_cache/setup_plugins_pytest_only_${PYTHON_KIND}.stamp"
    return 0
}

pytest_only_stamp_is_fresh() {
    [[ "$PYTEST_ONLY" == true ]] || return 1

    local stamp_file
    stamp_file="$(pytest_only_stamp_file)"
    [[ -f "$stamp_file" ]] || return 1

    local tracked_files=("$REPO_ROOT/pyproject.toml" "$REPO_ROOT/uv.lock")
    if [[ "$USE_UV" == false && -n "$PYTHON_BIN" ]]; then
        tracked_files+=("$PYTHON_BIN")
    fi

    local tracked
    for tracked in "${tracked_files[@]}"; do
        [[ -e "$tracked" && "$tracked" -nt "$stamp_file" ]] && return 1
    done

    BIOETL_REQUIRE_TEST_CAPABILITIES="${BIOETL_REQUIRE_TEST_CAPABILITIES:-0}" run_python - <<'PY' >/dev/null 2>&1
import importlib.util
import os

required = (
    "pytest",
    "pytest_asyncio",
    "pytest_cov",
    "xdist",
    "pytest_timeout",
    "pytest_vcr",
    "syrupy",
    "_hypothesis_pytestplugin",
    "pydantic",
    "pandas",
    "httpx",
    "click",
    "structlog",
    "pandera",
    "respx",
)

if os.environ.get("BIOETL_REQUIRE_TEST_CAPABILITIES") == "1":
    required += (
        "opentelemetry.sdk",
        "orjson",
        "polars",
        "radon",
        "vulture",
        "importlinter",
        "pytest_benchmark",
    )

raise SystemExit(0 if all(importlib.util.find_spec(module) is not None for module in required) else 1)
PY
    return 0
}

mark_pytest_only_stamp() {
    [[ "$PYTEST_ONLY" == true ]] || return 0

    local stamp_file
    stamp_file="$(pytest_only_stamp_file)"
    mkdir -p "$(dirname "$stamp_file")"
    : > "$stamp_file"
}

find_bootstrap_python() {
    local candidate
    for candidate in "$PYTHON_BIN" python3 python; do
        [[ -n "$candidate" ]] || continue
        if command -v "$candidate" >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

python_has_required_pytest_modules() {
    local python_bin="$1"
    [[ -n "$python_bin" ]] || return 1

    local resolved_python=""
    if command -v "$python_bin" >/dev/null 2>&1; then
        resolved_python="$(command -v "$python_bin")"
    elif [[ -x "$python_bin" ]]; then
        resolved_python="$python_bin"
    else
        return 1
    fi

    BIOETL_REQUIRE_TEST_CAPABILITIES="${BIOETL_REQUIRE_TEST_CAPABILITIES:-0}" "$resolved_python" - <<'PY' >/dev/null 2>&1
import importlib.util
import os

required = (
    "pytest",
    "pytest_asyncio",
    "pytest_cov",
    "xdist",
    "pytest_timeout",
    "pytest_vcr",
    "syrupy",
    "_hypothesis_pytestplugin",
    "pydantic",
    "pandas",
    "httpx",
    "click",
    "structlog",
    "pandera",
    "respx",
)

if os.environ.get("BIOETL_REQUIRE_TEST_CAPABILITIES") == "1":
    required += (
        "opentelemetry.sdk",
        "orjson",
        "polars",
        "radon",
        "vulture",
        "importlinter",
        "pytest_benchmark",
    )

raise SystemExit(0 if all(importlib.util.find_spec(module) is not None for module in required) else 1)
PY
}

project_runtime_packages() {
    local bootstrap_python
    bootstrap_python="$(find_bootstrap_python)" || return 1

    "$bootstrap_python" - <<'PY'
from __future__ import annotations

import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
project = data["project"]

deps: list[str] = []
seen: set[str] = set()

def extend(items: list[str]) -> None:
    for item in items:
        if item not in seen:
            seen.add(item)
            deps.append(item)

extend(project.get("dependencies", []))
optional = project.get("optional-dependencies", {})
for key in ("tests", "tests_full", "dev", "tracing"):
    extend(optional.get(key, []))

for dep in deps:
    print(dep)
PY
    return 0
}

ensure_temp_pytest_runtime_venv() {
    local bootstrap_python
    bootstrap_python="$(find_bootstrap_python)" || {
        log_warn "Could not find a bootstrap Python to create temporary pytest runtime."
        return 1
    }

    if [[ -d "$TEMP_PYTEST_VENV_DIR" ]]; then
        "$bootstrap_python" -m venv --clear "$TEMP_PYTEST_VENV_DIR"
    else
        "$bootstrap_python" -m venv "$TEMP_PYTEST_VENV_DIR"
    fi

    local pip_cache_dir="/tmp/$(basename "$REPO_ROOT")-pip-cache"
    mkdir -p "$pip_cache_dir"

    local -a runtime_pkgs=()
    mapfile -t runtime_pkgs < <(project_runtime_packages)
    runtime_pkgs+=("$@")

    PIP_CACHE_DIR="$pip_cache_dir" "$TEMP_PYTEST_VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
    if ! PIP_CACHE_DIR="$pip_cache_dir" "$TEMP_PYTEST_VENV_DIR/bin/python" -m pip install "${runtime_pkgs[@]}"; then
        log_warn "Temporary pytest runtime install failed; recreating the runtime from scratch"
        "$bootstrap_python" -m venv --clear "$TEMP_PYTEST_VENV_DIR"
        PIP_CACHE_DIR="$pip_cache_dir" "$TEMP_PYTEST_VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
        PIP_CACHE_DIR="$pip_cache_dir" "$TEMP_PYTEST_VENV_DIR/bin/python" -m pip install "${runtime_pkgs[@]}"
    fi

    PYTHON_BIN="$TEMP_PYTEST_VENV_DIR/bin/python"
    PYTHON_KIND="temp-posix-venv"
    return 0
}

write_pytest_runtime_env_file() {
    mkdir -p "$(dirname "$PYTEST_RUNTIME_ENV_FILE")"
    if [[ "$USE_UV" == true ]]; then
        rm -f "$PYTEST_RUNTIME_ENV_FILE"
        return 0
    fi

    {
        printf 'export BIOETL_PYTEST_RUNTIME_PYTHON=%q\n' "$PYTHON_BIN"
    } >"$PYTEST_RUNTIME_ENV_FILE"
    return 0
}

if [[ -f "$PYTEST_RUNTIME_ENV_FILE" ]]; then
    # Reuse a previously bootstrapped temporary pytest runtime when the default
    # interpreter is present but incomplete.
    # shellcheck disable=SC1090
    source "$PYTEST_RUNTIME_ENV_FILE"
    if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]] && \
        ! python_has_required_pytest_modules "$PYTHON_BIN" && \
        python_has_required_pytest_modules "$BIOETL_PYTEST_RUNTIME_PYTHON"; then
        PYTHON_BIN="$BIOETL_PYTEST_RUNTIME_PYTHON"
        PYTHON_KIND="temp-posix-venv"
    fi
fi

install_dev_dependencies() {
    local pytest_pkgs=(
        pytest
        pytest-asyncio
        pytest-cov
        pytest-xdist
        pytest-timeout
        pytest-vcr
        syrupy
        hypothesis
    )

    if [[ "$USE_UV" == true ]]; then
        log_info "Syncing dev/test dependencies via uv..."
        uv sync --extra dev --extra tests --extra tests_full --extra tracing
    else
        log_info "Installing dev/test dependencies via pip..."
        if "$PYTHON_BIN" -m pip install -e ".[dev,tests,tests_full,tracing]"; then
            return 0
        fi
        if [[ "$PYTHON_KIND" == "$PYTHON_KIND_POSIX_VENV" || "$PYTHON_KIND" == "$PYTHON_KIND_WINDOWS_VENV" ]]; then
            log_warn "Editable install failed; creating temporary pytest runtime under /tmp"
            ensure_temp_pytest_runtime_venv "${pytest_pkgs[@]}"
            return 0
        fi
        log_warn "Pip install blocked by externally managed environment, retrying with --break-system-packages"
        if "$PYTHON_BIN" -m pip install --break-system-packages -e ".[dev,tests,tests_full,tracing]"; then
            return 0
        fi
        log_warn "Still blocked; creating temporary pytest runtime under /tmp"
        ensure_temp_pytest_runtime_venv "${pytest_pkgs[@]}"
    fi
}

check_pytest_plugins() {
    BIOETL_REQUIRE_TEST_CAPABILITIES="${BIOETL_REQUIRE_TEST_CAPABILITIES:-0}" run_python - <<'PY'
import importlib.util
import os

required = {
    "pytest": "pytest",
    "pytest_asyncio": "pytest-asyncio",
    "pytest_cov": "pytest-cov",
    "xdist": "pytest-xdist",
    "pytest_timeout": "pytest-timeout",
    "pytest_vcr": "pytest-vcr",
    "syrupy": "syrupy",
    "_hypothesis_pytestplugin": "hypothesis",
    "pydantic": "pydantic",
    "pandas": "pandas",
    "httpx": "httpx",
    "click": "click",
    "structlog": "structlog",
    "pandera": "pandera",
    "respx": "respx",
}
if os.environ.get("BIOETL_REQUIRE_TEST_CAPABILITIES") == "1":
    required.update(
        {
            "opentelemetry.sdk": "opentelemetry-sdk",
            "orjson": "orjson",
            "polars": "polars",
            "radon": "radon",
            "vulture": "vulture",
            "importlinter": "import-linter",
            "pytest_benchmark": "pytest-benchmark",
        }
    )
missing = [pkg for module, pkg in required.items() if importlib.util.find_spec(module) is None]
if missing:
    print("[setup-plugins][error] Missing pytest plugins:", ", ".join(missing))
    raise SystemExit(1)

print("[setup-plugins][ok] pytest plugins are available")
PY
    return 0
}

install_precommit() {
    if [[ "$PYTEST_ONLY" == true ]]; then
        return 0
    fi

    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        log_warn ".pre-commit-config.yaml not found, skipping hook installation"
        return 0
    fi

    log_info "Ensuring pre-commit is installed..."
    local cache_root="$REPO_ROOT/.cache"
    local precommit_home="$cache_root/pre-commit"
    local precommit_home_runtime="$precommit_home"
    local cache_root_runtime="$cache_root"
    local go_cache_runtime="$cache_root/go-build"
    local go_path_runtime="$cache_root/go"
    local uv_cache_runtime="$cache_root/uv"
    mkdir -p "$precommit_home" "$cache_root" "$cache_root/go-build" "$cache_root/go" "$cache_root/uv"

    if [[ "$PYTHON_KIND" == "windows-venv" ]] && [[ "$IS_WSL" == false ]]; then
        local precommit_home_win_runtime=""
        local cache_root_win_runtime=""
        local go_cache_win_runtime=""
        local go_path_win_runtime=""
        local uv_cache_win_runtime=""
        precommit_home_win_runtime="$(to_windows_path "$precommit_home")" || precommit_home_win_runtime=""
        cache_root_win_runtime="$(to_windows_path "$cache_root")" || cache_root_win_runtime=""
        go_cache_win_runtime="$(to_windows_path "$cache_root/go-build")" || go_cache_win_runtime=""
        go_path_win_runtime="$(to_windows_path "$cache_root/go")" || go_path_win_runtime=""
        uv_cache_win_runtime="$(to_windows_path "$cache_root/uv")" || uv_cache_win_runtime=""
        if [[ -n "$precommit_home_win_runtime" ]]; then
            precommit_home_runtime="$precommit_home_win_runtime"
        fi
        if [[ -n "$cache_root_win_runtime" ]]; then
            cache_root_runtime="$cache_root_win_runtime"
        fi
        if [[ -n "$go_cache_win_runtime" ]]; then
            go_cache_runtime="$go_cache_win_runtime"
        fi
        if [[ -n "$go_path_win_runtime" ]]; then
            go_path_runtime="$go_path_win_runtime"
        fi
        if [[ -n "$uv_cache_win_runtime" ]]; then
            uv_cache_runtime="$uv_cache_win_runtime"
        fi
    fi
    export PRE_COMMIT_HOME="$precommit_home_runtime"
    export XDG_CACHE_HOME="$cache_root_runtime"
    export GOCACHE="$go_cache_runtime"
    export GOPATH="$go_path_runtime"
    export UV_CACHE_DIR="$uv_cache_runtime"

    if [[ "$PYTHON_KIND" == "$PYTHON_KIND_WINDOWS_VENV" ]] && [[ "$IS_WSL" == false ]] && command -v powershell.exe >/dev/null 2>&1; then
        local repo_root_win=""
        local python_bin_win=""
        local precommit_home_win=""
        local cache_root_win=""
        local go_cache_win=""
        local go_path_win=""
        local uv_cache_win=""

        repo_root_win="$(to_windows_path "$REPO_ROOT")" || repo_root_win=""
        python_bin_win="$(to_windows_path "$REPO_ROOT/$PYTHON_BIN")" || python_bin_win=""
        precommit_home_win="$(to_windows_path "$precommit_home")" || precommit_home_win=""
        cache_root_win="$(to_windows_path "$cache_root")" || cache_root_win=""
        go_cache_win="$(to_windows_path "$cache_root/go-build")" || go_cache_win=""
        go_path_win="$(to_windows_path "$cache_root/go")" || go_path_win=""
        uv_cache_win="$(to_windows_path "$cache_root/uv")" || uv_cache_win=""

        if [[ -n "$repo_root_win" ]] && [[ -n "$python_bin_win" ]] && [[ -n "$precommit_home_win" ]] && [[ -n "$cache_root_win" ]] && [[ -n "$go_cache_win" ]] && [[ -n "$go_path_win" ]] && [[ -n "$uv_cache_win" ]]; then
            powershell.exe -NoProfile -Command "
\$env:Path='C:\\Program Files\\Git\\cmd;'+\$env:Path
\$env:PRE_COMMIT_HOME='$precommit_home_win'
\$env:XDG_CACHE_HOME='$cache_root_win'
\$env:GOCACHE='$go_cache_win'
\$env:GOPATH='$go_path_win'
\$env:UV_CACHE_DIR='$uv_cache_win'
New-Item -ItemType Directory -Force -Path \$env:PRE_COMMIT_HOME | Out-Null
New-Item -ItemType Directory -Force -Path \$env:XDG_CACHE_HOME | Out-Null
New-Item -ItemType Directory -Force -Path \$env:GOCACHE | Out-Null
New-Item -ItemType Directory -Force -Path \$env:GOPATH | Out-Null
New-Item -ItemType Directory -Force -Path \$env:UV_CACHE_DIR | Out-Null
Set-Location '$repo_root_win'
& '$python_bin_win' -m pre_commit install --install-hooks --hook-type pre-commit --hook-type pre-push
" >/dev/null
            log_ok "pre-commit hooks installed"
            return 0
        fi

        log_warn "Windows pre-commit bootstrap fallback could not convert required paths; using direct invocation."
    fi

    if [[ "$USE_UV" == true ]]; then
        if ! uv run python -m pre_commit --version >/dev/null 2>&1; then
            uv run python -m pip install pre-commit
        fi
        if git rev-parse --git-dir >/dev/null 2>&1; then
            uv run python -m pre_commit install --install-hooks --hook-type pre-commit --hook-type pre-push
            log_ok "pre-commit hooks installed"
        else
            log_warn "Not a git repository, skipping pre-commit install"
        fi
    else
        if ! "$PYTHON_BIN" -m pre_commit --version >/dev/null 2>&1; then
            "$PYTHON_BIN" -m pip install pre-commit
        fi
        if git rev-parse --git-dir >/dev/null 2>&1; then
            "$PYTHON_BIN" -m pre_commit install --install-hooks --hook-type pre-commit --hook-type pre-push
            log_ok "pre-commit hooks installed"
        else
            log_warn "Not a git repository, skipping pre-commit install"
        fi
    fi
    return 0
}

if pytest_only_stamp_is_fresh; then
    log_ok "pytest plugin setup already verified"
else
    if ! check_pytest_plugins; then
        install_dev_dependencies
        check_pytest_plugins
    fi
    mark_pytest_only_stamp
fi

write_pytest_runtime_env_file
install_precommit
log_ok "Plugin setup completed"
