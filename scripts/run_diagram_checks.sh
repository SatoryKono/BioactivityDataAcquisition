#!/usr/bin/env bash
# Unified runner for diagram validation suites.
# Profiles:
#   pr      - hard-gate PR checks (syntax/lint/render/artifacts/smoke/quality)
#   nightly - pr profile + nightly DIAG-T024..T029 suite
#   quick   - lightweight local checks without render
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="pr"
PUPPETEER_CFG="${PUPPETEER_CFG:-/tmp/puppeteer-config.json}"
STRICT_NIGHTLY=0
SKIP_RENDER=0
DIAGRAM_PATH=""
SOURCE_MANIFEST="$REPO_ROOT/docs/02-architecture/mmd-diagrams/quality-gate-manifest.txt"
RENDER_MANIFEST="$REPO_ROOT/docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt"
TEMP_SOURCE_MANIFEST=""
TEMP_RENDER_MANIFEST=""
THEME_CONFIG="$REPO_ROOT/docs/02-architecture/mmd-diagrams/theme/mermaid-config.json"

usage() {
  cat <<'EOF'
Usage: scripts/run_diagram_checks.sh [options]

Options:
  --profile <pr|nightly|quick>   Check profile (default: pr)
  --diagram <path>               Run checks only for one .mmd/.mermaid diagram
  --puppeteer <path>             Puppeteer config path (default: /tmp/puppeteer-config.json)
  --strict-nightly               Fail nightly profile on warnings
  --skip-render                  Skip render step (useful for local dry loops)
  -h, --help                     Show this help

Examples:
  scripts/run_diagram_checks.sh --profile pr
  scripts/run_diagram_checks.sh --profile pr --diagram docs/02-architecture/mmd-diagrams/foundation/30-port-adapter-mapping.mmd
  scripts/run_diagram_checks.sh --profile nightly --strict-nightly
  scripts/run_diagram_checks.sh --profile quick
EOF
}

log() { printf '[INFO] %s\n' "$*"; }

cleanup_temp_manifests() {
  [[ -n "$TEMP_SOURCE_MANIFEST" ]] && rm -f "$TEMP_SOURCE_MANIFEST" || true
  [[ -n "$TEMP_RENDER_MANIFEST" ]] && rm -f "$TEMP_RENDER_MANIFEST" || true
}

trap cleanup_temp_manifests EXIT

ensure_puppeteer_config() {
  cat > "$PUPPETEER_CFG" <<'EOF'
{
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
}
EOF
}

run_syntax_check() {
  if [[ -z "$DIAGRAM_PATH" ]]; then
    bash "$REPO_ROOT/scripts/validate_mermaid_syntax.sh" --puppeteer "$PUPPETEER_CFG"
    return
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
    if ! mmdc -i "$source_abs" -o "$tmp_svg" "${mmdc_args[@]}" >/dev/null 2>"$tmp_err"; then
      echo "ERROR: Mermaid validation failed for $DIAGRAM_PATH" >&2
      if grep -q "Could not find Chrome" "$tmp_err"; then
        echo "HINT: mmdc could not find Chrome/Chromium for Puppeteer." >&2
      fi
      sed -n '1,8p' "$tmp_err" >&2 || true
      rm -f "$tmp_svg" "$tmp_err"
      exit 1
    fi
  fi

  rm -f "$tmp_svg" "$tmp_err"
  log "Syntax validation passed for $DIAGRAM_PATH"
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
}

run_lint_check() {
  if [[ -n "$DIAGRAM_PATH" ]]; then
    python3 "$REPO_ROOT/scripts/lint_diagrams.py" "$REPO_ROOT/$DIAGRAM_PATH"
  else
    python3 "$REPO_ROOT/scripts/lint_diagrams.py" "$REPO_ROOT/docs/02-architecture/mmd-diagrams"
  fi
}

run_render_step() {
  if [[ -n "$DIAGRAM_PATH" ]]; then
    local diagram_dir
    local diagram_stem
    diagram_dir="$(dirname "$DIAGRAM_PATH")"
    diagram_stem="$(basename "${DIAGRAM_PATH%.*}")"
    bash "$REPO_ROOT/docs/02-architecture/mmd-diagrams/render.sh" \
      --dir "$REPO_ROOT/$diagram_dir" \
      --filter "$diagram_stem" \
      --puppeteer "$PUPPETEER_CFG"
  else
    bash "$REPO_ROOT/docs/02-architecture/mmd-diagrams/render.sh" --puppeteer "$PUPPETEER_CFG"
  fi
}

run_pr_profile() {
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
  python3 "$REPO_ROOT/scripts/check_diagram_artifacts.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T014..T015: SVG text visibility"
  python3 "$REPO_ROOT/scripts/check_svg_text_visibility.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T013/DIAG-T026: Visual smoke drift"
  python3 "$REPO_ROOT/scripts/check_diagram_visual_smoke.py" \
    --manifest "$RENDER_MANIFEST"

  log "DIAG-T018..T023: Quality gates"
  python3 "$REPO_ROOT/scripts/check_diagram_quality_gates.py" \
    --manifest "$SOURCE_MANIFEST"
}

run_nightly_profile() {
  run_pr_profile

  log "DIAG-T024..T029: Nightly suite"
  nightly_cmd=(
    python3 "$REPO_ROOT/scripts/run_diagram_nightly_suite.py"
    --source-manifest "$SOURCE_MANIFEST"
    --render-manifest "$RENDER_MANIFEST"
    --puppeteer "$PUPPETEER_CFG"
  )

  if [[ "$STRICT_NIGHTLY" -eq 1 ]]; then
    nightly_cmd+=(--strict)
  fi

  "${nightly_cmd[@]}"
}

run_quick_profile() {
  log "Quick profile: syntax + lint + quality + nightly (light)"

  log "DIAG-T001: Mermaid syntax"
  run_syntax_check

  log "DIAG-T002..T008: Diagram lint"
  run_lint_check

  log "DIAG-T018..T023: Quality gates"
  python3 "$REPO_ROOT/scripts/check_diagram_quality_gates.py" \
    --manifest "$SOURCE_MANIFEST"

  log "DIAG-T024..T029: Nightly suite (light mode)"
  python3 "$REPO_ROOT/scripts/run_diagram_nightly_suite.py" \
    --source-manifest "$SOURCE_MANIFEST" \
    --render-manifest "$RENDER_MANIFEST" \
    --skip-chaos --skip-growth --skip-theme
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
    --strict-nightly)
      STRICT_NIGHTLY=1
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

if [[ -n "$DIAGRAM_PATH" ]]; then
  prepare_diagram_scope "$DIAGRAM_PATH"
fi

ensure_puppeteer_config

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
