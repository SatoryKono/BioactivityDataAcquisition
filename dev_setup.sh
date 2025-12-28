#!/usr/bin/env bash
# ==============================================================================
# dev_setup.sh — Скрипт настройки окружения разработки для BioETL
#
# Использование:
#   ./dev_setup.sh          # Полная настройка
#   ./dev_setup.sh --quick  # Только установка зависимостей (без тестов)
#   ./dev_setup.sh --help   # Справка
#
# Синхронизировано с RULES.md v5.7 (2025-12-27)
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

# Флаги
QUICK_MODE=false
SKIP_TESTS=false
FORCE=false

# ==============================================================================
# Функции
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
    - AGENT.md          Инструкции для разработчика
    - docs/RULES.md     Конституция проекта
    - CLAUDE.md         Справочник для Claude Code
EOF
    exit 0
}

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
    local version_output
    version_output=$($python_cmd --version 2>&1)

    # Извлекаем мажорную и минорную версии
    local major minor
    major=$(echo "$version_output" | grep -oP '\d+' | head -1)
    minor=$(echo "$version_output" | grep -oP '\d+' | sed -n '2p')

    if [[ $major -lt $MIN_PYTHON_MAJOR ]] || \
       [[ $major -eq $MIN_PYTHON_MAJOR && $minor -lt $MIN_PYTHON_MINOR ]]; then
        return 1
    fi
    return 0
}

find_python() {
    # Ищем подходящий Python в порядке приоритета
    local python_candidates=("python3.12" "python3.11" "python3" "python")

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

detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

get_venv_activate_path() {
    local os_type
    os_type=$(detect_os)

    if [[ "$os_type" == "windows" ]]; then
        echo "${VENV_DIR}/Scripts/activate"
    else
        echo "${VENV_DIR}/bin/activate"
    fi
}

get_venv_python_path() {
    local os_type
    os_type=$(detect_os)

    if [[ "$os_type" == "windows" ]]; then
        echo "${VENV_DIR}/Scripts/python"
    else
        echo "${VENV_DIR}/bin/python"
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

    # Проверяем Make
    print_step "Проверка Make..."
    if check_command make; then
        print_success "Make: $(make --version | head -1)"
    else
        print_warning "Make не найден. Некоторые команды автоматизации недоступны."
    fi

    # Проверяем Python
    print_step "Поиск Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+..."
    local python_cmd
    if python_cmd=$(find_python); then
        print_success "Python: $($python_cmd --version)"
        PYTHON_CMD="$python_cmd"
    else
        print_error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ не найден!"
        print_error "Установите Python 3.11 или выше и повторите попытку."
        ((errors++))
    fi

    # Проверяем, что мы в корне проекта
    print_step "Проверка директории проекта..."
    if [[ -f "pyproject.toml" && -f "Makefile" ]]; then
        print_success "Находимся в корне проекта BioETL"
    else
        print_error "Скрипт должен запускаться из корня проекта BioETL"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        print_error "Обнаружены критические ошибки. Устраните их и повторите попытку."
        exit 1
    fi
}

step_create_venv() {
    print_header "Шаг 2: Создание виртуального окружения"

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
    $PYTHON_CMD -m venv "$VENV_DIR"
    print_success "Виртуальное окружение создано: $VENV_DIR"
}

step_install_dependencies() {
    print_header "Шаг 3: Установка зависимостей"

    local venv_python
    venv_python=$(get_venv_python_path)

    print_step "Обновление pip, setuptools, wheel..."
    "$venv_python" -m pip install --upgrade pip setuptools wheel --quiet

    print_step "Установка зависимостей разработки..."
    "$venv_python" -m pip install -e ".[dev]" --quiet

    print_success "Зависимости установлены"
}

step_setup_precommit() {
    print_header "Шаг 4: Настройка pre-commit hooks"

    local venv_python
    venv_python=$(get_venv_python_path)

    # Проверяем наличие pre-commit конфига
    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        print_warning "Файл .pre-commit-config.yaml не найден, пропускаем настройку hooks"
        return 0
    fi

    # Проверяем, установлен ли pre-commit
    if "$venv_python" -m pip show pre-commit &> /dev/null; then
        print_step "Установка pre-commit hooks..."
        "$venv_python" -m pre_commit install --install-hooks 2>/dev/null || \
            print_warning "pre-commit hooks не установлены (возможно, не в git-репозитории)"
        print_success "Pre-commit hooks настроены"
    else
        print_step "Установка pre-commit..."
        "$venv_python" -m pip install pre-commit --quiet
        "$venv_python" -m pre_commit install --install-hooks 2>/dev/null || \
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

    local venv_python
    venv_python=$(get_venv_python_path)

    # Проверяем импорт основного модуля
    print_step "Проверка импорта bioetl..."
    if "$venv_python" -c "import bioetl; print(f'BioETL v{bioetl.__version__}')" 2>/dev/null; then
        print_success "Модуль bioetl импортируется корректно"
    else
        print_error "Ошибка импорта модуля bioetl"
        exit 1
    fi

    # Проверяем CLI
    print_step "Проверка CLI..."
    if "$venv_python" -m bioetl --help &>/dev/null; then
        print_success "CLI работает корректно"
    else
        print_warning "CLI недоступен"
    fi
}

step_run_checks() {
    print_header "Шаг 7: Запуск проверок качества"

    if [[ "$QUICK_MODE" == true ]]; then
        print_warning "Быстрый режим: проверки пропущены (--quick)"
        return 0
    fi

    local venv_python
    venv_python=$(get_venv_python_path)

    # Запуск линтеров
    print_step "Запуск ruff..."
    if "$venv_python" -m ruff check src/ tests/ --quiet; then
        print_success "Ruff: без ошибок"
    else
        print_warning "Ruff: обнаружены проблемы (не критично для установки)"
    fi

    print_step "Запуск mypy..."
    if "$venv_python" -m mypy src/bioetl --no-error-summary 2>/dev/null; then
        print_success "Mypy: без ошибок"
    else
        print_warning "Mypy: обнаружены проблемы с типами (не критично для установки)"
    fi

    # Запуск тестов
    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Тесты пропущены (--skip-tests)"
    else
        print_step "Запуск тестов (это может занять несколько минут)..."
        if "$venv_python" -m pytest tests/ -v --tb=short -q 2>/dev/null; then
            print_success "Все тесты пройдены"
        else
            print_warning "Некоторые тесты не прошли (проверьте вручную)"
        fi
    fi
}

print_final_instructions() {
    print_header "Готово! Окружение разработки настроено"

    local activate_path
    activate_path=$(get_venv_activate_path)

    cat << EOF
${GREEN}Следующие шаги:${NC}

1. Активируйте виртуальное окружение:
   ${BLUE}source ${activate_path}${NC}

2. Проверьте статус проекта:
   ${BLUE}make lint && make test${NC}

3. Изучите документацию:
   - ${YELLOW}AGENT.md${NC}         — Инструкции для разработчика
   - ${YELLOW}docs/RULES.md${NC}    — Конституция проекта
   - ${YELLOW}CLAUDE.md${NC}        — Справочник для Claude Code

4. Основные команды:
   ${BLUE}make help${NC}            — Список всех команд
   ${BLUE}make test${NC}            — Запуск тестов
   ${BLUE}make lint${NC}            — Проверка кода
   ${BLUE}make run-local${NC}       — Запуск на фикстурах

${GREEN}Удачной разработки!${NC}
EOF
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
