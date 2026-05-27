"""Architecture test: Any usage justification (TYPE-002).

TYPE-002: ``Any`` SHOULD NOT be used without a ``# Any:`` justification comment.
This test enforces that bare ``Any`` in type annotations has an inline comment
explaining *why* ``Any`` is necessary.

Scope: ``src/bioetl/`` (all layers).
Exemptions:
  - Import lines (``from typing import Any``)
  - Lines with ``# Any:`` inline justification
  - Callsites of globally-justified aliases (BronzeRecord, GoldRecord, MetaDict)
  - Docstrings and pure-comment lines

Graduated threshold: ``MAX_UNJUSTIFIED`` starts above current count and is
ratcheted down as modules are hardened.  The threshold MUST NOT increase.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path("src/bioetl")

# ── Graduated threshold (ratchet down over time) ──────────────────────
MAX_UNJUSTIFIED = 5
"""Maximum allowed unjustified ``Any`` usages.  Decrease after each iteration."""

# Aliases whose definition already carries ``# Any:`` justification;
# callsites using these names do NOT need per-line justification.
_GLOBALLY_JUSTIFIED = re.compile(
    r"\bBronzeRecord\b|\bGoldRecord\b|\bMetaDict\b|\bDataContainer\b"
)

# Lines that are typing imports — not annotation usages.
_IMPORT_RE = re.compile(r"^\s*from\s+typing.*\bAny\b|^\s*import\s+typing")

# ``Any`` as a word boundary in the *code* portion of the line.
_ANY_RE = re.compile(r"\bAny\b")


def _code_part(line: str) -> str:
    """Return the code portion of *line*, stripping inline comments."""
    # Split on ``  #`` (two-space comment separator per PEP 8).
    idx = line.find("  #")
    if idx != -1:
        return line[:idx]
    # Also handle single-space ``#`` at the start for pure comments.
    return line


def _strip_docstrings(text: str) -> dict[int, str]:
    """Return {lineno: code_part} excluding docstrings and pure-comment lines."""
    result: dict[int, str] = {}
    in_docstring = False
    docstring_char = ""
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if in_docstring:
            if stripped.endswith(docstring_char) or docstring_char in stripped[1:]:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            docstring_char = stripped[:3]
            if stripped.count(docstring_char) == 1:
                in_docstring = True
            continue
        if stripped.startswith("#"):
            continue
        result[i] = _code_part(line)
    return result


def _collect_violations(source_content_cache: dict[Path, str]) -> list[str]:
    """Collect all unjustified ``Any`` usages across src/bioetl/."""
    violations: list[str] = []
    for path, text in sorted(source_content_cache.items()):
        code_lines = _strip_docstrings(text)
        raw_lines = text.splitlines()

        for lineno, code in code_lines.items():
            # Skip import lines.
            if _IMPORT_RE.match(code):
                continue
            # Skip lines without Any.
            if not _ANY_RE.search(code):
                continue
            # Skip if the *full* line has ``# Any:`` justification.
            full_line = raw_lines[lineno - 1]
            if "# Any:" in full_line:
                continue
            # Skip if a globally-justified alias is on this line.
            if _GLOBALLY_JUSTIFIED.search(code):
                continue

            violations.append(
                f"{path.as_posix()}:{lineno}: {raw_lines[lineno - 1].strip()[:100]}"
            )
    return violations


def test_any_budget_threshold(source_content_cache: dict[Path, str]) -> None:
    """Unjustified ``Any`` count must stay below the graduated threshold."""
    violations = _collect_violations(source_content_cache)
    count = len(violations)

    assert count <= MAX_UNJUSTIFIED, (
        f"TYPE-002: {count} unjustified Any usages found "
        f"(threshold: {MAX_UNJUSTIFIED}).  "
        f"Add '# Any: <reason>' inline comment or replace with a proper type.\n"
        f"Top violations:\n" + "\n".join(violations[:40])
    )


def test_any_budget_no_regression(source_content_cache: dict[Path, str]) -> None:
    """Ensure new code does not introduce bare ``Any`` without justification.

    This test prints the current count for tracking purposes.
    """
    violations = _collect_violations(source_content_cache)
    count = len(violations)
    # Informational — printed even when passing.
    print(f"\n[Any Budget] Unjustified: {count} / Threshold: {MAX_UNJUSTIFIED}")
    assert count <= MAX_UNJUSTIFIED, (
        f"TYPE-002: unjustified Any budget regressed ({count} > {MAX_UNJUSTIFIED})"
    )
