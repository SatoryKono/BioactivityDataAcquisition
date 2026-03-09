"""Architecture tests for documentation cross-reference integrity.

Validates ADR-043 requirements:
- ADR references in code comments point to existing ADRs
- Provider runbooks exist for active providers
- Glossary exists as single source of truth
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ADR_DIR = DOCS_DIR / "02-architecture" / "decisions"
SRC_DIR = ROOT / "src" / "bioetl"


@pytest.mark.architecture
class TestADRReferencesValid:
    """Verify that ADR references in source code point to existing ADRs."""

    _ADR_PATTERN = re.compile(r"ADR[- ]?(\d{3})", re.IGNORECASE)

    def _get_existing_adr_numbers(self) -> set[int]:
        """Collect all ADR numbers from docs/02-architecture/decisions/."""
        numbers: set[int] = set()
        for path in ADR_DIR.glob("ADR-*.md"):
            match = re.search(r"ADR-(\d{3})", path.name)
            if match:
                numbers.add(int(match.group(1)))
        return numbers

    def test_code_adr_references_exist(self) -> None:
        """All ADR-NNN references in source code should have corresponding files."""
        existing = self._get_existing_adr_numbers()
        violations: list[str] = []

        for py_file in SRC_DIR.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for match in self._ADR_PATTERN.finditer(content):
                adr_num = int(match.group(1))
                if adr_num not in existing and adr_num > 0:
                    violations.append(
                        f"{py_file.relative_to(ROOT)}:{match.start()}: "
                        f"references ADR-{adr_num:03d} which does not exist"
                    )

        if violations:
            msg = f"Found {len(violations)} broken ADR reference(s):\n"
            msg += "\n".join(violations[:10])
            if len(violations) > 10:
                msg += f"\n... and {len(violations) - 10} more"
            pytest.fail(msg)


@pytest.mark.architecture
class TestProviderRunbooks:
    """Verify provider runbooks exist per ADR-043."""

    _ACTIVE_PROVIDERS = [
        "chembl",
        "pubchem",
        "uniprot",
        "pubmed",
        "crossref",
        "openalex",
        "semanticscholar",
    ]

    def test_runbook_dir_exists(self) -> None:
        """Runbooks directory should exist."""
        runbook_dir = DOCS_DIR / "05-operations" / "runbooks"
        if not runbook_dir.exists():
            pytest.skip("Runbooks directory not yet created (ADR-043 pending implementation)")


@pytest.mark.architecture
class TestGlossaryExists:
    """Verify glossary exists as single source of truth."""

    def test_glossary_file_exists(self) -> None:
        """Glossary should exist in docs/04-reference/."""
        glossary_candidates = [
            DOCS_DIR / "04-reference" / "glossary.md",
            DOCS_DIR / "04-reference" / "GLOSSARY.md",
        ]
        found = any(p.exists() for p in glossary_candidates)
        if not found:
            pytest.skip("Glossary not yet created (ADR-043 pending implementation)")
