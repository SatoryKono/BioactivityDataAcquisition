#!/usr/bin/env python3
"""
Скрипт для проверки дрейфа документации.
Запрещает абсолютные локальные пути и ссылки на другой репозиторий.
"""
import re
import sys
from pathlib import Path


def check_file_forbidden_patterns(file_path: Path) -> list[str]:
    """Проверяет файл на наличие запрещённых шаблонов."""
    forbidden_patterns = [
        r"/mnt/\S+",  # Абсолютные пути в Linux
        r"C:\\\\\S+",  # Абсолютные пути в Windows
        r"file:///\S+",  # Локальные файловые ссылки
        r"BioactivityDataAcquisition2",  # Ссылки на другой репозиторий
    ]

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    violations = []
    for pattern in forbidden_patterns:
        if re.search(pattern, content):
            violations.append(f"Forbidden pattern '{pattern}' found in {file_path}")

    return violations


def main() -> int:
    """Основная функция скрипта."""
    docs_dir = Path("docs")
    readme_file = Path("README.md")

    files_to_check = [readme_file] + list(docs_dir.rglob("*.md"))

    all_violations = []
    for file_path in files_to_check:
        if file_path.is_file():
            violations = check_file_forbidden_patterns(file_path)
            all_violations.extend(violations)

    if all_violations:
        print("Docs drift detected:", file=sys.stderr)
        for violation in all_violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("No docs drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
