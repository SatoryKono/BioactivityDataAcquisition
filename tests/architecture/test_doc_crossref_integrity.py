"""Architecture tests for documentation cross-reference integrity.

Validates ADR-043 requirements:
- ADR references in code comments point to existing ADRs
- Provider reference docs exist for active providers
- Runbooks index exists for operational playbooks
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
class TestProviderDocumentationTopology:
    """Verify provider docs and runbooks topology per ADR-043."""

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
        assert runbook_dir.exists(), "docs/05-operations/runbooks/ directory missing"

    def test_runbook_index_exists(self) -> None:
        """Operational runbooks must be indexed from runbooks/index.md."""
        index_path = DOCS_DIR / "05-operations" / "runbooks" / "index.md"
        assert index_path.exists(), "docs/05-operations/runbooks/index.md missing"

    def test_provider_reference_docs_exist(self) -> None:
        """Each active provider should have reference docs under docs/04-reference/providers."""
        providers_dir = DOCS_DIR / "04-reference" / "providers"
        missing = [
            provider
            for provider in self._ACTIVE_PROVIDERS
            if not (providers_dir / provider).exists()
        ]
        assert not missing, (
            "Missing provider reference docs under docs/04-reference/providers/: "
            + ", ".join(sorted(missing))
        )


@pytest.mark.architecture
class TestGlossaryExists:
    """Verify glossary exists as single source of truth."""

    def test_glossary_file_exists(self) -> None:
        """Glossary should exist at docs/00-project/glossary.md."""
        glossary_path = DOCS_DIR / "00-project" / "glossary.md"
        assert glossary_path.exists(), "docs/00-project/glossary.md missing"
