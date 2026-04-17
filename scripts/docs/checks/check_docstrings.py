#!/usr/bin/env python3
"""check_docstring_coverage.py - Verify docstring coverage meets project thresholds.

Checks that all public modules, classes, and functions in src/bioetl/ have
docstrings.  Exits with code 1 if coverage drops below the configured
thresholds (see ``THRESHOLDS``).

Usage:
    python scripts/check_docstring_coverage.py            # Full report
    python scripts/check_docstring_coverage.py --summary   # One-line summary only
    python scripts/check_docstring_coverage.py --json      # Machine-readable JSON
    python scripts/check_docstring_coverage.py --fail-under 95  # Custom threshold (%)

Exit code: 0 = pass, 1 = threshold violation found

References:
    - RULES.md TYPE-001 (public function annotations)
    - ai-selfreview-rules.md §5 (Type Annotations)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src" / "bioetl"

# Default thresholds (percent)
THRESHOLDS = {
    "modules": 100,
    "classes": 95,
    "functions": 90,
}


@dataclass
class CoverageStats:
    """Accumulated docstring coverage statistics."""

    modules_total: int = 0
    modules_with_doc: int = 0
    classes_total: int = 0
    classes_with_doc: int = 0
    functions_total: int = 0
    functions_with_doc: int = 0
    missing: list[dict[str, str]] = field(default_factory=list)

    def _pct(self, with_doc: int, total: int) -> float:
        return round(100.0 * with_doc / total, 1) if total else 100.0

    @property
    def modules_pct(self) -> float:
        return self._pct(self.modules_with_doc, self.modules_total)

    @property
    def classes_pct(self) -> float:
        return self._pct(self.classes_with_doc, self.classes_total)

    @property
    def functions_pct(self) -> float:
        return self._pct(self.functions_with_doc, self.functions_total)

    def to_dict(self) -> dict[str, object]:
        """Serialize statistics to a plain dictionary."""
        return {
            "modules": {
                "total": self.modules_total,
                "documented": self.modules_with_doc,
                "percent": self.modules_pct,
            },
            "classes": {
                "total": self.classes_total,
                "documented": self.classes_with_doc,
                "percent": self.classes_pct,
            },
            "functions": {
                "total": self.functions_total,
                "documented": self.functions_with_doc,
                "percent": self.functions_pct,
            },
            "missing_count": len(self.missing),
            "missing": self.missing,
        }


def collect_stats(src_dir: Path) -> CoverageStats:
    """Walk *src_dir* and gather docstring coverage data."""
    stats = CoverageStats()

    def process_body(nodes: list[ast.stmt], *, rel: Path) -> None:
        """Collect public classes and functions from one lexical body."""
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                stats.classes_total += 1
                if ast.get_docstring(node):
                    stats.classes_with_doc += 1
                else:
                    stats.missing.append(
                        {
                            "file": str(rel),
                            "line": str(node.lineno),
                            "kind": "class",
                            "name": node.name,
                        }
                    )
                process_body(node.body, rel=rel)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                stats.functions_total += 1
                if ast.get_docstring(node):
                    stats.functions_with_doc += 1
                else:
                    stats.missing.append(
                        {
                            "file": str(rel),
                            "line": str(node.lineno),
                            "kind": "function",
                            "name": node.name,
                        }
                    )

    for py_file in sorted(src_dir.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue

        rel = py_file.relative_to(src_dir)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue

        stats.modules_total += 1
        if ast.get_docstring(tree):
            stats.modules_with_doc += 1
        else:
            stats.missing.append({"file": str(rel), "kind": "module", "name": str(rel)})
        process_body(tree.body, rel=rel)

    return stats


def print_report(stats: CoverageStats, *, verbose: bool = True) -> None:
    """Print a human-readable coverage report to *stdout*."""
    print("Docstring Coverage Report")
    print("=" * 50)
    print(
        f"  Modules:   {stats.modules_with_doc}/{stats.modules_total}"
        f"  ({stats.modules_pct}%)"
    )
    print(
        f"  Classes:   {stats.classes_with_doc}/{stats.classes_total}"
        f"  ({stats.classes_pct}%)"
    )
    print(
        f"  Functions: {stats.functions_with_doc}/{stats.functions_total}"
        f"  ({stats.functions_pct}%)"
    )
    print()

    if verbose and stats.missing:
        public_missing = [m for m in stats.missing if not m["name"].startswith("_")]
        if public_missing:
            print(f"Public items missing docstrings ({len(public_missing)}):")
            for m in public_missing:
                loc = f"{m['file']}:{m.get('line', '1')}"
                print(f"  {m['kind']:>8}  {loc}  {m['name']}")
            print()


def check_thresholds(
    stats: CoverageStats,
    fail_under: float | None = None,
) -> list[str]:
    """Return list of threshold violations (empty = pass)."""
    violations: list[str] = []

    thresholds = dict(THRESHOLDS)
    if fail_under is not None:
        thresholds = dict.fromkeys(thresholds, fail_under)

    for kind, threshold in thresholds.items():
        actual = getattr(stats, f"{kind}_pct")
        if actual < threshold:
            violations.append(f"{kind}: {actual}% < {threshold}% threshold")

    return violations


def main() -> int:
    """Run the docstring coverage checker."""
    parser = argparse.ArgumentParser(
        description="Check docstring coverage for src/bioetl/",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print one-line summary only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Override all thresholds with a single percentage (e.g. 95)",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=SRC_DIR,
        help="Source directory to scan (default: src/bioetl)",
    )
    args = parser.parse_args()

    stats = collect_stats(args.src)

    if args.json_output:
        violations = check_thresholds(stats, args.fail_under)
        output = stats.to_dict()
        output["violations"] = violations
        output["status"] = "FAIL" if violations else "PASS"
        json.dump(output, sys.stdout, indent=2)
        print()
        return 1 if violations else 0

    if args.summary:
        print(
            f"Docstrings: modules={stats.modules_pct}%"
            f" classes={stats.classes_pct}%"
            f" functions={stats.functions_pct}%"
            f" (missing={len(stats.missing)})"
        )
    else:
        print_report(stats)

    violations = check_thresholds(stats, args.fail_under)
    if violations:
        print("THRESHOLD VIOLATIONS:")
        for violation in violations:
            print(f"  FAIL: {violation}")
        return 1

    print("All thresholds passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
