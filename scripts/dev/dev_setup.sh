#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
[dev-setup] Legacy compatibility facade.

`scripts/dev/dev_setup.sh` is not the supported onboarding path anymore.
Use the maintained entrypoints instead:

  bash scripts/dev/setup_env_wsl.sh
  make install
  make test-deps
  make setup-plugins
  python -m scripts.dev setup-mcp

Supported compatibility flags:
  --quick   Print the recommended fast-path commands and exit 0
  --ci      Print the CI-aligned setup commands and exit 0
EOF
}

mode="${1:-}"
case "${mode}" in
    ""|"--quick"|"--ci")
        usage
        ;;
    "--help"|"-h")
        usage
        exit 0
        ;;
    *)
        echo "[dev-setup] Unsupported argument: ${mode}" >&2
        usage >&2
        exit 2
        ;;
esac

if [[ "${mode}" == "--ci" ]]; then
    cat <<'EOF'

[dev-setup] CI-aligned commands:
  uv sync --extra dev --extra tests --extra tracing
  python -m scripts.dev setup-mcp
EOF
    exit 0
fi

cat <<'EOF'

[dev-setup] Recommended WSL onboarding:
  bash scripts/dev/setup_env_wsl.sh
EOF

if [[ "${mode}" == "--quick" ]]; then
    cat <<'EOF'
[dev-setup] Fast follow-up:
  bash scripts/dev/run_pytest.sh --narrow --collect-only tests/architecture/test_boundary_assertions.py
  bash scripts/dev/run_mypy.sh --narrow --config-file pyproject.toml --strict src/bioetl/domain/__init__.py
EOF
fi
