#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
PRESERVE_PYTEST_CACHE="${BIOETL_PREFLIGHT_PRESERVE_PYTEST_CACHE:-0}"
DETAIL_LIMIT="${BIOETL_PREFLIGHT_DETAIL_LIMIT:-25}"
COMPUTE_SIZE="${BIOETL_PREFLIGHT_COMPUTE_SIZE:-0}"
INCLUDE_LOCAL_CACHE_ROOTS="${BIOETL_PREFLIGHT_INCLUDE_LOCAL_CACHE_ROOTS:-0}"
INCLUDE_LOCAL_VENDOR="${BIOETL_PREFLIGHT_INCLUDE_LOCAL_VENDOR:-0}"
ALLOW_SLOW_FS_DELETE="${BIOETL_PREFLIGHT_ALLOW_SLOW_FS_DELETE:-0}"
SLOW_FS="${BIOETL_PREFLIGHT_SLOW_FS:-auto}"
SLOW_FS_MAX_TARGETS="${BIOETL_PREFLIGHT_SLOW_FS_MAX_TARGETS:-50}"

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=true
      ;;
    --include-local-cache-roots)
      INCLUDE_LOCAL_CACHE_ROOTS=1
      ;;
    --include-local-vendor)
      INCLUDE_LOCAL_VENDOR=1
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/engineering/repo/preflight_cleanup.sh [--dry-run] [--include-local-cache-roots] [--include-local-vendor]

Removes common Python/build/cache artifacts before release checks.

Options:
  --dry-run                    Show what would be deleted and report counts/sizes.
  --include-local-cache-roots  Also remove reviewed local cache roots such as
                               .cache/, .import_linter_cache/, .npm-cache/, and
                               .coverage-sharded-current-main/.
  --include-local-vendor       Also remove reviewed local vendor/editor roots such
                               as .junie/, .qodo/, .sonarlint/, and .windsurf/.
Environment:
  BIOETL_PREFLIGHT_ALLOW_SLOW_FS_DELETE=1
                               Allow large cleanup deletes on WSL /mnt checkouts.
  BIOETL_PREFLIGHT_SLOW_FS=0|1|auto
                               Override slow filesystem detection.
  BIOETL_PREFLIGHT_SLOW_FS_MAX_TARGETS=N
                               Max targets before slow-FS cleanup is skipped.
  -h, --help                   Show this help message.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

format_bytes() {
  local bytes="$1"
  if (( bytes < 1024 )); then
    printf '%s B' "$bytes"
  elif (( bytes < 1024 * 1024 )); then
    awk -v b="$bytes" 'BEGIN { printf "%.2f KiB", b/1024 }'
  elif (( bytes < 1024 * 1024 * 1024 )); then
    awk -v b="$bytes" 'BEGIN { printf "%.2f MiB", b/1024/1024 }'
  else
    awk -v b="$bytes" 'BEGIN { printf "%.2f GiB", b/1024/1024/1024 }'
  fi
  return 0
}

safe_dir_size_bytes() {
  local path="$1"
  local size=""
  if size="$(du -sb -- "$path" 2>/dev/null | awk 'NR == 1 { print $1 }')" && [[ "$size" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$size"
    return 0
  fi
  printf '0\n'
}

safe_file_size_bytes() {
  local path="$1"
  local size=""
  if size="$(stat -c%s -- "$path" 2>/dev/null)" && [[ "$size" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$size"
    return 0
  fi
  printf '0\n'
}

is_wsl_runtime() {
  if [[ -r /proc/version ]] && grep -qiE 'microsoft|wsl' /proc/version; then
    return 0
  fi
  return 1
}

is_slow_fs_checkout() {
  case "$SLOW_FS" in
    1|true|TRUE|yes|YES)
      return 0
      ;;
    0|false|FALSE|no|NO)
      return 1
      ;;
    auto|"")
      ;;
    *)
      echo "[preflight_cleanup][warn] Unsupported BIOETL_PREFLIGHT_SLOW_FS=$SLOW_FS; using auto detection" >&2
      ;;
  esac

  is_wsl_runtime || return 1
  case "$(pwd -P)" in
    /mnt/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

print_limited_list() {
  local label="$1"
  shift
  local items=("$@")
  local total="${#items[@]}"
  if (( total == 0 )); then
    return 0
  fi
  echo "$label"
  local visible="$DETAIL_LIMIT"
  if (( visible < 0 )); then
    visible=0
  fi
  if (( visible > total )); then
    visible="$total"
  fi
  local index=0
  while (( index < visible )); do
    printf '  %s\n' "${items[$index]}"
    index=$((index + 1))
  done
  if (( total > visible )); then
    printf '  ... %s additional target(s) omitted\n' "$((total - visible))"
  fi
  return 0
}

FIND_ROOTS=(.)
EXCLUDE_DIRS=(
  ai
  .benchmarks
  .cache
  .codex
  .codex_tmp
  .coverage-sharded
  .cursor
  .gemini
  .git
  .hypothesis
  .venv
  .venv-docs
  .venv-win
  .venv-win-corrupt
  .mypy_cache
  .python-user
  .pytest_cache
  .ruff_cache
  .vibe
  .idea
  .vscode
  .worktrees
  .mkdocs-site-check
  .mkdocs-site-check-2
  .mkdocs-site-verify
  .mkdocs-site-verify-3
  assets
  data
  logs
  node_modules
  output
  reports
  site
  tmp
)

PROTECTED_BUILD_DIRS=(
  ./scripts/docs/build
)
SAFE_LOCAL_ROOT_DIRS=(
  .benchmarks
  .hypothesis
)
OPTIONAL_LOCAL_CACHE_ROOTS=(
  .cache
  .coverage-sharded-current-main
  .import_linter_cache
  .npm-cache
)
OPTIONAL_LOCAL_VENDOR_ROOTS=(
  .junie
  .qodo
  .sonarlint
  .windsurf
)

build_find_prune() {
  local expr=()
  expr+=( '(' )
  local first=true
  for d in "${EXCLUDE_DIRS[@]}"; do
    if [[ "$first" == false ]]; then
      expr+=( -o )
    fi
    expr+=( -name "$d" )
    first=false
  done
  expr+=( ')' -prune -o )
  printf '%s\n' "${expr[@]}"
  return 0
}

mapfile -t PRUNE_EXPR < <(build_find_prune)

mapfile -t DIR_TARGETS < <(
  find "${FIND_ROOTS[@]}" "${PRUNE_EXPR[@]}" -type d \( -name '__pycache__' -o -name '*.egg-info' -o -name 'build' -o -name 'dist' -o -name 'htmlcov' \) -print 2>/dev/null | sort -u
)

mapfile -t FILE_TARGETS < <(
  find "${FIND_ROOTS[@]}" "${PRUNE_EXPR[@]}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.coverage' -o -name '.coverage.*' -o -name 'coverage.xml' -o -name '*.log' -o -name 'pytestdebug.log' \) -print 2>/dev/null | sort -u
)

# Add cache directories explicitly in case they were pruned
for cache_dir in .pytest_cache .mypy_cache .ruff_cache "${SAFE_LOCAL_ROOT_DIRS[@]}"; do
  if [[ "$cache_dir" == ".pytest_cache" && "$PRESERVE_PYTEST_CACHE" == "1" ]]; then
    continue
  fi
  if [[ -d "$cache_dir" ]]; then
    DIR_TARGETS+=("./$cache_dir")
  fi
done

if [[ "$INCLUDE_LOCAL_CACHE_ROOTS" == "1" ]]; then
  for cache_dir in "${OPTIONAL_LOCAL_CACHE_ROOTS[@]}"; do
    if [[ -d "$cache_dir" ]]; then
      DIR_TARGETS+=("./$cache_dir")
    fi
  done
fi

if [[ "$INCLUDE_LOCAL_VENDOR" == "1" ]]; then
  for vendor_dir in "${OPTIONAL_LOCAL_VENDOR_ROOTS[@]}"; do
    if [[ -d "$vendor_dir" ]]; then
      DIR_TARGETS+=("./$vendor_dir")
    fi
  done
fi

if (( ${#DIR_TARGETS[@]} > 0 )); then
  mapfile -t DIR_TARGETS < <(printf '%s\n' "${DIR_TARGETS[@]}" | sort -u)
fi

if (( ${#DIR_TARGETS[@]} > 0 )) && (( ${#PROTECTED_BUILD_DIRS[@]} > 0 )); then
  protected_regex="$(printf '%s\n' "${PROTECTED_BUILD_DIRS[@]}" | sed 's/[.[\*^$()+?{}|]/\\&/g' | paste -sd'|' -)"
  mapfile -t DIR_TARGETS < <(
    printf '%s\n' "${DIR_TARGETS[@]}" | rg -v "^(${protected_regex})$"
  )
fi

total_targets=$(( ${#DIR_TARGETS[@]} + ${#FILE_TARGETS[@]} ))
total_size_bytes=0
size_summary="skipped (set BIOETL_PREFLIGHT_COMPUTE_SIZE=1 to compute)"

if [[ "$DRY_RUN" == "true" && "$COMPUTE_SIZE" == "1" ]]; then
  dir_size_bytes=0
  for path in "${DIR_TARGETS[@]}"; do
    size="$(safe_dir_size_bytes "$path")"
    dir_size_bytes=$((dir_size_bytes + size))
  done

  file_size_bytes=0
  for path in "${FILE_TARGETS[@]}"; do
    size="$(safe_file_size_bytes "$path")"
    file_size_bytes=$((file_size_bytes + size))
  done

  total_size_bytes=$(( dir_size_bytes + file_size_bytes ))
  size_summary="$(format_bytes "$total_size_bytes") (${total_size_bytes} bytes)"
elif [[ "$DRY_RUN" != "true" ]]; then
  size_summary="skipped (non-dry-run)"
fi

echo "Preflight cleanup targets:"
echo "  Directories: ${#DIR_TARGETS[@]}"
echo "  Files:       ${#FILE_TARGETS[@]}"
echo "  Total:       ${total_targets}"
echo "  Size:        ${size_summary}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo
  echo "[dry-run] No files were deleted."
  print_limited_list "[dry-run] Directories to remove:" "${DIR_TARGETS[@]}"
  print_limited_list "[dry-run] Files to remove:" "${FILE_TARGETS[@]}"
  exit 0
fi

if is_slow_fs_checkout \
  && [[ "$ALLOW_SLOW_FS_DELETE" != "1" ]] \
  && [[ "$SLOW_FS_MAX_TARGETS" =~ ^[0-9]+$ ]] \
  && (( total_targets > SLOW_FS_MAX_TARGETS )); then
  echo "[preflight_cleanup][warn] Skipped cleanup on slow WSL mount: ${total_targets} targets exceed BIOETL_PREFLIGHT_SLOW_FS_MAX_TARGETS=${SLOW_FS_MAX_TARGETS}."
  echo "[preflight_cleanup][warn] Re-run with BIOETL_PREFLIGHT_ALLOW_SLOW_FS_DELETE=1 for explicit cleanup."
  exit 0
fi

if (( ${#DIR_TARGETS[@]} > 0 )) && ! rm -rf -- "${DIR_TARGETS[@]}" 2>/dev/null; then
  for path in "${DIR_TARGETS[@]}"; do
    if ! rm -rf -- "$path" 2>/dev/null; then
      echo "[preflight_cleanup][warn] Could not remove directory: $path" >&2
    fi
  done
fi

if (( ${#FILE_TARGETS[@]} > 0 )); then
  for path in "${FILE_TARGETS[@]}"; do
    if ! rm -f -- "$path" 2>/dev/null; then
      echo "[preflight_cleanup][warn] Could not remove file: $path" >&2
    fi
  done
fi

echo "Cleanup complete. Removed ${total_targets} targets."
