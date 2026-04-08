#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
PRESERVE_PYTEST_CACHE="${BIOETL_PREFLIGHT_PRESERVE_PYTEST_CACHE:-0}"

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/preflight_cleanup.sh [--dry-run]

Removes common Python/build/cache artifacts before release checks.

Options:
  --dry-run    Show what would be deleted and report counts/sizes.
  -h, --help   Show this help message.
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

FIND_ROOTS=(.)
EXCLUDE_DIRS=(.git .venv .mypy_cache .pytest_cache .ruff_cache data .idea .vscode)

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
}

mapfile -t PRUNE_EXPR < <(build_find_prune)

mapfile -t DIR_TARGETS < <(
  find "${FIND_ROOTS[@]}" "${PRUNE_EXPR[@]}" -type d \( -name '__pycache__' -o -name '*.egg-info' -o -name 'build' -o -name 'dist' -o -name 'htmlcov' \) -print 2>/dev/null | sort -u
)

mapfile -t FILE_TARGETS < <(
  find "${FIND_ROOTS[@]}" "${PRUNE_EXPR[@]}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.coverage' -o -name '.coverage.*' -o -name 'coverage.xml' -o -name '*.log' -o -name 'pytestdebug.log' \) -print 2>/dev/null | sort -u
)

# Add cache directories explicitly in case they were pruned
for cache_dir in .pytest_cache .mypy_cache .ruff_cache; do
  if [[ "$cache_dir" == ".pytest_cache" && "$PRESERVE_PYTEST_CACHE" == "1" ]]; then
    continue
  fi
  if [[ -d "$cache_dir" ]]; then
    DIR_TARGETS+=("./$cache_dir")
  fi
done

if (( ${#DIR_TARGETS[@]} > 0 )); then
  mapfile -t DIR_TARGETS < <(printf '%s\n' "${DIR_TARGETS[@]}" | sort -u)
fi

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

total_targets=$(( ${#DIR_TARGETS[@]} + ${#FILE_TARGETS[@]} ))
total_size_bytes=$(( dir_size_bytes + file_size_bytes ))

echo "Preflight cleanup targets:"
echo "  Directories: ${#DIR_TARGETS[@]}"
echo "  Files:       ${#FILE_TARGETS[@]}"
echo "  Total:       ${total_targets}"
echo "  Size:        $(format_bytes "$total_size_bytes") (${total_size_bytes} bytes)"

if [[ "$DRY_RUN" == "true" ]]; then
  echo
  echo "[dry-run] No files were deleted."
  if (( ${#DIR_TARGETS[@]} > 0 )); then
    echo "[dry-run] Directories to remove:"
    printf '  %s\n' "${DIR_TARGETS[@]}"
  fi
  if (( ${#FILE_TARGETS[@]} > 0 )); then
    echo "[dry-run] Files to remove:"
    printf '  %s\n' "${FILE_TARGETS[@]}"
  fi
  exit 0
fi

if (( ${#DIR_TARGETS[@]} > 0 )); then
  rm -rf "${DIR_TARGETS[@]}"
fi

if (( ${#FILE_TARGETS[@]} > 0 )); then
  rm -f "${FILE_TARGETS[@]}"
fi

echo "Cleanup complete. Removed ${total_targets} targets."
