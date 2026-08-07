#!/usr/bin/env python3
"""Fix invalid thick arrow operators in Mermaid diagrams.

Replaces ==> with --> and ==>> with -->> in class and sequence diagrams.
Flowcharts and other diagram types are ignored as they use ==> intentionally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ArrowIssue:
    """Represents a thick arrow issue found in a diagram."""

    line_no: int
    operator: str
    line: str


@dataclass
class CheckResult:
    """Result of checking a diagram file for thick arrows."""

    issues: list[ArrowIssue]


def _repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _get_diagram_type(content: str) -> str | None:
    """Get the diagram type from content."""
    first_line = content.strip().split("\n")[0].strip()
    if first_line == "classDiagram":
        return "class"
    elif first_line == "sequenceDiagram":
        return "sequence"
    return None


def check_file(path: Path) -> CheckResult:
    """Check a diagram file for invalid thick arrow operators.

    Args:
        path: Path to the diagram file to check.

    Returns:
        CheckResult with list of ArrowIssue objects.
    """
    content = path.read_text(encoding="utf-8")
    
    diagram_type = _get_diagram_type(content)
    if diagram_type is None:
        return CheckResult(issues=[])
    
    issues: list[ArrowIssue] = []
    lines = content.split("\n")
    
    for line_no, line in enumerate(lines, start=1):
        if diagram_type == "class" and "==>" in line:
            issues.append(ArrowIssue(line_no=line_no, operator="==>", line=line))
        elif diagram_type == "sequence":
            # Use word boundaries to avoid matching ==> inside ==>>
            if re.search(r'(?<!>)==>(?!>)', line):
                issues.append(ArrowIssue(line_no=line_no, operator="==>", line=line))
            if "==>>" in line:
                issues.append(ArrowIssue(line_no=line_no, operator="==>>", line=line))
    
    return CheckResult(issues=issues)


def fix_file(path: Path, dry_run: bool = False) -> int:
    """Fix invalid thick arrow operators in a diagram file.

    Args:
        path: Path to the diagram file to fix.
        dry_run: If True, don't modify the file.

    Returns:
        Number of replacements made.

    Raises:
        ValueError: If the path is outside the repository root or uses parent traversal.
    """
    repo_root = _repo_root()
    
    # Check for parent traversal in the original path first
    if ".." in path.parts:
        raise ValueError(f"Path {path} contains parent traversal")
    
    # Resolve path to check if it's outside repo
    resolved_path = path.resolve()
    
    # Check if path is outside repo
    try:
        resolved_path.relative_to(repo_root.resolve())
    except ValueError:
        raise ValueError(f"Path {path} is outside repository root {repo_root}")
    
    content = path.read_text(encoding="utf-8")
    
    diagram_type = _get_diagram_type(content)
    if diagram_type is None:
        return 0
    
    # Count and perform replacements based on diagram type
    if diagram_type == "class":
        replacements = content.count("==>")
        if replacements == 0:
            return 0
        fixed_content = content.replace("==>", "-->")
    elif diagram_type == "sequence":
        # Sequence diagrams use both ==> and ==>>
        # Count standalone ==> (not part of ==>>)
        standalone_equals = len(re.findall(r'(?<!>)==>(?!>)', content))
        double_equals = content.count("==>>")
        replacements = standalone_equals + double_equals
        if replacements == 0:
            return 0
        # Replace ==>> first to avoid double-replacing
        fixed_content = content.replace("==>>", "-->>")
        fixed_content = fixed_content.replace("==>", "-->")
    else:
        return 0
    
    if not dry_run:
        path.write_text(fixed_content, encoding="utf-8")
    
    return replacements


def main() -> int:
    """CLI entry point for fixing Mermaid operators."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix invalid thick arrow operators in Mermaid diagrams")
    parser.add_argument("path", type=Path, help="Path to the diagram file to fix")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files")
    args = parser.parse_args()
    
    try:
        replacements = fix_file(args.path, dry_run=args.dry_run)
        print(f"Fixed {replacements} thick arrow operators in {args.path}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
