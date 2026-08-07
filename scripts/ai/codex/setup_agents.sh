#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PERSONAL_CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
SOURCE_DIR="$REPO_ROOT/.codex/agents"
TARGET_DIR="$PERSONAL_CODEX_ROOT/agents"
INSTALL_PERSONAL=0
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: setup_agents.sh [--check] [--install-personal] [--dry-run]

Check the repository-native `.codex/agents/*.toml` descriptors. Codex discovers
them directly in a trusted checkout; no bootstrap copy is required.

`--install-personal` is an explicit compatibility option that copies the native
TOML descriptors into the current user's Codex home. `--dry-run` previews that
optional copy without writing.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --check)
            ;;
        --install-personal)
            INSTALL_PERSONAL=1
            ;;
        --dry-run)
            INSTALL_PERSONAL=1
            DRY_RUN=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

python3 - "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
sys.path.insert(0, str(repo_root / "scripts/ai/codex"))
from native_runtime_contract import validate_agents

findings = validate_agents(repo_root)
for finding in findings:
    print(f"[FAIL] {finding.code}: {finding.message} ({finding.path})")
raise SystemExit(bool(findings))
PY

mapfile -t agent_files < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name 'py-*.toml' | sort)
echo "[OK] ${#agent_files[@]} repository-native Codex agent descriptors are valid"

if [[ "$INSTALL_PERSONAL" -eq 0 ]]; then
    exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would copy optional personal descriptors: $SOURCE_DIR -> $TARGET_DIR"
    printf '  %s\n' "${agent_files[@]##*/}"
    exit 0
fi

mkdir -p "$TARGET_DIR"
for path in "${agent_files[@]}"; do
    destination="$TARGET_DIR/$(basename "$path")"
    if [[ -e "$destination" ]]; then
        echo "[WARN] Existing personal descriptor left unchanged: $destination" >&2
        continue
    fi
    cp "$path" "$destination"
done
echo "Copied ${#agent_files[@]} optional personal agent descriptors into $TARGET_DIR"
