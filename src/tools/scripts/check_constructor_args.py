#!/usr/bin/env python3
"""Check constructor argument counts to enforce dependency limits.

This script uses AST analysis to count the number of arguments in __init__ methods.
Classes with more than MAX_CONSTRUCTOR_ARGS are flagged as violations.

Usage:
    python scripts/check_constructor_args.py           # Enforce mode (exit 1 on violations)
    python scripts/check_constructor_args.py --warn-only  # Warning mode (exit 0 always)
"""

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
    violations = []
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            args = item.args
            count = len(args.args) - 1 + len(args.kwonlyargs)
            if count > MAX_CONSTRUCTOR_ARGS:
                violations.append((class_node.name, count, item.lineno))
    return violations


def check_file(filepath: Path) -> list[tuple[str, int, int]]:
    """Check a file for constructor argument violations.

    Args:
        filepath: Path to the Python file to check.

    Returns:
        List of (class_name, arg_count, line_number) tuples for violations.
    """
    violations = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return violations

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

        with waiver_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        print(
            "Error: PyYAML is required to read constructor_waivers.yaml",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error reading waivers file: {e}", file=sys.stderr)
        sys.exit(1)


def _parse_expiry(expiry_str: str) -> date:
    """Parse expiry date string; return default on invalid."""
    try:
        return datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except ValueError:
        return date(2000, 1, 1)


def _check_single_waiver(
    class_name: str,
    count: int,
    waivers: dict,
    today: date,
    max_ttl_days: int,
) -> tuple[bool, str | None]:
    """Check if a violation is waived. Returns (is_waived, expiry_str or None)."""
    if class_name not in waivers:
        return False, None
    w = waivers[class_name]
    allowed = w.get("allowed_args", 8)
    expiry_str = w.get("expiry_date", "2000-01-01")
    expiry_date = _parse_expiry(expiry_str)
    if count > allowed:
        return False, None
    if expiry_date < today:
        print(f"[WAIVER EXPIRED] {class_name} waiver expired on {expiry_date}")
        return False, None
    if (expiry_date - today).days > max_ttl_days:
        print(
            f"[WAIVER INVALID] {class_name} expiry {expiry_date} exceeds 6 months TTL"
        )
        return False, None
    return True, expiry_str


def _collect_violations_and_waivers(
    src_path: Path,
    waivers: dict,
    today: date,
    max_ttl_days: int,
) -> tuple[list[tuple[Path, str, int, int]], list[tuple[Path, str, int, int, str]]]:
    """Scan source tree and classify violations as waived or not."""
    all_violations: list[tuple[Path, str, int, int]] = []
    waived_classes: list[tuple[Path, str, int, int, str]] = []

    for py_file in src_path.rglob("*.py"):
        if any(p in py_file.name for p in EXCLUDE_PATTERNS):
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
    waiver_path = Path("constructor_waivers.yaml")

    if not src_path.exists():
        print(f"Source path {src_path} not found")
        sys.exit(1)

    waivers = _load_waivers(waiver_path)
    today = datetime.now(UTC).date()
    max_ttl_days = 183  # ~6 months

    all_violations, waived_classes = _collect_violations_and_waivers(
        src_path, waivers, today, max_ttl_days
    )

    _print_results(waived_classes, all_violations)
    _exit_with_status(all_violations, warn_only)


if __name__ == "__main__":
    main()
