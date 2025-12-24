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
from pathlib import Path

MAX_CONSTRUCTOR_ARGS = 8
EXCLUDE_PATTERNS = ["test_", "conftest"]


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
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    # Count args excluding self
                    args = item.args
                    count = len(args.args) - 1 + len(args.kwonlyargs)
                    if count > MAX_CONSTRUCTOR_ARGS:
                        violations.append((node.name, count, item.lineno))
    return violations


def main() -> None:
    """Main entry point."""
    warn_only = "--warn-only" in sys.argv
    src_path = Path("src/bioetl")

    if not src_path.exists():
        print(f"Source path {src_path} not found")
        sys.exit(1)

    all_violations: list[tuple[Path, str, int, int]] = []

    for py_file in src_path.rglob("*.py"):
        if any(p in py_file.name for p in EXCLUDE_PATTERNS):
            continue
        violations = check_file(py_file)
        for class_name, count, lineno in violations:
            all_violations.append((py_file, class_name, count, lineno))

    if all_violations:
        print(f"Constructor argument count violations (max {MAX_CONSTRUCTOR_ARGS}):")
        for filepath, class_name, count, lineno in sorted(all_violations):
            # Use path as-is since it's already relative to src_path
            print(f"  {filepath}:{lineno} - {class_name}.__init__ has {count} args")

        if warn_only:
            print(f"\n[WARN MODE] {len(all_violations)} violation(s) found but not blocking CI")
            print("TODO (#refactor): Remove --warn-only after refactoring")
            sys.exit(0)
        else:
            print(f"\n❌ {len(all_violations)} violation(s) found")
            sys.exit(1)
    else:
        print(f"✅ All constructors have <= {MAX_CONSTRUCTOR_ARGS} arguments")
        sys.exit(0)


if __name__ == "__main__":
    main()
