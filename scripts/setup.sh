#!/usr/bin/env bash
# ==============================================================================
# scripts/setup.sh —  скрипт настройки окружения BioETL
#
# Использование:
#   ./scripts/setup.sh              # Полная настройка
#   ./scripts/setup.sh --quick      # Быстрая установка (без линтеров/тестов)
#   ./scripts/setup.sh --skip-tests # Запуск линтеров без тестов
#   ./scripts/setup.sh --force      # Пересоздание .venv
# ==============================================================================

set -e

QUICK=0
SKIP_TESTS=0
FORCE=0

for arg in "$@"; do
    case $arg in
        --quick)
            QUICK=1
            ;;
        --skip-tests)
            SKIP_TESTS=1
            ;;
        --force)
            FORCE=1
            ;;
        *)
            echo "Неизвестный аргумент: $arg"
            exit 1
            ;;
    esac
done

if [ "$FORCE" -eq 1 ]; then
    echo "Удаление .venv..."
    rm -rf .venv
fi

echo "Установка зависимостей..."
make install

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

if [ "$QUICK" -eq 1 ]; then
    echo "Установка завершена (quick mode)."
    exit 0
fi

echo "Запуск линтеров..."
make lint

if [ "$SKIP_TESTS" -eq 1 ]; then
    echo "Установка завершена (тесты пропущены)."
    exit 0
fi

echo "Запуск тестов..."
make test-fast

echo "Установка успешно завершена."
