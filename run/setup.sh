#!/usr/bin/env bash
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly VENV_DIR=".venv"

QUICK_MODE=false
FORCE=false
SKIP_CHECKS=false
PYTHON_CMD=""

print_header() {
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"
}

print_step() { echo -e "${GREEN}▶ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✖ $1${NC}"; }
print_success() { echo -e "${GREEN}✔ $1${NC}"; }

show_help() {
    cat <<'USAGE'
BioETL — скрипт подготовки локального окружения

Использование:
  ./run/setup.sh [OPTIONS]

Опции:
  --quick, -q      Быстрая установка (без линтеров и тестов)
  --force, -f      Удалить и пересоздать .venv
  --skip-checks    Пропустить linters/tests после установки
  --help, -h       Показать справку
USAGE
}

check_command() {
    local cmd="$1"
    local label="${2:-$cmd}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        print_error "$label не найден"
        return 1
    fi
    return 0
}

check_python_version() {
    local cmd="$1"
    local version
    local major
    local minor

    version="$($cmd --version 2>&1)"
    major=$(echo "$version" | grep -oE '[0-9]+' | sed -n '1p')
    minor=$(echo "$version" | grep -oE '[0-9]+' | sed -n '2p')

    if [[ -z "$major" || -z "$minor" ]]; then
        return 1
    fi

    if [[ "$major" -lt "$MIN_PYTHON_MAJOR" ]]; then
        return 1
    fi

    if [[ "$major" -eq "$MIN_PYTHON_MAJOR" && "$minor" -lt "$MIN_PYTHON_MINOR" ]]; then
        return 1
    fi

    return 0
}

find_python() {
    local candidates=("python3.12" "python3.11" "python3" "python")
    local cmd
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1 && check_python_version "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quick|-q)
                QUICK_MODE=true
                SKIP_CHECKS=true
                shift
                ;;
            --force|-f)
                FORCE=true
                shift
                ;;
            --skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Неизвестный аргумент: $1"
                exit 1
                ;;
        esac
    done
}

get_venv_python() {
    if [[ -x "${VENV_DIR}/bin/python" ]]; then
        echo "${VENV_DIR}/bin/python"
    elif [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
        echo "${VENV_DIR}/Scripts/python.exe"
    else
        print_error "Python в виртуальном окружении не найден"
        exit 1
    fi
}

step_prerequisites() {
    print_header "Шаг 1: Проверка требований"

    check_command git "Git"
    print_success "$(git --version)"

    if ! check_command make "Make"; then
        print_warning "Make не найден. Используется fallback через pip"
    else
        print_success "$(make --version | head -n1)"
    fi

    if PYTHON_CMD=$(find_python); then
        print_success "Python: $($PYTHON_CMD --version 2>&1)"
    else
        print_error "Требуется Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+"
        exit 1
    fi

    if [[ ! -f "pyproject.toml" ]]; then
        print_error "Запустите скрипт из корня репозитория"
        exit 1
    fi
}

step_create_venv() {
    print_header "Шаг 2: Подготовка виртуального окружения"

    if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
        print_warning "Удаление существующего ${VENV_DIR} (--force)"
        rm -rf "$VENV_DIR"
    fi

    if [[ -d "$VENV_DIR" ]]; then
        print_success "Окружение уже существует: ${VENV_DIR}"
        return 0
    fi

    print_step "Создание ${VENV_DIR}"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    print_success "Виртуальное окружение создано"
}

step_install_dependencies() {
    print_header "Шаг 3: Установка зависимостей"

    local venv_python
    venv_python="$(get_venv_python)"

    if command -v uv >/dev/null 2>&1 && [[ "$FORCE" == false ]]; then
        print_step "Найден uv: установка через uv sync"
        uv sync --extra dev --extra tracing
    else
        print_step "Установка через pip"
        "$venv_python" -m pip install --upgrade pip setuptools wheel
        "$venv_python" -m pip install -e ".[dev,tracing]"
    fi

    print_success "Зависимости установлены"
}

step_env_file() {
    print_header "Шаг 4: Подготовка .env"

    if [[ -f ".env" ]]; then
        print_success ".env уже существует"
        return 0
    fi

    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_success "Создан .env из .env.example"
        print_warning "Заполните секреты в .env перед запуском pipeline"
    else
        print_warning ".env.example не найден — шаг пропущен"
    fi
}

step_smoke_checks() {
    print_header "Шаг 5: Проверка установки"

    local venv_python
    venv_python="$(get_venv_python)"

    print_step "Проверка импорта bioetl"
    "$venv_python" -c "import bioetl; print('bioetl ok')"

    print_step "Проверка CLI"
    "$venv_python" -m bioetl --help >/dev/null

    if [[ "$SKIP_CHECKS" == true ]]; then
        print_warning "Проверки качества пропущены"
        return 0
    fi

    print_step "ruff check src/ tests/"
    if ! "$venv_python" -m ruff check src/ tests/; then
        print_warning "Ruff обнаружил замечания"
    fi

    if [[ "$QUICK_MODE" == false ]]; then
        print_step "pytest tests/smoke -q"
        if ! "$venv_python" -m pytest tests/smoke -q; then
            print_warning "Smoke тесты завершились с ошибками"
        fi
    fi

    print_success "Проверка установки завершена"
}

print_next_steps() {
    print_header "Готово"
    cat <<'NEXT'
1) Активируйте окружение:
   source .venv/bin/activate

2) Проверьте проект:
   make lint
   make test-smoke

3) Запуск пайплайна:
   python -m bioetl run --help
NEXT
}

main() {
    parse_args "$@"
    step_prerequisites
    step_create_venv
    step_install_dependencies
    step_env_file
    step_smoke_checks
    print_next_steps
}

main "$@"
