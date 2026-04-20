"""Architecture test: документация синхронизирована с RULES.md.

REQ-DOC-010: Все ключевые документы MUST ссылаться на актуальную версию RULES.md.

Этот тест проверяет:
1. Версия в RULES.md извлекается корректно
2. Ключевые документы ссылаются на эту версию
3. CLAUDE.md синхронизирован с RULES.md

См. docs/quick-reference/rules-summary.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Паттерны для извлечения версии из RULES.md.
# Legacy header example: *Версия: 5.10 (TTL/Heartbeat Values Correction), 2026-01-06*
# Canonical frontmatter example: Version: 5.24.0
RULES_VERSION_PATTERN = re.compile(r"\*Версия:\s*(\d+\.\d+)")
RULES_FRONTMATTER_VERSION_PATTERN = re.compile(r"^Version:\s*(\d+\.\d+)(?:\.\d+)?\s*$")
RULES_FRONTMATTER_VERIFIED_PATTERN = re.compile(
    r"^Last verified:\s*'?\d{4}-\d{2}-\d{2}'?\s*$"
)

# Паттерны для проверки ссылок на версию в документах
DOC_VERSION_PATTERNS = [
    re.compile(r"RULES\.md v(\d+\.\d+)"),
    re.compile(r"RULES\.md\s+v(\d+\.\d+)"),
]

# Документы, которые MUST быть синхронизированы с RULES.md
# Исключаем: archived/, audits/ (исторические), __-prompts/ (шаблоны)
# Note: docs restructured to 00-project, 01-requirements, etc.
REQUIRED_SYNC_DOCS = [
    "docs/00-project/ai/agents/guides/CLAUDE.md",
    "docs/00-project/00-map.md",
    "docs/01-requirements/REQUIREMENTS.md",
    "docs/00-project/rules-summary.md",
    "docs/03-guides/cleanup-policy.md",
    "docs/02-architecture/00-overview.md",
]
NONCANONICAL_DOC_PARTS = frozenset(
    {
        "archived",
        "audits",
        "audit",
        "__-prompts",
        "audit-reports",
        "99-archive",
        "reports",
        "exports",
        "generated",
        "site",
    }
)
CANONICAL_VERSION_ROOTS = (
    "docs/02-architecture",
    "docs/03-guides",
    "docs/04-reference",
)


def get_project_root() -> Path:
    """Получить корневую директорию проекта."""
    # Поддержка запуска из разных директорий
    current = Path(__file__).resolve()
    for parent in [current, *list(current.parents)]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (pyproject.toml)")


def extract_rules_version(project_root: Path) -> str:
    """Извлечь версию из docs/00-project/RULES.md."""
    rules_path = project_root / "docs" / "00-project" / "RULES.md"
    if not rules_path.exists():
        raise FileNotFoundError(f"RULES.md not found at {rules_path}")

    content = rules_path.read_text(encoding="utf-8")

    # Ищем в первых 12 строках: поддерживаем legacy inline header и canonical frontmatter.
    for line in content.split("\n")[:12]:
        match = RULES_VERSION_PATTERN.search(line)
        if match:
            return match.group(1)
        match = RULES_FRONTMATTER_VERSION_PATTERN.search(line)
        if match:
            return match.group(1)

    raise ValueError("Could not extract version from RULES.md header")


def extract_doc_version(content: str) -> str | None:
    """Извлечь версию RULES.md из содержимого документа."""
    for pattern in DOC_VERSION_PATTERNS:
        match = pattern.search(content)
        if match:
            return match.group(1)
    return None


def is_noncanonical_doc(md_file: Path) -> bool:
    """Return True for generated/historical doc zones excluded from active version sync."""
    return any(excluded in md_file.parts for excluded in NONCANONICAL_DOC_PARTS)


def _changelog_start_offset(content: str) -> int:
    """Return the earliest changelog/history section offset or content length."""
    markers = (
        "## changelog",
        "## history",
        "## история изменений",
        "## version history",
        "## изменения",
    )
    content_lower = content.lower()
    offsets = [content_lower.find(marker) for marker in markers]
    candidates = [offset for offset in offsets if offset != -1]
    return min(candidates, default=len(content))


def _should_skip_outdated_match(
    *,
    content: str,
    match_start: int,
    match_end: int,
    changelog_start: int,
) -> bool:
    if match_start >= changelog_start:
        return True
    line_start = content.rfind("\n", 0, match_start) + 1
    line = content[line_start : match_end + 50].lower()
    return any(kw in line for kw in ("changelog", "history", "история", "версия:"))


def collect_outdated_version_refs(
    *,
    paths: list[Path],
    project_root: Path,
    rules_version: str,
    docs_text_cache: dict[Path, str] | None = None,
) -> list[str]:
    """Collect stale RULES.md version references outside changelog/history sections."""
    outdated: list[str] = []
    current_major_minor = tuple(map(int, rules_version.split(".")))

    for md_file in paths:
        content = _read_doc_text(md_file, docs_text_cache=docs_text_cache)
        if content is None:
            continue

        outdated.extend(
            _iter_outdated_refs_for_doc(
                md_file=md_file,
                content=content,
                project_root=project_root,
                rules_version=rules_version,
                current_major_minor=current_major_minor,
            )
        )

    return sorted(set(outdated))


def _read_doc_text(
    md_file: Path,
    *,
    docs_text_cache: dict[Path, str] | None,
) -> str | None:
    if docs_text_cache is not None and md_file in docs_text_cache:
        return docs_text_cache[md_file]
    try:
        return md_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _iter_outdated_refs_for_doc(
    *,
    md_file: Path,
    content: str,
    project_root: Path,
    rules_version: str,
    current_major_minor: tuple[int, int],
) -> list[str]:
    changelog_start = _changelog_start_offset(content)
    relative_path = md_file.relative_to(project_root)
    outdated: list[str] = []
    for pattern in DOC_VERSION_PATTERNS:
        for match in pattern.finditer(content):
            found_version = match.group(1)
            if not _is_outdated_doc_version(found_version, current_major_minor):
                continue
            if _should_skip_outdated_match(
                content=content,
                match_start=match.start(),
                match_end=match.end(),
                changelog_start=changelog_start,
            ):
                continue
            outdated.append(
                f"{relative_path}: v{found_version} (current: v{rules_version})"
            )
    return outdated


def _is_outdated_doc_version(
    found_version: str,
    current_major_minor: tuple[int, int],
) -> bool:
    return tuple(map(int, found_version.split("."))) < current_major_minor


def _classify_required_sync_docs(
    *,
    project_root: Path,
    rules_version: str,
) -> tuple[list[str], list[str], list[str]]:
    mismatched: list[str] = []
    missing_version: list[str] = []
    not_found: list[str] = []

    for doc_path in REQUIRED_SYNC_DOCS:
        full_path = project_root / doc_path
        if not full_path.exists():
            not_found.append(doc_path)
            continue

        content = full_path.read_text(encoding="utf-8")
        doc_version = extract_doc_version(content)
        if doc_version is None:
            missing_version.append(doc_path)
            continue
        if doc_version != rules_version:
            mismatched.append(f"{doc_path}: v{doc_version} (expected v{rules_version})")

    return mismatched, missing_version, not_found


def _build_required_sync_doc_errors(
    *,
    mismatched: list[str],
    missing_version: list[str],
    not_found: list[str],
) -> list[str]:
    errors: list[str] = []
    if not_found:
        errors.append(
            "Required documents not found:\n" + "\n".join(f"  - {f}" for f in not_found)
        )
    if missing_version:
        errors.append(
            "Documents missing RULES.md version reference:\n"
            + "\n".join(f"  - {f}" for f in missing_version)
        )
    if mismatched:
        errors.append(
            "Documents with outdated RULES.md version:\n"
            + "\n".join(f"  - {f}" for f in mismatched)
        )
    return errors


def _iter_canonical_docs(
    *,
    project_root: Path,
    docs_markdown_files: list[Path],
) -> list[Path]:
    canonical_root_paths = tuple(
        project_root / root for root in CANONICAL_VERSION_ROOTS
    )
    return [
        md_file
        for md_file in docs_markdown_files
        if any(
            root_path == md_file.parent or root_path in md_file.parents
            for root_path in canonical_root_paths
        )
        and not is_noncanonical_doc(md_file)
    ]


class TestDocsVersionSync:
    """Тесты синхронизации версий документации."""

    @pytest.fixture(scope="session")
    def project_root(self) -> Path:
        """Получить корневую директорию проекта."""
        return get_project_root()

    @pytest.fixture(scope="session")
    def rules_version(self, project_root: Path) -> str:
        """Получить актуальную версию RULES.md."""
        return extract_rules_version(project_root)

    def test_rules_version_extractable(self, project_root: Path) -> None:
        """RULES.md MUST содержать версию в заголовке.

        Формат: *Версия: X.Y (описание), YYYY-MM-DD*
        """
        version = extract_rules_version(project_root)
        assert version, "RULES.md must have version in header"
        assert re.match(r"\d+\.\d+", version), f"Invalid version format: {version}"

    def test_claude_md_synced(self, project_root: Path, rules_version: str) -> None:
        """CLAUDE.md MUST быть синхронизирован с RULES.md.

        REQ-DOC-010: CLAUDE.md является основным справочником для агента.
        """
        claude_md = (
            project_root
            / "docs"
            / "00-project"
            / "ai"
            / "agents"
            / "guides"
            / "CLAUDE.md"
        )
        assert claude_md.exists(), "CLAUDE.md not found"

        content = claude_md.read_text(encoding="utf-8")
        doc_version = extract_doc_version(content)

        assert doc_version is not None, (
            f"CLAUDE.md must reference RULES.md version.\n"
            f"Expected: RULES.md v{rules_version}\n"
            f"Add: *Синхронизировано с RULES.md v{rules_version}*"
        )

        assert doc_version == rules_version, (
            f"CLAUDE.md version mismatch.\n"
            f"RULES.md version: {rules_version}\n"
            f"CLAUDE.md references: {doc_version}\n"
            f"Update CLAUDE.md to reference v{rules_version}"
        )

    def test_required_docs_synced(self, project_root: Path, rules_version: str) -> None:
        """Ключевые документы MUST ссылаться на актуальную версию RULES.md.

        REQ-DOC-010: Документы в REQUIRED_SYNC_DOCS должны быть синхронизированы.
        """
        mismatched, missing_version, not_found = _classify_required_sync_docs(
            project_root=project_root,
            rules_version=rules_version,
        )
        errors = _build_required_sync_doc_errors(
            mismatched=mismatched,
            missing_version=missing_version,
            not_found=not_found,
        )
        assert not errors, "\n\n".join(errors)

    def test_no_outdated_versions_in_active_docs(
        self,
        project_root: Path,
        rules_version: str,
        docs_markdown_files: list[Path],
        docs_text_cache: dict[Path, str],
    ) -> None:
        """Активные документы НЕ ДОЛЖНЫ ссылаться на устаревшие версии.

        Исключения:
        - docs/archived/ - исторические документы (включая audits/)
        - docs/__-prompts/ - шаблоны промптов
        - Changelog/История изменений секции (версия в контексте истории)
        """
        docs_dir = project_root / "docs"
        if not docs_dir.exists():
            pytest.skip("docs/ directory not found")

        active_docs = [
            md_file
            for md_file in docs_markdown_files
            if not is_noncanonical_doc(md_file)
        ]
        outdated = collect_outdated_version_refs(
            paths=active_docs,
            project_root=project_root,
            rules_version=rules_version,
            docs_text_cache=docs_text_cache,
        )

        assert not outdated, (
            f"Found {len(outdated)} documents referencing outdated RULES.md versions:\n"
            + "\n".join(f"  - {f}" for f in sorted(outdated)[:20])
            + ("\n  ... and more" if len(outdated) > 20 else "")
        )

    def test_no_outdated_versions_in_canonical_docs(
        self,
        project_root: Path,
        rules_version: str,
        docs_markdown_files: list[Path],
        docs_text_cache: dict[Path, str],
    ) -> None:
        """Canonical docs in 02/03/04 MUST not reference stale RULES.md versions."""
        canonical_docs = _iter_canonical_docs(
            project_root=project_root,
            docs_markdown_files=docs_markdown_files,
        )

        outdated = collect_outdated_version_refs(
            paths=canonical_docs,
            project_root=project_root,
            rules_version=rules_version,
            docs_text_cache=docs_text_cache,
        )
        assert not outdated, (
            "Canonical docs contain stale RULES.md version references:\n"
            + "\n".join(f"  - {item}" for item in outdated[:20])
            + ("\n  ... and more" if len(outdated) > 20 else "")
        )


class TestVersionFormat:
    """Тесты формата версии."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Получить корневую директорию проекта."""
        return get_project_root()

    def test_rules_version_format(self, project_root: Path) -> None:
        """RULES.md версия MUST соответствовать формату X.Y.

        Формат: major.minor (например, 5.10)
        """
        version = extract_rules_version(project_root)
        parts = version.split(".")

        assert len(parts) == 2, f"Version must be X.Y format, got: {version}"
        assert all(p.isdigit() for p in parts), (
            f"Version parts must be numeric: {version}"
        )

    def test_rules_header_format(self, project_root: Path) -> None:
        """RULES.md header MUST expose version and verification date."""
        rules_path = project_root / "docs" / "00-project" / "RULES.md"
        content = rules_path.read_text(encoding="utf-8")

        legacy_header_pattern = re.compile(
            r"\*Версия:\s*\d+\.\d+\s*\([^)]+\),\s*\d{4}-\d{2}-\d{2}\*"
        )
        lines = content.split("\n")[:12]

        legacy_header_found = any(legacy_header_pattern.search(line) for line in lines)
        frontmatter_version_found = any(
            RULES_FRONTMATTER_VERSION_PATTERN.search(line) for line in lines
        )
        frontmatter_verified_found = any(
            RULES_FRONTMATTER_VERIFIED_PATTERN.search(line) for line in lines
        )

        assert legacy_header_found or (
            frontmatter_version_found and frontmatter_verified_found
        ), (
            "RULES.md must have either a legacy version header:\n"
            "*Версия: X.Y (description), YYYY-MM-DD*\n"
            "or canonical frontmatter with Version and Last verified fields."
        )
