#!/usr/bin/env bash
# ==============================================================================
# dev_setup.sh — Скрипт настройки окружения разработки для BioETL
#
# Использование:
#   ./dev_setup.sh          # Полная настройка
#   ./dev_setup.sh --quick  # Только установка зависимостей (без тестов)
#   ./dev_setup.sh --help   # Справка
#
# Синхронизировано с RULES.md v5.20 (2026-02-17)
# ==============================================================================

set -euo pipefail

# Цвета для вывода
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Минимальные версии
readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly VENV_DIR=".venv"

# Глобальные переменные (устанавливаются на этапе prerequisites / install)
PYTHON_CMD=""   # Системный python для создания venv
VENV_PYTHON=""  # Python внутри venv (используется для всех последующих шагов)
HAS_UV=false    # Доступен ли uv

# Флаги
QUICK_MODE=false
SKIP_TESTS=false
FORCE=false

# ==============================================================================
# Функции вывода
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

show_help() {
    cat << EOF
BioETL — Скрипт настройки окружения разработки

Использование:
    ./dev_setup.sh [OPTIONS]

Опции:
    --quick, -q     Быстрая установка (без запуска тестов и линтеров)
    --skip-tests    Пропустить запуск тестов (но запустить линтеры)
    --force, -f     Пересоздать виртуальное окружение, даже если оно существует
    --help, -h      Показать эту справку

Примеры:
    ./dev_setup.sh              # Полная настройка с проверками
    ./dev_setup.sh --quick      # Быстрая установка для опытных разработчиков
    ./dev_setup.sh --force      # Пересоздать окружение с нуля

Документация:
    - docs/00-project/agents/AGENT.md    Инструкции для разработчика
    - docs/00-project/RULES.md           Конституция проекта
    - docs/00-project/agents/CLAUDE.md   Справочник для Claude Code
EOF
    exit 0
}

# ==============================================================================
# Утилиты
# ==============================================================================

check_command() {
    local cmd=$1
    local name=${2:-$cmd}
    if ! command -v "$cmd" &> /dev/null; then
        print_error "$name не найден. Установите $name и повторите попытку."
        return 1
    fi
    return 0
}

check_python_version() {
    local python_cmd=$1
    local major minor
    major=$("$python_cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null) || return 1
    minor=$("$python_cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || return 1

    if [[ $major -lt $MIN_PYTHON_MAJOR ]] || \
       [[ $major -eq $MIN_PYTHON_MAJOR && $minor -lt $MIN_PYTHON_MINOR ]]; then
        return 1
    fi
    return 0
}

find_python() {
    # Ищем подходящий Python в порядке приоритета
    local python_candidates=("python3.13" "python3.12" "python3.11" "python3" "python")

    for cmd in "${python_candidates[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            if check_python_version "$cmd"; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# Находит python внутри venv (кроссплатформенно)
resolve_venv_python() {
    if [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
        echo "${VENV_DIR}/Scripts/python.exe"
    elif [[ -x "${VENV_DIR}/Scripts/python" ]]; then
        echo "${VENV_DIR}/Scripts/python"
    elif [[ -x "${VENV_DIR}/bin/python" ]]; then
        echo "${VENV_DIR}/bin/python"
    else
        return 1
    fi
}

# Находит activate скрипт venv (кроссплатформенно)
resolve_venv_activate() {
    if [[ -f "${VENV_DIR}/Scripts/activate" ]]; then
        echo "${VENV_DIR}/Scripts/activate"
    elif [[ -f "${VENV_DIR}/bin/activate" ]]; then
        echo "${VENV_DIR}/bin/activate"
    else
        echo "${VENV_DIR}/bin/activate"  # fallback
    fi
}

# ==============================================================================
# Парсинг аргументов
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick|-q)
                QUICK_MODE=true
                SKIP_TESTS=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --force|-f)
                FORCE=true
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                print_error "Неизвестный аргумент: $1"
                echo "Используйте --help для справки"
                exit 1
                ;;
        esac
    done
}

# ==============================================================================
# Основные шаги настройки
# ==============================================================================

step_check_prerequisites() {
    print_header "Шаг 1: Проверка предварительных требований"

    local errors=0

    # Проверяем Git
    print_step "Проверка Git..."
    if check_command git; then
        print_success "Git: $(git --version)"
    else
        ((errors++))
    fi

    # Проверяем Make (опционально)
    print_step "Проверка Make..."
    if check_command make; then
        print_success "Make: $(make --version | head -1)"
    else
        print_warning "Make не найден. Некоторые команды автоматизации недоступны."
    fi

    # Проверяем uv (рекомендуемый менеджер)
    print_step "Проверка uv..."
    if command -v uv &> /dev/null; then
        HAS_UV=true
        print_success "uv: $(uv --version)"
    else
        print_warning "uv не найден. Будет использован pip (медленнее)."
        print_step "Установка uv: https://docs.astral.sh/uv/getting-started/installation/"
    fi

    # Проверяем Python
    print_step "Поиск Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+..."
    if PYTHON_CMD=$(find_python); then
        print_success "Python: $($PYTHON_CMD --version)"
    else
        print_error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ не найден!"
        print_error "Установите Python 3.11 или выше и повторите попытку."
        ((errors++))
    fi

    # Проверяем, что мы в корне проекта
    print_step "Проверка директории проекта..."
    if [[ -f "pyproject.toml" ]]; then
        print_success "Находимся в корне проекта BioETL"
    else
        print_error "Скрипт должен запускаться из корня проекта BioETL (pyproject.toml не найден)"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        print_error "Обнаружены критические ошибки. Устраните их и повторите попытку."
        exit 1
    fi
}

step_create_venv() {
    print_header "Шаг 2: Создание виртуального окружения"

    # uv создаёт venv самостоятельно при sync — пропускаем ручное создание
    if [[ "$HAS_UV" == true ]]; then
        if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
            print_warning "Удаление существующего окружения (--force)..."
            rm -rf "$VENV_DIR"
        fi
        print_step "uv создаст виртуальное окружение автоматически при установке"
        return 0
    fi

    if [[ -d "$VENV_DIR" ]]; then
        if [[ "$FORCE" == true ]]; then
            print_warning "Удаление существующего окружения (--force)..."
            rm -rf "$VENV_DIR"
        else
            print_success "Виртуальное окружение уже существует: $VENV_DIR"
            print_step "Используйте --force для пересоздания"
            return 0
        fi
    fi

    print_step "Создание виртуального окружения..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    print_success "Виртуальное окружение создано: $VENV_DIR"
}

step_install_dependencies() {
    print_header "Шаг 3: Установка зависимостей"

    if [[ "$HAS_UV" == true ]]; then
        print_step "Установка зависимостей с помощью uv (рекомендуется)..."
        uv sync --group dev --extra dev --extra tests --extra tracing --extra performance --extra export
        print_success "Зависимости установлены через uv"
    else
        VENV_PYTHON=$(resolve_venv_python) || {
            print_error "Не удалось найти python в $VENV_DIR"
            exit 1
        }

        print_step "Обновление pip, setuptools, wheel..."
        "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel --quiet

        print_step "Установка зависимостей разработки..."
        "$VENV_PYTHON" -m pip install -e ".[dev,tests,tracing,performance,export]" --quiet

        print_success "Зависимости установлены через pip"
    fi

    # Определяем venv python для последующих шагов
    VENV_PYTHON=$(resolve_venv_python) || {
        print_error "Не удалось найти python в $VENV_DIR после установки"
        exit 1
    }
    print_step "Venv Python: $($VENV_PYTHON --version 2>&1)"
}

step_setup_precommit() {
    print_header "Шаг 4: Настройка pre-commit hooks"

    # Проверяем наличие pre-commit конфига
    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        print_warning "Файл .pre-commit-config.yaml не найден, пропускаем настройку hooks"
        return 0
    fi

    # Проверяем, установлен ли pre-commit
    if "$VENV_PYTHON" -m pip show pre-commit &> /dev/null; then
        print_step "Установка pre-commit hooks..."
        "$VENV_PYTHON" -m pre_commit install --install-hooks 2>/dev/null || \
            print_warning "pre-commit hooks не установлены (возможно, не в git-репозитории)"
        print_success "Pre-commit hooks настроены"
    else
        print_step "Установка pre-commit..."
        "$VENV_PYTHON" -m pip install pre-commit --quiet
        "$VENV_PYTHON" -m pre_commit install --install-hooks 2>/dev/null || \
            print_warning "pre-commit hooks не установлены"
        print_success "Pre-commit установлен и настроен"
    fi
}

step_setup_env() {
    print_header "Шаг 5: Настройка переменных окружения"

    if [[ -f ".env" ]]; then
        print_success "Файл .env уже существует"
    elif [[ -f ".env.example" ]]; then
        print_step "Копирование .env.example → .env..."
        cp .env.example .env
        print_success "Файл .env создан из примера"
        print_warning "Отредактируйте .env для добавления API-ключей при необходимости"
    else
        print_warning "Файл .env.example не найден, пропускаем"
    fi
}

step_verify_installation() {
    print_header "Шаг 6: Проверка установки"

    # Проверяем импорт основного модуля
    print_step "Проверка импорта bioetl..."
    if "$VENV_PYTHON" -c "import bioetl; print(f'BioETL v{bioetl.__version__}')" 2>/dev/null; then
        print_success "Модуль bioetl импортируется корректно"
    else
        print_error "Ошибка импорта модуля bioetl"
        exit 1
    fi

    # Проверяем критические runtime-зависимости
    print_step "Проверка критических зависимостей (pandas, pandera, deltalake)..."
    if "$VENV_PYTHON" -c "
import pandas, pandera, deltalake
print(f'pandas {pandas.__version__}, pandera {pandera.__version__}, deltalake {deltalake.__version__}')
" 2>/dev/null; then
        print_success "Критические зависимости доступны"
    else
        print_error "Критические зависимости не найдены! Проверьте установку."
        exit 1
    fi

    # Проверяем dev-зависимости
    print_step "Проверка dev-зависимостей (ruff, mypy, pytest)..."
    if "$VENV_PYTHON" -c "import pytest; print(f'pytest {pytest.__version__}')" 2>/dev/null \
       && "$VENV_PYTHON" -m ruff version 2>/dev/null \
       && "$VENV_PYTHON" -m mypy --version 2>/dev/null; then
        print_success "Dev-зависимости доступны"
    else
        print_warning "Некоторые dev-зависимости не найдены (не критично для runtime)"
    fi

    # Полная проверка через Makefile если доступен
    if command -v make &> /dev/null && [[ -f "Makefile" ]]; then
        print_step "Запуск расширенной проверки через make test-deps-dev..."
        if make test-deps-dev; then
            print_success "Все зависимости и инструменты разработки подтверждены"
        else
            print_warning "Некоторые зависимости не прошли проверку. Проверьте логи."
        fi
    fi

    # Проверяем CLI
    print_step "Проверка CLI..."
    if "$VENV_PYTHON" -m bioetl --help &>/dev/null; then
        print_success "CLI работает корректно"
    else
        print_warning "CLI недоступен (возможно, требуется настройка)"
    fi
}

step_run_checks() {
    print_header "Шаг 7: Запуск проверок качества"

    if [[ "$QUICK_MODE" == true ]]; then
        print_warning "Быстрый режим: проверки пропущены (--quick)"
        return 0
    fi

    # Запуск линтеров
    print_step "Запуск ruff..."
    if "$VENV_PYTHON" -m ruff check src/ tests/ --quiet; then
        print_success "Ruff: без ошибок"
    else
        print_warning "Ruff: обнаружены проблемы (не критично для установки)"
    fi

    print_step "Запуск mypy..."
    if "$VENV_PYTHON" -m mypy src/bioetl --no-error-summary 2>/dev/null; then
        print_success "Mypy: без ошибок"
    else
        print_warning "Mypy: обнаружены проблемы с типами (не критично для установки)"
    fi

    # Запуск architecture тестов
    print_step "Запуск architecture тестов..."
    if "$VENV_PYTHON" -m pytest tests/architecture/ -q --tb=short 2>/dev/null; then
        print_success "Architecture tests: без нарушений"
    else
        print_warning "Architecture tests: обнаружены нарушения (проверьте вручную)"
    fi

    # Запуск тестов
    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Тесты пропущены (--skip-tests)"
    else
        print_step "Запуск тестов..."
        if "$VENV_PYTHON" -m pytest tests/ -q --tb=short 2>/dev/null; then
            print_success "Все тесты пройдены"
        else
            print_warning "Некоторые тесты не прошли (проверьте вручную)"
        fi
    fi
}

print_final_instructions() {
    print_header "Готово! Окружение разработки настроено"

    local activate_path
    activate_path=$(resolve_venv_activate)

    if [[ "$HAS_UV" == true ]]; then
        cat << EOF
${GREEN}Следующие шаги:${NC}

1. Команды запускаются через uv (активация venv не требуется):
   ${BLUE}uv run bioetl --help${NC}
   ${BLUE}uv run pytest tests/ -q${NC}

   Или активируйте окружение вручную:
   ${BLUE}source ${activate_path}${NC}

2. Проверьте статус проекта:
   ${BLUE}make lint && make test${NC}

3. Изучите документацию:
   - ${YELLOW}docs/00-project/agents/AGENT.md${NC}  — Инструкции для разработчика
   - ${YELLOW}docs/00-project/RULES.md${NC}         — Конституция проекта (v5.20)
   - ${YELLOW}docs/00-project/agents/CLAUDE.md${NC} — Справочник для Claude Code

4. Основные команды:
   ${BLUE}make help${NC}            — Список всех команд
   ${BLUE}make test${NC}            — Запуск тестов
   ${BLUE}make lint${NC}            — Проверка кода
   ${BLUE}make run-local${NC}       — Запуск пайплайна на фикстурах

${GREEN}Удачной разработки!${NC}
EOF
    else
        cat << EOF
${GREEN}Следующие шаги:${NC}

1. Активируйте виртуальное окружение:
   ${BLUE}source ${activate_path}${NC}

2. Проверьте статус проекта:
   ${BLUE}make lint && make test${NC}

3. Изучите документацию:
   - ${YELLOW}docs/00-project/agents/AGENT.md${NC}  — Инструкции для разработчика
   - ${YELLOW}docs/00-project/RULES.md${NC}         — Конституция проекта (v5.20)
   - ${YELLOW}docs/00-project/agents/CLAUDE.md${NC} — Справочник для Claude Code

4. Основные команды:
   ${BLUE}make help${NC}            — Список всех команд
   ${BLUE}make test${NC}            — Запуск тестов
   ${BLUE}make lint${NC}            — Проверка кода
   ${BLUE}make run-local${NC}       — Запуск пайплайна на фикстурах

${GREEN}Удачной разработки!${NC}
EOF
    fi
}

# ==============================================================================
# Главная функция
# ==============================================================================

main() {
    print_header "BioETL — Настройка окружения разработки"

    parse_args "$@"

    step_check_prerequisites
    step_create_venv
    step_install_dependencies
    step_setup_precommit
    step_setup_env
    step_verify_installation
    step_run_checks
    print_final_instructions
}

# Запуск
main "$@"