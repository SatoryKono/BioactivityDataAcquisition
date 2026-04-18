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
    file_kind: str
    auto_safe: bool
    notes: str

    @property
    def executable(self) -> bool:
        return self.action == "replace_symbol" and self.auto_safe


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


def load_plan_id(plan_path: Path) -> str:
    payload = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    plan_id = payload.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        raise ValueError(f"{plan_path} does not contain a valid plan_id")
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


def load_rows(matrix_path: Path) -> list[RenameRow]:
    rows: list[RenameRow] = []
    with matrix_path.open(encoding="utf-8", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for record in reader:
            rows.append(
                RenameRow(
                    wave=record["wave"],
                    phase_order=int(record["phase_order"]),
                    action=record["action"],
                    symbol_kind=record["symbol_kind"],
                    old_name=record["old_name"],
                    new_name=record["new_name"],
                    file_path=_normalize_path(record["file_path"]),
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
) -> tuple[dict[Path, list[RenameRow]], list[RenameRow]]:
    file_to_rows: dict[Path, list[RenameRow]] = {}
    skipped_rows: list[RenameRow] = []
    for row in rows:
        if row.executable:
            file_to_rows.setdefault(row.file_path, []).append(row)
        else:
            skipped_rows.append(row)
    return file_to_rows, skipped_rows


def _apply_rows_to_file(
    *,
    file_path: Path,
    rows: list[RenameRow],
    patterns: dict[str, re.Pattern[str]],
    apply: bool,
) -> int:
    if not file_path.exists():
        print(f"[missing] {file_path}")
        return 0

    updated_text = file_path.read_text(encoding="utf-8")
    file_matches = 0
    for row in rows:
        pattern = patterns[row.old_name]
        updated_text, count = pattern.subn(row.new_name, updated_text)
        file_matches += count
        if count:
            print(f"[match] {file_path} :: {row.old_name} -> {row.new_name} :: {count}")

    if file_matches == 0:
        print(f"[noop] {file_path}")
        return 0

    if apply:
        file_path.write_text(updated_text, encoding="utf-8")
        print(f"[write] {file_path}")
    else:
        print(f"[dry-run] {file_path}")
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

    for file_path in sorted(file_to_rows):
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

    if not args.matrix.exists():
        print(f"Matrix not found: {args.matrix}", file=sys.stderr)
        return 2
    if not args.plan.exists():
        print(f"Plan not found: {args.plan}", file=sys.stderr)
        return 2

    plan_id = load_plan_id(args.plan)
    rows = load_rows(args.matrix)
    selected_rows = select_rows(rows, args.wave)

    if not selected_rows:
        print("No rows selected.", file=sys.stderr)
        return 2

    print(f"Plan: {plan_id}")
    print(f"Matrix: {args.matrix}")

    if args.list_waves:
        return list_waves(rows)

    return apply_rows(selected_rows, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
