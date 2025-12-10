#!/usr/bin/env python3
"""
Скрипт для запуска тестов с различными опциями.

Использование:
    python scripts/run_tests.py [category] [options]

Категории:
    unit        - Только unit-тесты (быстрые, без сети)
    integration - Интеграционные тесты
    golden      - Golden-тесты (snapshot testing)
    all         - Все тесты
    coverage    - Все тесты с покрытием кода

Опции:
    --verbose, -v    - Подробный вывод
    --fast, -f       - Быстрый режим (только unit)
    --coverage, -c    - С покрытием кода
    --html           - HTML-отчёт о покрытии
    --min-cov=85     - Минимальное покрытие (по умолчанию 85%)
"""
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(cmd: list[str], description: str) -> int:
    """Запустить команду и вернуть код возврата."""
    print(f"\n{'='*60}")
    print(f"> {description}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        category = "unit"
    else:
        category = sys.argv[1].lower()

    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    coverage = "-c" in sys.argv or "--coverage" in sys.argv or category == "coverage"
    html_report = "--html" in sys.argv
    fast = "-f" in sys.argv or "--fast" in sys.argv

    # Извлечь минимальное покрытие
    min_cov = 85
    for arg in sys.argv:
        if arg.startswith("--min-cov="):
            min_cov = int(arg.split("=")[1])

    base_cmd = ["python", "-m", "pytest"]

    if verbose:
        base_cmd.append("-v")
    else:
        base_cmd.append("-q")

    if category == "unit" or fast:
        cmd = base_cmd + [
            "-m",
            "unit",
            "--ignore=tests/integration",
            "--ignore=tests/golden",
        ]
        return run_command(cmd, "Запуск unit-тестов")

    elif category == "integration":
        cmd = base_cmd + ["-m", "integration", "tests/integration"]
        return run_command(cmd, "Запуск интеграционных тестов")

    elif category == "golden":
        cmd = base_cmd + ["-m", "golden", "tests/golden"]
        return run_command(cmd, "Запуск golden-тестов")

    elif category == "coverage" or coverage:
        cmd = [
            "python",
            "-m",
            "pytest",
            "--cov=src/bioetl",
            "--cov-report=term-missing",
            f"--cov-fail-under={min_cov}",
        ]
        if html_report:
            cmd.append("--cov-report=html")
        if not verbose:
            cmd.append("-q")
        return run_command(cmd, f"Запуск всех тестов с покрытием (минимум {min_cov}%)")

    elif category == "all":
        cmd = base_cmd + ["tests/"]
        return run_command(cmd, "Запуск всех тестов")

    else:
        print(f"Неизвестная категория: {category}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
