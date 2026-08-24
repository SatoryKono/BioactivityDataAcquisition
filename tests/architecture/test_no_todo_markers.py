# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
"""
Test to prevent TODO/FIXME markers in production code.

This test enforces governance by detecting real TODO/FIXME comments in Python source code,
excluding configuration files, documentation, and intentional marker definitions.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[2]

# Patterns to exclude - these are intentional uses in configs/validation
EXCLUDED_PATTERNS = [
    r"placeholder_markers.*todo",  # Config definitions of TODO as placeholder
    r"wip_markers.*todo",  # Memory graph WIP marker definitions
    r'_PLACEHOLDER_.*RE.*todo',  # Regex patterns for placeholder validation
    r"ADR-XXX",  # ADR filename pattern
    r"Wxxxx",  # OpenAlex ID pattern
    r"CVCL_XXXX",  # Cellosaurus ID pattern
    r"10\.XXXX",  # DOI validation pattern
    r"mktemp.*XXXXX",  # Temporary file creation
    r"fix all TODO",  # Documentation examples
]

# Paths to exclude from scanning
EXCLUDED_PATHS = [
    "tests/",  # Test files may have TODO comments
    "docs/",  # Documentation files
    ".github/",  # GitHub configuration
    "scripts/",  # Scripts may have intentional TODO examples
    "configs/",  # Configuration files with validation patterns
    ".devin/",  # Devin configuration
    ".codex/",  # Codex configuration
    ".junie/",  # Junie configuration
]

# Specific files to exclude from TEMPORAL marker check
# These files have intentional TEMPORAL documentation sections
TEMPORAL_EXCLUDED_FILES = [
    "src/bioetl/domain/mapping/publication_fields.py",  # Field migration documentation
]


def _is_excluded_path(path: Path) -> bool:
    """Check if path should be excluded from TODO scanning."""
    path_str = str(path.relative_to(REPO_ROOT))
    for excluded in EXCLUDED_PATHS:
        if excluded in path_str or path_str.startswith(excluded):
            return True
    return False


def _is_excluded_pattern(line: str) -> bool:
    """Check if line matches an excluded pattern (intentional use)."""
    for pattern in EXCLUDED_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _is_temporal_excluded_file(path: Path) -> bool:
    """Check if file is excluded from TEMPORAL marker check."""
    try:
        # Normalize path separators for cross-platform compatibility
        path_str = str(path.relative_to(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        return False
    return any(excluded in path_str for excluded in TEMPORAL_EXCLUDED_FILES)


def test_no_todo_markers(source_content_cache: dict) -> None:
    """
    Test that no real TODO/FIXME comments exist in production code.
    
    This test looks for actual TODO/FIXME comments in Python source code,
    excluding:
    - Configuration files that define TODO as a placeholder marker
    - Validation patterns that include TODO in regex
    - Documentation and examples
    - Test files
    
    Real TODO comments should be tracked in GitHub issues, not left in code.
    """
    violations: list[str] = []
    
    # Pattern for real TODO/FIXME comments (not just mentions in strings/docs)
    # Matches: # TODO:, # FIXME:, # TODO, # FIXME (case-insensitive)
    todo_pattern = re.compile(r"#\s*(TODO|FIXME)\s*:", re.IGNORECASE)
    
    for path, text in source_content_cache.items():
        # Skip excluded paths
        if _is_excluded_path(path):
            continue
        
        # Skip files with intentional TEMPORAL documentation
        if _is_temporal_excluded_file(path):
            continue
        
        # Only check Python files
        if not path.suffix == ".py":
            continue
        
        for i, line in enumerate(text.splitlines(), 1):
            # Check for TODO/FIXME pattern
            if todo_pattern.search(line):
                # Skip if line matches excluded pattern
                if _is_excluded_pattern(line):
                    continue
                
                violations.append(f"{path}:{i}: {line.strip()}")
    
    assert not violations, (
        "Real TODO/FIXME comments found in production code. "
        "Track these in GitHub issues instead of leaving in code:\n"
        + "\n".join(violations[:50])
    )


def test_no_temporal_markers_in_comments(source_content_cache: dict) -> None:
    """
    Test that no TEMPORAL TODO markers exist in code comments.
    
    This test specifically looks for TEMPORAL markers used as TODO indicators
    (e.g., "# TEMPORAL: fix this later"), not legitimate use of the word
    "temporal" in documentation (e.g., "# Temporal fields" in mapping files).
    """
    violations: list[str] = []
    
    # Pattern for TEMPORAL TODO markers (not just the word "temporal")
    # Matches: # TEMPORAL:, # TEMPORARY - used as TODO markers
    temporal_todo_pattern = re.compile(r"#\s*TEMPORAL\s*[:\-]", re.IGNORECASE)
    
    for path, text in source_content_cache.items():
        # Skip excluded paths
        if _is_excluded_path(path):
            continue
        
        # Skip files with intentional TEMPORAL documentation
        if _is_temporal_excluded_file(path):
            continue
        
        # Only check Python files
        if not path.suffix == ".py":
            continue
        
        for i, line in enumerate(text.splitlines(), 1):
            if temporal_todo_pattern.search(line):
                violations.append(f"{path}:{i}: {line.strip()}")
    
    assert not violations, (
        "TEMPORAL TODO markers found in code comments. "
        "Use GitHub issues to track temporary code:\n"
        + "\n".join(violations[:50])
    )
