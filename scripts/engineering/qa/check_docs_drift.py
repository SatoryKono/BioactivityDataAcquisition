#!/usr/bin/env python3
"""
Скрипт для проверки дрейфа документации.
Запрещает абсолютные локальные пути и ссылки на другой репозиторий.
"""

import re
import sys
from pathlib import Path

_FORBIDDEN_PATTERNS = (
    r"/mnt/\S+",
    r"C:\\\\\S+",
    r"file:///\S+",
    r"BioactivityDataAcquisition2",
)


def _file_content(file_path: Path) -> str:
    """Read markdown file content."""
    return file_path.read_text(encoding="utf-8")


def _matched_patterns(content: str) -> list[str]:
    """Return forbidden regex patterns found in content."""
    return [pattern for pattern in _FORBIDDEN_PATTERNS if re.search(pattern, content)]


def check_file_forbidden_patterns(file_path: Path) -> list[str]:
    """Проверяет файл на наличие запрещённых шаблонов."""
    return [
        f"Forbidden pattern '{pattern}' found in {file_path}"
        for pattern in _matched_patterns(_file_content(file_path))
    ]


def _markdown_files(docs_dir: Path, readme_file: Path) -> list[Path]:
    """Return README plus docs markdown files."""
    return [readme_file, *docs_dir.rglob("*.md")]


def main() -> int:
    """Основная функция скрипта."""
    docs_dir = Path("docs")
    readme_file = Path("README.md")

    all_violations = []
    skipped_files = []
    for file_path in _markdown_files(docs_dir, readme_file):
        try:
            if file_path.is_file():
                violations = check_file_forbidden_patterns(file_path)
                all_violations.extend(violations)
        except OSError as e:
            # Пропускаем файлы с слишком длинными путями (Windows limitation)
            skipped_files.append(str(file_path))
            print(
                f"Warning: Skipping file due to path error: {file_path}",
                file=sys.stderr,
            )

    if skipped_files:
        print(
            f"Warning: Skipped {len(skipped_files)} files due to path errors",
            file=sys.stderr,
        )

    if all_violations:
        print("Docs drift detected:", file=sys.stderr)
        for violation in all_violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("No docs drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
