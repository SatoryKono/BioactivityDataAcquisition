#!/bin/bash
# Скрипт для запуска тестов (bash-версия)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

CATEGORY="${1:-unit}"
VERBOSE="${2:-}"

case "$CATEGORY" in
    unit)
        echo "▶ Запуск unit-тестов"
        python -m pytest -m unit --ignore=tests/integration --ignore=tests/golden ${VERBOSE:+-v} -q
        ;;
    integration)
        echo "▶ Запуск интеграционных тестов"
        python -m pytest -m integration tests/integration ${VERBOSE:+-v} -q
        ;;
    golden)
        echo "▶ Запуск golden-тестов"
        python -m pytest -m golden tests/golden ${VERBOSE:+-v} -q
        ;;
    coverage)
        echo "▶ Запуск всех тестов с покрытием (минимум 85%)"
        python -m pytest --cov=src/bioetl --cov-report=term-missing --cov-fail-under=85 -q
        ;;
    all)
        echo "▶ Запуск всех тестов"
        python -m pytest tests/ ${VERBOSE:+-v} -q
        ;;
    *)
        echo "Неизвестная категория: $CATEGORY"
        echo "Использование: $0 [unit|integration|golden|coverage|all] [verbose]"
        exit 1
        ;;
esac

