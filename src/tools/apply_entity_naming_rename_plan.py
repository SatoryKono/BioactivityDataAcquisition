"""Apply allowlisted entity naming renames from the prepared CSV matrix.

Default mode is dry-run. The script only executes rows marked as:
- action = replace_symbol
- auto_safe = true

Manual-review and regenerate rows remain visible in the summary but are never
modified by this script.

Examples:
    python src/tools/apply_entity_naming_rename_plan.py
    python src/tools/apply_entity_naming_rename_plan.py --wave W1-domain-entities
    python src/tools/apply_entity_naming_rename_plan.py --wave W2-gold-contract-schemas --apply
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX_PATH = (
    REPO_ROOT
    / "reports"
    / "architecture"
    / "entity-naming-rename-matrix-2026-03-19.csv"
)
DEFAULT_PLAN_PATH = (
    REPO_ROOT / "reports" / "architecture" / "entity-naming-rename-plan-2026-03-19.yaml"
)


@dataclass(frozen=True, slots=True)
class RenameRow:
    wave: str
    phase_order: int
    action: str
    symbol_kind: str
    old_name: str
    new_name: str
    file_path: Path
    validated_file_path: ValidatedRepoPath
    file_kind: str
    auto_safe: bool
    notes: str

    @property
    def executable(self) -> bool:
        return self.action == "replace_symbol" and self.auto_safe


@dataclass(frozen=True, slots=True)
class ValidatedRepoPath:
    """Repository-scoped path validated before filesystem access."""

    resolved_path: Path

    @property
    def repo_relative_path(self) -> Path:
        return self.resolved_path.relative_to(REPO_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix",
        type=Path,
        default=DEFAULT_MATRIX_PATH,
        help="CSV rename matrix to execute.",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help="YAML plan file used only for metadata/reporting.",
    )
    parser.add_argument(
        "--wave",
        action="append",
        default=[],
        help="Restrict execution to one or more waves.",
    )
    parser.add_argument(
        "--list-waves",
        action="store_true",
        help="Print discovered waves and exit.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk. Default is dry-run.",
    )
    return parser.parse_args()


def _resolve_input_path(path: Path) -> ValidatedRepoPath:
    candidate = _resolve_repo_path(path)
    if not candidate.is_file():
        raise ValueError(f"expected file path, got: {candidate}")
    return ValidatedRepoPath(candidate)


def _validated_input_path(path: ValidatedRepoPath | Path) -> ValidatedRepoPath:
    if isinstance(path, ValidatedRepoPath):
        return path
    return _resolve_input_path(path)


def load_plan_id(plan_path: ValidatedRepoPath | Path) -> str:
    safe_plan_path = _validated_input_path(plan_path)
    payload = (
        yaml.safe_load(safe_plan_path.resolved_path.read_text(encoding="utf-8")) or {}
    )
    plan_id = payload.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        raise ValueError(
            f"{safe_plan_path.resolved_path} does not contain a valid plan_id"
        )
    return plan_id


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() == "true"


def _normalize_path(raw: str) -> Path:
    if os.name == "nt" and raw.startswith("/mnt/"):
        parts = raw.split("/")
        if len(parts) >= 4 and len(parts[2]) == 1:
            drive = parts[2].upper()
            rest = "/".join(parts[3:])
            return Path(f"{drive}:/{rest}")
    return Path(raw)


def _normalize_repo_relative_path(path: Path) -> Path:
    """Normalize and validate a repository-relative path."""
    if path.is_absolute():
        raise ValueError(
            f"expected repository-relative path, got absolute path: {path}"
        )

    normalized_parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"refusing parent traversal path: {path}")
        normalized_parts.append(part)

    if not normalized_parts:
        raise ValueError("refusing empty repository-relative path")
    return Path(*normalized_parts)


def _resolve_repo_path(path: Path) -> Path:
    candidate = (
        path
        if path.is_absolute()
        else REPO_ROOT.joinpath(*_normalize_repo_relative_path(path).parts)
    )
    resolved = candidate.resolve()
    if REPO_ROOT != resolved and REPO_ROOT not in resolved.parents:
        raise ValueError(f"refusing to access path outside repository: {resolved}")
    return resolved


def _repo_relative_path(path: Path) -> Path:
    """Return a repository-relative path for a validated file path."""
    return _resolve_repo_path(path).relative_to(REPO_ROOT)


def _write_validated_repo_text(file_path: ValidatedRepoPath, text: str) -> None:
    """Write text only after revalidating the target path inside the repository."""
    safe_path = _resolve_input_path(file_path.resolved_path).resolved_path
    with safe_path.open("w", encoding="utf-8") as file_obj:
        file_obj.write(text)


def load_rows(matrix_path: ValidatedRepoPath | Path) -> list[RenameRow]:
    safe_matrix_path = _validated_input_path(matrix_path)
    rows: list[RenameRow] = []
    with safe_matrix_path.resolved_path.open(encoding="utf-8", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for record in reader:
            validated_file_path = _resolve_input_path(
                _normalize_path(record["file_path"])
            )
            rows.append(
                RenameRow(
                    wave=record["wave"],
                    phase_order=int(record["phase_order"]),
                    action=record["action"],
                    symbol_kind=record["symbol_kind"],
                    old_name=record["old_name"],
                    new_name=record["new_name"],
                    file_path=validated_file_path.repo_relative_path,
                    validated_file_path=validated_file_path,
                    file_kind=record["file_kind"],
                    auto_safe=_parse_bool(record["auto_safe"]),
                    notes=record["notes"],
                )
            )
    return rows


def select_rows(rows: list[RenameRow], selected_waves: list[str]) -> list[RenameRow]:
    if not selected_waves:
        return rows
    selected = set(selected_waves)
    return [row for row in rows if row.wave in selected]


def list_waves(rows: list[RenameRow]) -> int:
    waves = sorted({(row.phase_order, row.wave) for row in rows})
    for phase_order, wave in waves:
        print(f"{phase_order}: {wave}")
    return 0


def _group_executable_rows(
    rows: list[RenameRow],
) -> tuple[dict[ValidatedRepoPath, list[RenameRow]], list[RenameRow]]:
    file_to_rows: dict[ValidatedRepoPath, list[RenameRow]] = {}
    skipped_rows: list[RenameRow] = []
    for row in rows:
        if row.executable:
            file_to_rows.setdefault(row.validated_file_path, []).append(row)
        else:
            skipped_rows.append(row)
    return file_to_rows, skipped_rows


def _apply_rows_to_file(
    *,
    file_path: ValidatedRepoPath,
    rows: list[RenameRow],
    patterns: dict[str, re.Pattern[str]],
    apply: bool,
) -> int:
    safe_file_path = file_path.resolved_path
    display_path = file_path.repo_relative_path
    if not safe_file_path.exists():
        print(f"[missing] {display_path}")
        return 0

    updated_text = safe_file_path.read_text(encoding="utf-8")
    file_matches = 0
    for row in rows:
        pattern = patterns[row.old_name]
        updated_text, count = pattern.subn(row.new_name, updated_text)
        file_matches += count
        if count:
            print(
                f"[match] {display_path} :: {row.old_name} -> {row.new_name} :: {count}"
            )

    if file_matches == 0:
        print(f"[noop] {display_path}")
        return 0

    if apply:
        _write_validated_repo_text(file_path, updated_text)
        print(f"[write] {display_path}")
    else:
        print(f"[dry-run] {display_path}")
    return file_matches


def _print_skipped_rows(skipped_rows: list[RenameRow]) -> None:
    if not skipped_rows:
        return
    print("\nSkipped non-auto-safe rows:")
    for row in skipped_rows:
        print(
            f"- {row.wave} :: {row.action} :: {row.old_name} -> {row.new_name} :: {row.file_path}"
        )


def apply_rows(rows: list[RenameRow], *, apply: bool) -> int:
    file_to_rows, skipped_rows = _group_executable_rows(rows)
    executable_rows = [
        row for grouped_rows in file_to_rows.values() for row in grouped_rows
    ]

    print(f"Mode: {'apply' if apply else 'dry-run'}")
    print(f"Executable rows: {len(executable_rows)}")
    print(f"Skipped rows: {len(skipped_rows)}")

    unique_old_names: set[str] = set()
    for row in executable_rows:
        unique_old_names.add(row.old_name)

    # Pre-compile patterns to avoid re-compilation in the nested loop
    # and bypass Python's internal regex cache limits.
    patterns = {
        name: re.compile(rf"\b{re.escape(name)}\b") for name in unique_old_names
    }

    total_matches = 0
    modified_files = 0

    for file_path in sorted(
        file_to_rows, key=lambda path: path.repo_relative_path.as_posix()
    ):
        file_matches = _apply_rows_to_file(
            file_path=file_path,
            rows=file_to_rows[file_path],
            patterns=patterns,
            apply=apply,
        )
        if file_matches == 0:
            continue
        total_matches += file_matches
        modified_files += 1
    _print_skipped_rows(skipped_rows)

    mode = "apply" if apply else "dry-run"
    print(
        "\nSummary: "
        f"modified_files={modified_files} "
        f"total_matches={total_matches} "
        f"mode={mode}"
    )
    return 0


def main() -> int:
    args = parse_args()
    try:
        matrix_path = _resolve_input_path(args.matrix)
        plan_path = _resolve_input_path(args.plan)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    plan_id = load_plan_id(plan_path)
    rows = load_rows(matrix_path)
    selected_rows = select_rows(rows, args.wave)

    if not selected_rows:
        print("No rows selected.", file=sys.stderr)
        return 2

    print(f"Plan: {plan_id}")
    print(f"Matrix: {matrix_path.resolved_path}")

    if args.list_waves:
        return list_waves(rows)

    return apply_rows(selected_rows, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
