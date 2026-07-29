# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for documentation cross-reference integrity.

Validates ADR-043 requirements:
- ADR references in code comments point to existing ADRs
- Provider reference docs exist for active providers
- Runbooks index exists for operational playbooks
- Glossary exists as single source of truth
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ADR_DIR = DOCS_DIR / "02-architecture" / "decisions"
SRC_DIR = ROOT / "src" / "bioetl"
CANONICAL_DOC_DIRS = (
    DOCS_DIR / "02-architecture",
    DOCS_DIR / "03-guides",
    DOCS_DIR / "04-reference",
)
NONCANONICAL_DOC_DIRS = (
    DOCS_DIR / "exports",
    DOCS_DIR / "reports",
    DOCS_DIR / "02-architecture" / "generated",
)
ARCHIVE_DIR = DOCS_DIR / "99-archive"
_LINK_TARGET_RE = re.compile(r"\[[^\]]+\]\(([^)#?]+)(?:[#?][^)]+)?\)")
_ARCHIVE_CONTEXT_MARKERS = ("archived", "historical", "legacy", "superseded")


def _iter_canonical_markdown_files(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect canonical markdown docs audited for cross-reference integrity."""
    return sorted(
        path
        for path in docs_markdown_files
        if any(
            root == path.parent or root in path.parents for root in CANONICAL_DOC_DIRS
        )
        and "generated" not in path.parts
    )


def _iter_internal_doc_links(
    path: Path,
    docs_text_cache: dict[Path, str],
) -> list[tuple[int, str, Path]]:
    """Collect internal docs links with resolved absolute targets."""
    records: list[tuple[int, str, Path]] = []
    for lineno, line in enumerate(docs_text_cache[path].splitlines(), start=1):
        for match in _LINK_TARGET_RE.finditer(line):
            target = match.group(1).strip()
            if not target or re.match(r"^[a-z]+:", target, re.IGNORECASE):
                continue
            # `Path.resolve()` is disproportionately expensive on /mnt/* checkouts
            # and we only need lexical normalization to keep comparisons inside docs/.
            resolved = Path(os.path.normpath(path.parent / target))
            if DOCS_DIR != resolved and DOCS_DIR not in resolved.parents:
                continue
            records.append((lineno, target, resolved))
    return records


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

    def test_code_adr_references_exist(
        self,
        source_content_cache: dict[Path, str],
    ) -> None:
        """All ADR-NNN references in source code should have corresponding files."""
        existing = self._get_existing_adr_numbers()
        violations: list[str] = []

        for py_file, content in source_content_cache.items():
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


@pytest.mark.architecture
class TestCanonicalDocCrossrefs:
    """Ensure canonical docs do not drift toward generated/report/archive artifacts."""

    def test_canonical_docs_do_not_link_noncanonical_doc_zones(
        self,
        docs_markdown_files: list[Path],
        docs_text_cache: dict[Path, str],
    ) -> None:
        """Canonical docs should not use reports/exports/generated docs as references."""
        violations: list[str] = []
        for doc_path in _iter_canonical_markdown_files(docs_markdown_files):
            for lineno, target, resolved in _iter_internal_doc_links(
                doc_path, docs_text_cache
            ):
                if any(
                    resolved == zone or zone in resolved.parents
                    for zone in NONCANONICAL_DOC_DIRS
                ):
                    violations.append(
                        f"{doc_path.relative_to(ROOT)}:{lineno} -> {target}"
                    )

        assert not violations, (
            "Canonical docs reference non-canonical doc zones "
            "(reports/exports/generated):\n" + "\n".join(violations)
        )

    def test_archive_links_in_canonical_docs_are_explicitly_marked(
        self,
        docs_markdown_files: list[Path],
        docs_text_cache: dict[Path, str],
    ) -> None:
        """Historical archive links from canonical docs must be marked as archived/historical."""
        violations: list[str] = []
        for doc_path in _iter_canonical_markdown_files(docs_markdown_files):
            lines = docs_text_cache[doc_path].splitlines()
            for lineno, target, resolved in _iter_internal_doc_links(
                doc_path, docs_text_cache
            ):
                if not (resolved == ARCHIVE_DIR or ARCHIVE_DIR in resolved.parents):
                    continue
                line = lines[lineno - 1].lower()
                if not any(marker in line for marker in _ARCHIVE_CONTEXT_MARKERS):
                    violations.append(
                        f"{doc_path.relative_to(ROOT)}:{lineno} -> {target}"
                    )

        assert not violations, (
            "Archive references from canonical docs must be explicitly marked "
            "as archived/historical:\n" + "\n".join(violations)
        )

    def test_reports_index_declares_non_normative_status(self) -> None:
        """Reports index must explicitly state that canonical guidance lives elsewhere."""
        reports_index = DOCS_DIR / "reports" / "index.md"
        text = reports_index.read_text(encoding="utf-8").lower()
        assert "non-normative" in text, "docs/reports/index.md must be non-normative"
        assert "docs/02-architecture" in text
        assert "docs/03-guides" in text
        assert "docs/04-reference" in text

    def test_generated_exports_declare_non_canonical_status(
        self,
        docs_markdown_files: list[Path],
        docs_text_cache: dict[Path, str],
    ) -> None:
        """Merged export docs must declare themselves generated/non-canonical."""
        violations: list[str] = []
        for path in sorted(
            p
            for p in docs_markdown_files
            if p.parent == DOCS_DIR / "exports" and p.name.endswith(".merged.md")
        ):
            head = "\n".join(docs_text_cache[path].splitlines()[:20]).lower()
            if "_generated:" not in head or "non-normative" not in head:
                violations.append(path.relative_to(ROOT).as_posix())

        assert not violations, (
            "Generated export docs must include generated + non-normative markers:\n"
            + "\n".join(violations)
        )
