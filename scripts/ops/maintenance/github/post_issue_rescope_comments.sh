#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="${SCRIPT_DIR}/update_github_issue.sh"
DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/post_issue_rescope_comments.sh [--apply] [--owner NAME] [--repo NAME] [--issue NUMBER]...

Options:
  --apply        Send comments to GitHub. Default mode is dry-run.
  --owner NAME   Repository owner (default: SatoryKono)
  --repo NAME    Repository name (default: BioactivityDataAcquisition)
  --issue NUM    Restrict to one issue number; may be repeated.
  -h, --help     Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Required only with --apply

Behavior:
  - posts prepared re-scope comments for issue(s) #2600, #2516, #2515, #2511
  - uses dry-run by default so the payload can be reviewed safely first

Examples:
  bash scripts/ops/maintenance/post_issue_rescope_comments.sh
  bash scripts/ops/maintenance/post_issue_rescope_comments.sh --issue 2600 --issue 2516
  GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/ops/maintenance/post_issue_rescope_comments.sh --apply
EOF
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
APPLY=0
declare -a REQUESTED_ISSUES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --issue)
      REQUESTED_ISSUES+=("${2:-}")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$UPDATE_SCRIPT" ]]; then
  printf '[FAIL] Missing helper script: %s\n' "$UPDATE_SCRIPT" >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cat >"$tmpdir/2600.md" <<'EOF'
Предлагаю re-scope issue, потому что текущее описание уже частично расходится с реализованной control-plane поверхностью.

Что уже есть в коде:
- `RunManifest` уже реализован как immutable control-plane artifact в `src/bioetl/domain/control_plane/run_manifest.py`
- `RunLedgerEntry` и replay helpers уже есть в `src/bioetl/domain/control_plane/run_ledger.py`
- file-backed stores уже существуют в `src/bioetl/infrastructure/control_plane/file_run_manifest_store.py` и `src/bioetl/infrastructure/control_plane/file_run_ledger_store.py`
- inspection/runtime surface уже поддержан через `run_manifest_service`, `run_ledger_service`, CLI и published contract docs

Что важно:
- текущая архитектура прямо фиксирует, что `RunManifest` не заменяет `PipelineRunContext` / `PipelineContext`
- значит issue уже не про “introduce RunManifest & RunLedger from scratch” и не про “one universal execution contract”

Предлагаю обновить scope так:
- довести существующую control-plane модель до полностью согласованного replay/resume contract
- закрыть remaining gaps между checkpoint snapshot и ledger replay
- унифицировать stage/event taxonomy для ordinary + composite paths
- убрать остаточные места, где runtime correlation anchors живут вне manifest/ledger surface
- явно зафиксировать boundary: runtime contexts остаются runtime contexts, manifest/ledger остаются provenance/control-plane artifacts

Suggested updated goal:
`Finish RunManifest/RunLedger replay model and checkpoint integration without collapsing runtime contexts into a universal manifest object.`

Suggested acceptance criteria:
- [ ] ordinary and composite runners emit canonical lifecycle events into ledger
- [ ] replay semantics for checkpoint resume are documented and covered by tests
- [ ] no new execution path bypasses manifest/ledger when control-plane is enabled
- [ ] stage/event taxonomy is stable and consistent across runners
- [ ] docs reflect the actual split between runtime context and control-plane artifacts
EOF

cat >"$tmpdir/2516.md" <<'EOF'
Предлагаю re-scope issue под текущую repo reality.

Что уже есть:
- workflow `Schema Governance` уже существует в `.github/workflows/schema-governance.yml`
- blocking checks на generated artifacts, contract imports и schema parity уже есть
- `src/tools/verify_schema_parity.py` уже сравнивает Silver ↔ Gold и использует baseline для известных расхождений
- representative silver schema drift gate уже встроен в CI

Что пока не выглядит закрытым:
- явная Gold compatibility classification по правилам ADR-036
- readable diff именно в терминах compatible vs breaking
- maintainable baseline именно для Gold contract compatibility rules
- policy path для intentional approved breaking changes

Предлагаю обновить issue так, чтобы он был не про “создать schema governance с нуля”, а про следующий конкретный шаг.

Suggested updated goal:
`Add explicit Gold compatibility classification on top of existing schema-governance gates.`

Suggested scope:
- build a Gold-focused compatibility checker on top of existing schema governance
- classify changes using explicit ADR-036 rules
- emit human-readable diagnostics for compatible vs breaking changes
- fail CI only on breaking Gold contract changes

Suggested acceptance criteria:
- [ ] adding nullable columns is classified as compatible
- [ ] removing/renaming columns is classified as breaking
- [ ] narrowing types is classified as breaking
- [ ] changing nullable -> non-nullable is classified as breaking
- [ ] CI output explains the exact Gold contract diff in human-readable form
- [ ] approved extension path is documented for new rules
EOF

cat >"$tmpdir/2515.md" <<'EOF'
Предлагаю re-scope issue, потому что lineage MVP в репозитории уже частично реализован.

Что уже есть:
- domain lineage model under `src/bioetl/domain/lineage/`
- file-backed lineage store in `src/bioetl/infrastructure/control_plane/file_lineage_store.py`
- lineage fragment builders in `src/bioetl/application/services/metadata_lineage_fragments_*.py`
- CLI inspection surface in `src/bioetl/interfaces/cli/commands/lineage.py`
- manifest/ledger diagnostics уже ссылаются на lineage anchors

То есть issue уже не про “introduce lineage metadata MVP from zero”.

Что остаётся актуальным:
- проверить, какие Bronze -> Silver -> Gold flows действительно покрыты end-to-end
- закрыть gaps в propagation и canonical refs
- зафиксировать supported trace/debug path как normative repo behavior
- добить tests/docs для supported lineage workflow

Suggested updated goal:
`Complete and standardize the existing lineage MVP for representative Bronze -> Silver -> Gold flows.`

Suggested updated acceptance criteria:
- [ ] at least one representative Bronze -> Silver -> Gold family is covered end-to-end
- [ ] lineage refs are persisted and queryable through the supported inspection surface
- [ ] one documented trace/debug path exists from output artifact/dataset back to run context
- [ ] tests verify propagation and lookup for the supported flows
- [ ] docs clearly define what is supported now vs future lineage expansion
EOF

cat >"$tmpdir/2511.md" <<'EOF'
Предлагаю formally keep this issue as a meta-roadmap and stop treating it as a direct implementation ticket.

Почему:
- часть roadmap уже распилена на executable child issues
- integration/VCR policy и provider contract drift уже вынесены в отдельные задачи
- schema drift subtrack тоже уже выделялся отдельно
- therefore this issue is now most useful as a parent tracker, not as a single deliverable

Suggested updated purpose:
`Parent roadmap for testing governance tracks; execution happens in child issues.`

Suggested checklist rewrite:
- [ ] Unit standards track has an executable child issue or completed implementation note
- [ ] Integration/VCR policy track is tracked in a child issue
- [ ] Contract drift track is tracked in a child issue
- [ ] Data validation gates track is tracked in a child issue
- [ ] Parent issue links current child issues and marks completed ones
- [ ] Parent body states which parts are roadmap only vs active implementation

Suggested note to add:
This issue should remain open only as a coordination/meta artifact. Concrete implementation work should happen in scoped child issues with explicit acceptance criteria and smaller blast radius.
EOF

comment_file_for_issue() {
  case "$1" in
    2600|2516|2515|2511)
      printf '%s/%s.md\n' "$tmpdir" "$1"
      ;;
    *)
      printf ''
      ;;
  esac
}

declare -a TARGET_ISSUES
if [[ "${#REQUESTED_ISSUES[@]}" -eq 0 ]]; then
  TARGET_ISSUES=(2600 2516 2515 2511)
else
  TARGET_ISSUES=("${REQUESTED_ISSUES[@]}")
fi

for issue in "${TARGET_ISSUES[@]}"; do
  case "$issue" in
    2600|2516|2515|2511)
      ;;
    *)
      printf '[FAIL] Unsupported issue number: %s\n' "$issue" >&2
      printf 'Supported issues: 2600, 2516, 2515, 2511\n' >&2
      exit 2
      ;;
  esac
done

for issue in "${TARGET_ISSUES[@]}"; do
  comment_file="$(comment_file_for_issue "$issue")"
  printf '[INFO] Preparing re-scope comment for issue #%s in %s/%s\n' \
    "$issue" "$OWNER" "$REPO"

  args=(
    --issue "$issue"
    --owner "$OWNER"
    --repo "$REPO"
    --comment-file "$comment_file"
  )
  if [[ "$APPLY" -eq 0 ]]; then
    args+=(--dry-run)
  fi

  bash "$UPDATE_SCRIPT" "${args[@]}"
  printf '\n'
done

printf '[INFO] Prepared %s re-scope comment(s).\n' "${#TARGET_ISSUES[@]}"
