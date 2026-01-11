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

# Паттерн для извлечения версии из RULES.md
# Пример: *Версия: 5.10 (TTL/Heartbeat Values Correction), 2026-01-06*
RULES_VERSION_PATTERN = re.compile(r"\*Версия:\s*(\d+\.\d+)")

# Паттерны для проверки ссылок на версию в документах
DOC_VERSION_PATTERNS = [
    re.compile(r"RULES\.md v(\d+\.\d+)"),
    re.compile(r"RULES\.md\s+v(\d+\.\d+)"),
]

# Документы, которые MUST быть синхронизированы с RULES.md
# Исключаем: archived/, audits/ (исторические), __-prompts/ (шаблоны)
# Note: docs/00-project_rules/ был консолидирован в docs/quick-reference/ и docs/03-guides/
REQUIRED_SYNC_DOCS = [
    "CLAUDE.md",
    "docs/00-map.md",
    "docs/REQUIREMENTS.md",
    "docs/quick-reference/rules-summary.md",
    "docs/03-guides/cleanup-policy.md",
    "docs/02-architecture/00-overview.md",
]


def get_project_root() -> Path:
    """Получить корневую директорию проекта."""
    # Поддержка запуска из разных директорий
    current = Path(__file__).resolve()
    for parent in [current, *list(current.parents)]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (pyproject.toml)")


def extract_rules_version(project_root: Path) -> str:
    """Извлечь версию из docs/RULES.md."""
    rules_path = project_root / "docs" / "RULES.md"
    if not rules_path.exists():
        raise FileNotFoundError(f"RULES.md not found at {rules_path}")

    content = rules_path.read_text(encoding="utf-8")

    # Ищем в первых 10 строках
    for line in content.split("\n")[:10]:
        match = RULES_VERSION_PATTERN.search(line)
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


class TestDocsVersionSync:
    """Тесты синхронизации версий документации."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Получить корневую директорию проекта."""
        return get_project_root()

    @pytest.fixture
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
        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists(), "CLAUDE.md not found"

        content = claude_md.read_text(encoding="utf-8")
        doc_version = extract_doc_version(content)

        assert doc_version is not None, (
            f"CLAUDE.md must reference RULES.md version.\n"
            f"Expected: RULES.md v{rules_version}\n"
            f"Add: *Синхронизировано с RULES.md v{rules_version}*"  # noqa: RUF001
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
        mismatched = []
        missing_version = []
        not_found = []

        for doc_path in REQUIRED_SYNC_DOCS:
            full_path = project_root / doc_path
            if not full_path.exists():
                not_found.append(doc_path)
                continue

            content = full_path.read_text(encoding="utf-8")
            doc_version = extract_doc_version(content)

            if doc_version is None:
                missing_version.append(doc_path)
            elif doc_version != rules_version:
                mismatched.append(
                    f"{doc_path}: v{doc_version} (expected v{rules_version})"
                )

        errors = []
        if not_found:
            errors.append(
                "Required documents not found:\n"
                + "\n".join(f"  - {f}" for f in not_found)
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

        assert not errors, "\n\n".join(errors)

    def test_no_outdated_versions_in_active_docs(
        self, project_root: Path, rules_version: str
    ) -> None:
        """Активные документы НЕ ДОЛЖНЫ ссылаться на устаревшие версии.

        Исключения:
        - docs/archived/ - исторические документы
        - docs/audits/, docs/audit/ - отчёты аудитов (фиксируют версию на момент аудита)
        - docs/__-prompts/ - шаблоны промптов
        - Changelog/История изменений секции (версия в контексте истории)
        """
        # Директории для исключения
        excluded_dirs = {"archived", "audits", "audit", "__-prompts", "audit-reports"}

        outdated = []
        current_major_minor = tuple(map(int, rules_version.split(".")))

        docs_dir = project_root / "docs"
        if not docs_dir.exists():
            pytest.skip("docs/ directory not found")

        for md_file in docs_dir.rglob("*.md"):
            # Пропускаем исключённые директории
            if any(excluded in md_file.parts for excluded in excluded_dirs):
                continue

            content = md_file.read_text(encoding="utf-8")

            # Определяем, есть ли секция changelog/history
            # и где она начинается
            changelog_markers = [
                "## changelog",
                "## history",
                "## история изменений",
                "## version history",
                "## изменения",
            ]
            changelog_start = len(content)  # По умолчанию - конец файла
            content_lower = content.lower()
            for marker in changelog_markers:
                pos = content_lower.find(marker)
                if pos != -1 and pos < changelog_start:
                    changelog_start = pos

            # Ищем все упоминания версий
            for pattern in DOC_VERSION_PATTERNS:
                for match in pattern.finditer(content):
                    found_version = match.group(1)
                    found_major_minor = tuple(map(int, found_version.split(".")))

                    # Проверяем, что версия не устаревшая
                    if found_major_minor < current_major_minor:
                        # Пропускаем упоминания в changelog секциях
                        if match.start() >= changelog_start:
                            continue

                        # Также проверяем контекст строки
                        line_start = content.rfind("\n", 0, match.start()) + 1
                        line = content[line_start : match.end() + 50].lower()
                        if any(
                            kw in line
                            for kw in ["changelog", "history", "история", "версия:"]
                        ):
                            continue

                        relative_path = md_file.relative_to(project_root)
                        outdated.append(
                            f"{relative_path}: v{found_version} "
                            f"(current: v{rules_version})"
                        )

        # Уникальные записи
        outdated = list(set(outdated))

        assert not outdated, (
            f"Found {len(outdated)} documents referencing outdated RULES.md versions:\n"
            + "\n".join(f"  - {f}" for f in sorted(outdated)[:20])
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
        """RULES.md заголовок MUST содержать версию и дату.

        Формат: *Версия: X.Y (описание), YYYY-MM-DD*
        """
        rules_path = project_root / "docs" / "RULES.md"
        content = rules_path.read_text(encoding="utf-8")

        # Полный паттерн заголовка
        header_pattern = re.compile(
            r"\*Версия:\s*\d+\.\d+\s*\([^)]+\),\s*\d{4}-\d{2}-\d{2}\*"
        )

        header_found = False
        for line in content.split("\n")[:10]:
            if header_pattern.search(line):
                header_found = True
                break

        assert header_found, (
            "RULES.md must have version header in format:\n"
            "*Версия: X.Y (description), YYYY-MM-DD*"
        )
