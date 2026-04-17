#!/usr/bin/env python3
"""Check constructor argument counts to enforce dependency limits."""

from __future__ import annotations

import ast
import sys
from datetime import UTC, date, datetime
from pathlib import Path

MAX_CONSTRUCTOR_ARGS = 8
EXCLUDE_PATTERNS = ["test_", "conftest"]


def _collect_violations_from_class(
    class_node: ast.ClassDef,
) -> list[tuple[str, int, int]]:
    """Check a class for constructor argument violations."""
    violations: list[tuple[str, int, int]] = []
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            args = item.args
            count = len(args.args) - 1 + len(args.kwonlyargs)
            if count > MAX_CONSTRUCTOR_ARGS:
                violations.append((class_node.name, count, item.lineno))
    return violations


def check_file(filepath: Path) -> list[tuple[str, int, int]]:
    """Check a file for constructor argument violations."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    violations: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            violations.extend(_collect_violations_from_class(node))
    return violations


def _load_waivers(waiver_path: Path) -> dict:
    """Load waivers from YAML file. Exits on error."""
    if not waiver_path.exists():
        return {}
    try:
        import yaml

        with waiver_path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except ImportError:
        print(
            "Error: PyYAML is required to read configs/quality/constructor_waivers.yaml",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - defensive user-facing branch
        print(f"Error reading waivers file: {exc}", file=sys.stderr)
        sys.exit(1)


def _parse_expiry(expiry_str: str) -> date:
    """Parse expiry date string; return default old date on invalid format."""
    try:
        return date.fromisoformat(expiry_str)
    except ValueError:
        return date(1970, 1, 1)


def _check_single_waiver(
    class_name: str,
    count: int,
    waivers: dict,
    today: date,
    max_ttl_days: int,
) -> tuple[bool, str | None]:
    """Return whether a class violation is currently waived."""
    waiver = waivers.get(class_name)
    if not waiver:
        return False, None

    expiry_str = waiver.get("expiry")
    if not isinstance(expiry_str, str):
        return False, None

    expiry = _parse_expiry(expiry_str)
    ttl_days = (expiry - today).days
    allowed_count = waiver.get("max_args")
    if not isinstance(allowed_count, int):
        allowed_count = MAX_CONSTRUCTOR_ARGS

    is_waived = today <= expiry and ttl_days <= max_ttl_days and count <= allowed_count
    return is_waived, expiry_str if is_waived else None


def _collect_violations_and_waivers(
    src_path: Path,
    waivers: dict,
    today: date,
    max_ttl_days: int,
) -> tuple[
    list[tuple[Path, str, int, int]],
    list[tuple[Path, str, int, int, str]],
]:
    """Collect constructor violations and currently valid waivers."""
    all_violations: list[tuple[Path, str, int, int]] = []
    waived_classes: list[tuple[Path, str, int, int, str]] = []

    for py_file in src_path.rglob("*.py"):
        if any(pattern in py_file.name for pattern in EXCLUDE_PATTERNS):
            continue

        for class_name, count, lineno in check_file(py_file):
            is_waived, expiry_str = _check_single_waiver(
                class_name, count, waivers, today, max_ttl_days
            )
            if is_waived and expiry_str is not None:
                waived_classes.append((py_file, class_name, count, lineno, expiry_str))
            elif not is_waived:
                all_violations.append((py_file, class_name, count, lineno))

    return all_violations, waived_classes


def _print_results(
    waived_classes: list[tuple[Path, str, int, int, str]],
    all_violations: list[tuple[Path, str, int, int]],
) -> None:
    """Print waived and violation summaries."""
    if waived_classes:
        print(f"Waived constructor violations ({len(waived_classes)}):")
        for filepath, class_name, count, lineno, expiry in sorted(waived_classes):
            print(
                f"  [WAIVED until {expiry}] {filepath}:{lineno} - {class_name} has {count} args"
            )
    if all_violations:
        print(f"\nConstructor argument count violations (max {MAX_CONSTRUCTOR_ARGS}):")
        for filepath, class_name, count, lineno in sorted(all_violations):
            print(f"  {filepath}:{lineno} - {class_name}.__init__ has {count} args")


def _exit_with_status(
    all_violations: list[tuple[Path, str, int, int]],
    warn_only: bool,
) -> None:
    """Exit with appropriate code based on violations and mode."""
    if not all_violations:
        print(f"[OK] All constructors have <= {MAX_CONSTRUCTOR_ARGS} arguments")
        sys.exit(0)
    if warn_only:
        print(
            f"\n[WARN MODE] {len(all_violations)} violation(s) found but not blocking CI"
        )
        sys.exit(0)
    print(f"\n[FAIL] {len(all_violations)} violation(s) found")
    sys.exit(1)


def main() -> None:
    """Main entry point."""
    warn_only = "--warn-only" in sys.argv
    src_path = Path("src/bioetl")
    waiver_path = Path("configs/quality/constructor_waivers.yaml")

    if not src_path.exists():
        print(f"Source path {src_path} not found")
        sys.exit(1)

    waivers = _load_waivers(waiver_path)
    today = datetime.now(UTC).date()
    max_ttl_days = 183

    all_violations, waived_classes = _collect_violations_and_waivers(
        src_path, waivers, today, max_ttl_days
    )

    _print_results(waived_classes, all_violations)
    _exit_with_status(all_violations, warn_only)


if __name__ == "__main__":
    main()
