#!/usr/bin/env bash
# Unified runner for diagram validation suites.
# Profiles:
#   pr      - hard-gate PR checks (syntax/lint/render/artifacts/smoke/quality)
#   nightly - pr profile + nightly DIAG-T024..T029 suite
#   quick   - lightweight local checks without render
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$REPO_ROOT_GIT"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
# shellcheck source=scripts/diagrams/diagram_paths.sh
source "$REPO_ROOT/scripts/diagrams/diagram_paths.sh"
PROFILE="pr"
PUPPETEER_CFG="${PUPPETEER_CFG:-/tmp/puppeteer-config.json}"
FORCE_WRITE_PUPPETEER=0
STRICT_NIGHTLY=0
SKIP_RENDER=0
ENFORCE_BUDGET=0
DIAGRAM_PATH=""
TEXT_LAYER="${TEXT_LAYER:-fallback-only}"
SOURCE_MANIFEST="$DIAGRAM_QUALITY_MANIFEST"
RENDER_MANIFEST="$DIAGRAM_VISUAL_MANIFEST"
TEMP_SOURCE_MANIFEST=""
TEMP_RENDER_MANIFEST=""
BUDGET_TMP_DIR=""
BUDGET_QUALITY_JSON=""
BUDGET_LINT_JSON=""
BUDGET_NIGHTLY_JSON=""
THEME_CONFIG="$DIAGRAM_THEME_DIR/mermaid-config.json"

usage() {
  cat <<'EOF'
Usage: scripts/diagrams/run_diagram_checks.sh [options]

Options:
  --profile <pr|nightly|quick>   Check profile (default: pr)
  --diagram <path>               Run checks only for one .mmd/.mermaid diagram
  --puppeteer <path>             Puppeteer config path (default: /tmp/puppeteer-config.json)
  --refresh-puppeteer-config     Rewrite Puppeteer config file if it already exists
  --text-layer <mode>            SVG text layers: dual|fo-only|fallback-only (default: fallback-only)
  --enforce-budget               Enforce diagram quality budget (blocking)
  --strict-nightly               Fail nightly profile on warnings
  --skip-render                  Skip render step (useful for local dry loops)
  -h, --help                     Show this help

Examples:
  scripts/diagrams/run_diagram_checks.sh --profile pr
  scripts/diagrams/run_diagram_checks.sh --profile pr --diagram <repo-relative-diagram-path>
  scripts/diagrams/run_diagram_checks.sh --profile pr --text-layer fallback-only
  scripts/diagrams/run_diagram_checks.sh --profile pr --enforce-budget
  scripts/diagrams/run_diagram_checks.sh --profile nightly --strict-nightly
  scripts/diagrams/run_diagram_checks.sh --profile quick
EOF
  return 0
}

log() {
  printf '[INFO] %s\n' "$*"
  return 0
}

cleanup_temp_manifests() {
  [[ -n "$TEMP_SOURCE_MANIFEST" ]] && rm -f "$TEMP_SOURCE_MANIFEST" || true
  [[ -n "$TEMP_RENDER_MANIFEST" ]] && rm -f "$TEMP_RENDER_MANIFEST" || true
  [[ -n "$BUDGET_TMP_DIR" ]] && rm -rf "$BUDGET_TMP_DIR" || true
  return 0
}

trap cleanup_temp_manifests EXIT

ensure_puppeteer_config() {
  local cfg_dir
  cfg_dir="$(dirname "$PUPPETEER_CFG")"
  mkdir -p "$cfg_dir"

  if [[ -f "$PUPPETEER_CFG" && "$FORCE_WRITE_PUPPETEER" -eq 0 ]]; then
    log "Using existing Puppeteer config: $PUPPETEER_CFG"
    return 0
  fi

  if [[ -f "$PUPPETEER_CFG" && "$FORCE_WRITE_PUPPETEER" -eq 1 ]]; then
    log "Rewriting Puppeteer config (--refresh-puppeteer-config): $PUPPETEER_CFG"
  else
    log "Creating Puppeteer config: $PUPPETEER_CFG"
  fi

  PUPPETEER_CFG="$PUPPETEER_CFG" \
  PUPPETEER_EXECUTABLE_PATH="${PUPPETEER_EXECUTABLE_PATH:-}" \
  HOME_DIR="${HOME:-}" \
  python3 - <<'PY'
import json
import os
from pathlib import Path
from shutil import which

cfg_path = Path(os.environ["PUPPETEER_CFG"])
cfg = {
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
}
exec_path = os.environ.get("PUPPETEER_EXECUTABLE_PATH", "").strip()
if not exec_path:
    from_path = which("chrome-headless-shell")
    if from_path:
        exec_path = from_path
if not exec_path:
    home_dir = os.environ.get("HOME_DIR", "").strip()
    if home_dir:
        cache_root = Path(home_dir) / ".cache/puppeteer/chrome-headless-shell"
        candidates = sorted(
            cache_root.glob("linux-*/chrome-headless-shell-linux64/chrome-headless-shell")
        )
        if candidates:
            exec_path = str(candidates[-1])
if exec_path:
    cfg["executablePath"] = exec_path

cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
PY
  return 0
}

validate_puppeteer_config() {
  if [[ ! -f "$PUPPETEER_CFG" ]]; then
    echo "Puppeteer config does not exist: $PUPPETEER_CFG" >&2
    exit 2
  fi

  if ! PUPPETEER_CFG="$PUPPETEER_CFG" python3 - <<'PY'
import json
import os
from pathlib import Path

cfg_path = Path(os.environ["PUPPETEER_CFG"])
raw = cfg_path.read_text(encoding="utf-8")
cfg = json.loads(raw)
if not isinstance(cfg, dict):
    raise ValueError("config root must be JSON object")

args = cfg.get("args")
if args is not None:
    if not isinstance(args, list):
        raise ValueError("'args' must be a list")
    for idx, item in enumerate(args):
        if not isinstance(item, str):
            raise ValueError(f"'args[{idx}]' must be a string")

executable = cfg.get("executablePath")
if executable is not None and (not isinstance(executable, str) or not executable.strip()):
    raise ValueError("'executablePath' must be a non-empty string")
PY
  then
    echo "Invalid Puppeteer config JSON: $PUPPETEER_CFG" >&2
    exit 2
  fi
  return 0
}

run_puppeteer_preflight() {
  local browser_bin=""
  local has_no_sandbox="unknown"
  local executable_path=""
  local preflight_lines=()

  for candidate in chrome-headless-shell chromium chromium-browser google-chrome google-chrome-stable; do
    if command -v "$candidate" >/dev/null 2>&1; then
      browser_bin="$candidate"
      break
    fi
  done

  if [[ -z "$browser_bin" ]]; then
    log "Preflight: no system Chrome/Chromium found in PATH (Puppeteer-managed browser may still work)."
  else
    log "Preflight: system browser found in PATH: $browser_bin"
  fi

  if [[ "$(id -u)" -eq 0 ]]; then
    log "Preflight: running as root (requires --no-sandbox in Puppeteer args)."
  fi

  mapfile -t preflight_lines < <(
    PUPPETEER_CFG="$PUPPETEER_CFG" python3 - <<'PY'
import json
import os
from pathlib import Path

cfg = json.loads(Path(os.environ["PUPPETEER_CFG"]).read_text(encoding="utf-8"))
args = cfg.get("args", [])
exec_path = cfg.get("executablePath", "")
has_no_sandbox = "--no-sandbox" in args
exec_print = exec_path if isinstance(exec_path, str) else ""
print(f"EXEC_PATH={exec_print}")
print(f"HAS_NO_SANDBOX={'true' if has_no_sandbox else 'false'}")
PY
  )

  for line in "${preflight_lines[@]}"; do
    case "$line" in
      EXEC_PATH=*)
        executable_path="${line#EXEC_PATH=}"
        ;;
      HAS_NO_SANDBOX=*)
        has_no_sandbox="${line#HAS_NO_SANDBOX=}"
        ;;
      *)
        log "Preflight: ignoring unexpected parser output: $line"
        ;;
    esac
  done

  if [[ -n "$executable_path" ]]; then
    log "Preflight: Puppeteer executablePath override enabled: $executable_path"
  else
    log "Preflight: Puppeteer executablePath not set (auto-discovery mode)."
  fi
  log "Preflight: Puppeteer args include --no-sandbox: $has_no_sandbox"
  return 0
}

run_syntax_check() {
  if [[ -z "$DIAGRAM_PATH" ]]; then
    bash "$REPO_ROOT/scripts/diagrams/validate_mermaid_syntax.sh" \
      --scope canonical \
      --puppeteer "$PUPPETEER_CFG"
    return 0
  fi

  if ! command -v mmdc >/dev/null 2>&1; then
    echo "Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
    exit 2
  fi

  local source_abs="$REPO_ROOT/$DIAGRAM_PATH"
  local tmp_svg
  local tmp_err
  tmp_svg="$(mktemp "${TMPDIR:-/tmp}/diagram-syntax.XXXXXX.svg")"
  tmp_err="$(mktemp "${TMPDIR:-/tmp}/diagram-syntax.XXXXXX.err")"
  local mmdc_args=()
  [[ -f "$THEME_CONFIG" ]] && mmdc_args+=(-c "$THEME_CONFIG")
  [[ -n "$PUPPETEER_CFG" ]] && mmdc_args+=(-p "$PUPPETEER_CFG")

  if ! mmdc -i "$source_abs" -o "$tmp_svg" "${mmdc_args[@]}" >/dev/null 2>"$tmp_err"; then
    echo "ERROR: Mermaid validation failed for $DIAGRAM_PATH" >&2
    if grep -q "Could not find Chrome" "$tmp_err"; then
      echo "HINT: mmdc could not find Chrome/Chromium for Puppeteer." >&2
    fi
    sed -n '1,8p' "$tmp_err" >&2 || true
    rm -f "$tmp_svg" "$tmp_err"
    exit 1
  fi

  rm -f "$tmp_svg" "$tmp_err"
  log "Syntax validation passed for $DIAGRAM_PATH"
  return 0
}

prepare_diagram_scope() {
  local input_path="$1"
  local abs_path="$input_path"

  if [[ "$abs_path" != /* ]]; then
    abs_path="$REPO_ROOT/$abs_path"
  fi
  if [[ ! -f "$abs_path" ]]; then
    echo "--diagram file not found: $input_path" >&2
    exit 2
  fi

  case "$abs_path" in
    *.mmd|*.mermaid) ;;
    *)
      echo "--diagram must point to .mmd or .mermaid file: $input_path" >&2
      exit 2
      ;;
  esac

  local rel_path="${abs_path#$REPO_ROOT/}"
  if [[ "$rel_path" == "$abs_path" ]]; then
    echo "--diagram must be inside repository: $input_path" >&2
    exit 2
  fi

  DIAGRAM_PATH="$rel_path"
  TEMP_SOURCE_MANIFEST="$(mktemp "${TMPDIR:-/tmp}/diagram-source-manifest.XXXXXX.txt")"
  TEMP_RENDER_MANIFEST="$(mktemp "${TMPDIR:-/tmp}/diagram-render-manifest.XXXXXX.txt")"
  printf '%s\n' "$DIAGRAM_PATH" > "$TEMP_SOURCE_MANIFEST"

  local diagram_dir
  local diagram_stem
  diagram_dir="$(dirname "$DIAGRAM_PATH")"
  diagram_stem="$(basename "${DIAGRAM_PATH%.*}")"
  printf '%s\n' "${diagram_dir}/svg/${diagram_stem}.svg" > "$TEMP_RENDER_MANIFEST"

  SOURCE_MANIFEST="$TEMP_SOURCE_MANIFEST"
  RENDER_MANIFEST="$TEMP_RENDER_MANIFEST"
  log "Single-diagram scope enabled: $DIAGRAM_PATH"
  return 0
}

run_lint_check() {
  if [[ -n "$DIAGRAM_PATH" ]]; then
    python3 "$REPO_ROOT/scripts/diagrams/lint_diagrams.py" "$REPO_ROOT/$DIAGRAM_PATH"
  else
    python3 "$REPO_ROOT/scripts/diagrams/lint_diagrams.py" "$DIAGRAM_ROOT"
  fi
  return 0
}

run_operator_guard() {
  if [[ -n "$DIAGRAM_PATH" ]]; then
    python3 "$REPO_ROOT/scripts/diagrams/fix_mermaid_operators.py" \
      --check "$REPO_ROOT/$DIAGRAM_PATH"
  else
    python3 "$REPO_ROOT/scripts/diagrams/fix_mermaid_operators.py" \
      --check "$DIAGRAM_ROOT"
  fi
  return 0
}

run_render_step() {
  if [[ -n "$DIAGRAM_PATH" ]]; then
    local diagram_dir
    local diagram_stem
    diagram_dir="$(dirname "$DIAGRAM_PATH")"
    diagram_stem="$(basename "${DIAGRAM_PATH%.*}")"
    bash "$DIAGRAM_RENDER_SCRIPT" \
      --dir "$REPO_ROOT/$diagram_dir" \
      --filter "$diagram_stem" \
      --text-layer "$TEXT_LAYER" \
      --puppeteer "$PUPPETEER_CFG"
  else
    bash "$DIAGRAM_RENDER_SCRIPT" \
      --text-layer "$TEXT_LAYER" \
      --puppeteer "$PUPPETEER_CFG"
  fi
  return 0
}

run_class_method_integrity_check() {
  local class_source_dir="$DIAGRAM_CLASS_SOURCE_DIR"
  local class_svg_dir="$DIAGRAM_CLASS_SVG_DIR"

  if [[ -n "$DIAGRAM_PATH" ]]; then
    case "$DIAGRAM_PATH" in
      "${DIAGRAM_ROOT_REL}/class-diagrams/"*.mmd)
        python3 "$REPO_ROOT/scripts/diagrams/check_class_method_render_integrity.py" \
          --source-dir "$class_source_dir" \
          --svg-dir "$class_svg_dir" \
          --file "$REPO_ROOT/$DIAGRAM_PATH"
        ;;
      *)
        log "DIAG-T033: class method integrity skipped (non class-diagram scope)"
        return 0
        ;;
    esac
    return 0
  fi

  python3 "$REPO_ROOT/scripts/diagrams/check_class_method_render_integrity.py" \
    --source-dir "$class_source_dir" \
    --svg-dir "$class_svg_dir"
  return 0
}

run_budget_enforcement() {
  local mode="$1"
  local cmd=(
    python3 "$REPO_ROOT/scripts/diagrams/enforce_diagram_quality_budget.py"
    --mode "$mode"
    --quality-report "$BUDGET_QUALITY_JSON"
    --lint-report "$BUDGET_LINT_JSON"
    --max-hard-failures 0
    --max-diag-t022 0
    --max-diag-t023 0
    --max-lint-errors 0
  )

  if [[ "$mode" == "nightly" ]]; then
    cmd+=(
      --nightly-report "$BUDGET_NIGHTLY_JSON"
      --max-nightly-errors 0
      --max-nightly-warnings 0
    )
  fi

  "${cmd[@]}"
  return 0
}

run_pr_profile() {
  log "DIAG-T000: Mermaid operator guard (class/sequence)"
  run_operator_guard

  log "DIAG-T001: Mermaid syntax"
  run_syntax_check

  log "DIAG-T002..T008: Diagram lint"
  run_lint_check

  if [[ "$SKIP_RENDER" -eq 0 ]]; then
    log "DIAG-T009: Render diagrams"
    run_render_step
  else
    log "Render skipped (--skip-render)"
  fi

  log "DIAG-T010..T012: Artifact existence/non-empty"
  python3 "$REPO_ROOT/scripts/diagrams/check_diagram_artifacts.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T014..T015: SVG text visibility"
  python3 "$REPO_ROOT/scripts/diagrams/check_svg_text_visibility.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T013/DIAG-T026: Visual smoke drift"
  python3 "$REPO_ROOT/scripts/diagrams/check_diagram_visual_smoke.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T018..T023: Quality gates"
  if [[ "$ENFORCE_BUDGET" -eq 1 ]]; then
    local lint_target="$DIAGRAM_ROOT"
    if [[ -n "$DIAGRAM_PATH" ]]; then
      lint_target="$REPO_ROOT/$DIAGRAM_PATH"
    fi
    if [[ -z "$BUDGET_TMP_DIR" ]]; then
      BUDGET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/diagram-budget.XXXXXX")"
    fi
    BUDGET_QUALITY_JSON="$BUDGET_TMP_DIR/quality.json"
    BUDGET_LINT_JSON="$BUDGET_TMP_DIR/lint.json"

    python3 "$REPO_ROOT/scripts/diagrams/check_diagram_quality_gates.py" \
      --manifest "$SOURCE_MANIFEST" \
      --json-out "$BUDGET_QUALITY_JSON"
    python3 "$REPO_ROOT/scripts/diagrams/lint_diagrams.py" \
      "$lint_target" --json > "$BUDGET_LINT_JSON" || true

    log "DIAG-BUDGET: Enforce PR budget"
    run_budget_enforcement pr
  else
    python3 "$REPO_ROOT/scripts/diagrams/check_diagram_quality_gates.py" \
      --manifest "$SOURCE_MANIFEST"
  fi

  log "DIAG-T033: class method render integrity"
  run_class_method_integrity_check
  return 0
}

run_nightly_profile() {
  local nightly_cmd
  run_pr_profile

  log "DIAG-T024..T029: Nightly suite"
  nightly_cmd=(
    python3 "$REPO_ROOT/scripts/diagrams/run_diagram_nightly_suite.py"
    --source-manifest "$SOURCE_MANIFEST"
    --render-manifest "$RENDER_MANIFEST"
    --puppeteer "$PUPPETEER_CFG"
  )

  if [[ "$ENFORCE_BUDGET" -eq 1 ]]; then
    if [[ -z "$BUDGET_TMP_DIR" ]]; then
      BUDGET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/diagram-budget.XXXXXX")"
    fi
    BUDGET_NIGHTLY_JSON="$BUDGET_TMP_DIR/nightly.json"
    nightly_cmd+=(--json-out "$BUDGET_NIGHTLY_JSON")
  fi

  if [[ "$STRICT_NIGHTLY" -eq 1 ]]; then
    nightly_cmd+=(--strict)
  fi

  "${nightly_cmd[@]}"

  if [[ "$ENFORCE_BUDGET" -eq 1 ]]; then
    log "DIAG-BUDGET: Enforce nightly budget"
    run_budget_enforcement nightly
  fi
  return 0
}

run_quick_profile() {
  log "Quick profile: syntax + lint + quality + nightly (light)"

  log "DIAG-T000: Mermaid operator guard (class/sequence)"
  run_operator_guard

  log "DIAG-T001: Mermaid syntax"
  run_syntax_check

  log "DIAG-T002..T008: Diagram lint"
  run_lint_check

  log "DIAG-T018..T023: Quality gates"
  if [[ "$ENFORCE_BUDGET" -eq 1 ]]; then
    local lint_target="$DIAGRAM_ROOT"
    if [[ -n "$DIAGRAM_PATH" ]]; then
      lint_target="$REPO_ROOT/$DIAGRAM_PATH"
    fi
    if [[ -z "$BUDGET_TMP_DIR" ]]; then
      BUDGET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/diagram-budget.XXXXXX")"
    fi
    BUDGET_QUALITY_JSON="$BUDGET_TMP_DIR/quality.json"
    BUDGET_LINT_JSON="$BUDGET_TMP_DIR/lint.json"
    python3 "$REPO_ROOT/scripts/diagrams/check_diagram_quality_gates.py" \
      --manifest "$SOURCE_MANIFEST" \
      --json-out "$BUDGET_QUALITY_JSON"
    python3 "$REPO_ROOT/scripts/diagrams/lint_diagrams.py" \
      "$lint_target" --json > "$BUDGET_LINT_JSON" || true

    log "DIAG-BUDGET: Enforce quick-profile PR budget"
    run_budget_enforcement pr
  else
    python3 "$REPO_ROOT/scripts/diagrams/check_diagram_quality_gates.py" \
      --manifest "$SOURCE_MANIFEST"
  fi

  log "DIAG-T024..T029: Nightly suite (light mode)"
  python3 "$REPO_ROOT/scripts/diagrams/run_diagram_nightly_suite.py" \
    --source-manifest "$SOURCE_MANIFEST" \
    --render-manifest "$RENDER_MANIFEST" \
    --skip-chaos --skip-growth --skip-theme
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -lt 2 ]] && { echo "--profile requires value" >&2; exit 2; }
      PROFILE="$2"
      shift 2
      ;;
    --diagram)
      [[ $# -lt 2 ]] && { echo "--diagram requires value" >&2; exit 2; }
      DIAGRAM_PATH="$2"
      shift 2
      ;;
    --puppeteer)
      [[ $# -lt 2 ]] && { echo "--puppeteer requires value" >&2; exit 2; }
      PUPPETEER_CFG="$2"
      shift 2
      ;;
    --refresh-puppeteer-config)
      FORCE_WRITE_PUPPETEER=1
      shift
      ;;
    --text-layer)
      [[ $# -lt 2 ]] && { echo "--text-layer requires value" >&2; exit 2; }
      TEXT_LAYER="$2"
      shift 2
      ;;
    --strict-nightly)
      STRICT_NIGHTLY=1
      shift
      ;;
    --enforce-budget)
      ENFORCE_BUDGET=1
      shift
      ;;
    --skip-render)
      SKIP_RENDER=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

case "$TEXT_LAYER" in
  dual|fo-only|fallback-only) ;;
  *)
    echo "--text-layer must be one of: dual|fo-only|fallback-only" >&2
    exit 2
    ;;
esac

if [[ -n "$DIAGRAM_PATH" ]]; then
  prepare_diagram_scope "$DIAGRAM_PATH"
fi

ensure_puppeteer_config
validate_puppeteer_config
run_puppeteer_preflight

case "$PROFILE" in
  pr)      run_pr_profile ;;
  nightly) run_nightly_profile ;;
  quick)   run_quick_profile ;;
  *)
    echo "Unsupported profile: $PROFILE" >&2
    usage
    exit 2
    ;;
esac

log "Diagram checks completed (profile=$PROFILE)"
