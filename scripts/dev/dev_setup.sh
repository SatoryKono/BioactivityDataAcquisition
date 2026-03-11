#!/usr/bin/env bash
# ==============================================================================
# scripts/dev/dev_setup.sh — Скрипт настройки окружения разработки для BioETL
#
# Использование:
#   ./scripts/dev/dev_setup.sh              # Полная настройка (canonical)
#   ./scripts/dev/dev_setup.sh --quick      # Только установка зависимостей
#   ./scripts/dev/dev_setup.sh --ci         # CI-режим (без цветов, без интерактива)
#   ./scripts/dev/dev_setup.sh --help       # Справка
#
# BioETL v6.0.0 | Синхронизировано с RULES.md v5.23 (2026-03-08)
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Конфигурация
# ==============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Минимальные версии
readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly MIN_UV_MAJOR=0
readonly MIN_UV_MINOR=6
readonly VENV_DIR=".venv"

# Замер времени
SETUP_START_TIME=""
STEP_TIMINGS=()

# Глобальные переменные (устанавливаются на этапе prerequisites / install)
PYTHON_CMD=""   # Системный python для создания venv
VENV_PYTHON=""  # Python внутри venv (используется для всех последующих шагов)
HAS_UV=false    # Доступен ли uv

# Флаги
QUICK_MODE=false
SKIP_TESTS=false
FORCE=false
CI_MODE=false
VERBOSE=false
NO_COLOR=false

# Результаты шагов для итоговой таблицы
declare -A STEP_RESULTS=()  # step_name -> PASS|WARN|FAIL|SKIP

# ==============================================================================
# Цвета (отключаются в CI или при NO_COLOR / pipe)
# ==============================================================================

setup_colors() {
    if [[ "$NO_COLOR" == true ]] || [[ "$CI_MODE" == true ]] || [[ ! -t 1 ]]; then
        RED='' GREEN='' YELLOW='' BLUE='' BOLD='' DIM='' NC=''
    else
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[0;33m'
        BLUE='\033[0;34m'
        BOLD='\033[1m'
        DIM='\033[2m'
        NC='\033[0m'
    fi
}

# ==============================================================================
# Функции вывода
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}══════════════════════════════════════════════════════════════${NC}\n"
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

print_info() {
    echo -e "${DIM}  $1${NC}"
}

# ==============================================================================
# Таймер
# ==============================================================================

now_ms() {
    if [[ "$(uname)" == "Darwin" ]]; then
        python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || date +%s000
    else
        date +%s%3N 2>/dev/null || date +%s000
    fi
}

record_step_time() {
    local step_name=$1
    local start_ms=$2
    local end_ms
    end_ms=$(now_ms)
    local duration_ms=$(( end_ms - start_ms ))
    local duration_s=$(( duration_ms / 1000 ))
    local duration_remainder=$(( duration_ms % 1000 ))
    STEP_TIMINGS+=("${step_name}|${duration_s}.${duration_remainder}s")
}

# ==============================================================================
# Справка
# ==============================================================================

show_help() {
    cat << 'EOF'
BioETL — Скрипт настройки окружения разработки

Использование:
    ./scripts/dev/dev_setup.sh [OPTIONS]

Опции:
    --quick, -q     Быстрая установка (без тестов и линтеров)
    --skip-tests    Пропустить тесты (но запустить линтеры)
    --force, -f     Пересоздать виртуальное окружение с нуля
    --ci            CI-режим (без цветов, без интерактивных проверок)
    --verbose, -v   Подробный вывод (показывать stdout зависимостей)
    --no-color      Отключить цветной вывод
    --help, -h      Показать эту справку

Примеры:
    ./scripts/dev/dev_setup.sh              # Полная настройка с проверками
    ./scripts/dev/dev_setup.sh --quick      # Минимальная установка
    ./scripts/dev/dev_setup.sh --force      # Пересоздать окружение с нуля
    ./scripts/dev/dev_setup.sh --ci         # CI: без цветов, non-interactive
    ./scripts/dev/dev_setup.sh -q -f        # Быстрая переустановка

Переменные окружения:
    BIOETL_SKIP_PRECOMMIT=1    Пропустить установку pre-commit hooks
    BIOETL_SKIP_DOCKER=1       Пропустить проверку Docker-сервисов
    NO_COLOR=1                 Отключить цветной вывод (стандарт no-color.org)

Документация:
    docs/03-guides/quick-start.md         Быстрый старт
    docs/00-project/RULES.md              Конституция проекта (v5.23)
    docs/00-project/ai/agents/AGENT.md    Инструкции для разработчика
    docs/00-project/ai/agents/CLAUDE.md   Справочник для Claude Code
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
    # Ищем подходящий Python в порядке приоритета (от новых к старым)
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

# Выполняет python-команду через uv run или напрямую
run_py() {
    if [[ "$HAS_UV" == true ]]; then
        uv run python "$@"
    else
        "$VENV_PYTHON" "$@"
    fi
}

# ==============================================================================
# Парсинг аргументов
# ==============================================================================

parse_args() {
    # Поддержка NO_COLOR из окружения (https://no-color.org/)
    if [[ -n "${NO_COLOR:-}" ]]; then
        NO_COLOR=true
    fi

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
            --ci)
                CI_MODE=true
                NO_COLOR=true
                SKIP_TESTS=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --no-color)
                NO_COLOR=true
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
# Шаг 1: Проверка предварительных требований
# ==============================================================================

step_check_prerequisites() {
    print_header "Шаг 1/9: Проверка предварительных требований"
    local step_start
    step_start=$(now_ms)

    local errors=0
    local warnings=0

    # --- Git ---
    print_step "Проверка Git..."
    if check_command git; then
        local git_ver
        git_ver=$(git --version)
        print_success "Git: $git_ver"
    else
        ((errors++))
    fi

    # --- Make (опционально) ---
    print_step "Проверка Make..."
    if command -v make &> /dev/null; then
        print_success "Make: $(make --version 2>/dev/null | head -1)"
    else
        print_warning "Make не найден. Некоторые команды автоматизации недоступны."
        print_info "Установка: sudo apt install make  |  brew install make"
        ((warnings++))
    fi

    # --- uv (рекомендуемый менеджер) ---
    print_step "Проверка uv..."
    if command -v uv &> /dev/null; then
        HAS_UV=true
        local uv_ver
        uv_ver=$(uv --version 2>/dev/null)
        print_success "uv: $uv_ver"
    else
        print_warning "uv не найден. Будет использован pip (медленнее)."
        print_info "Установка: curl -LsSf https://astral.sh/uv/install.sh | sh"
        ((warnings++))
    fi

    # --- Python ---
    print_step "Поиск Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+..."
    if PYTHON_CMD=$(find_python); then
        print_success "Python: $($PYTHON_CMD --version 2>&1)"
    else
        print_error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ не найден!"
        print_info "Установка: https://www.python.org/downloads/"
        print_info "Или через uv: uv python install 3.12"
        ((errors++))
    fi

    # --- Корень проекта ---
    print_step "Проверка директории проекта..."
    if [[ -f "pyproject.toml" ]] && grep -q 'name = "bioetl"' pyproject.toml 2>/dev/null; then
        print_success "Корень проекта BioETL подтвержден"
    elif [[ -f "pyproject.toml" ]]; then
        print_warning "pyproject.toml найден, но это может быть другой проект"
    else
        print_error "Скрипт должен запускаться из корня проекта BioETL (pyproject.toml не найден)"
        print_info "cd \"$SCRIPT_DIR\"\"
        ((errors++))
    fi

    # --- gh CLI (опционально, для PR workflow) ---
    print_step "Проверка gh CLI (GitHub)..."
    if command -v gh &> /dev/null; then
        print_success "gh: $(gh --version 2>/dev/null | head -1)"
    else
        print_warning "gh CLI не найден. GitHub-операции из командной строки недоступны."
        print_info "Установка: https://cli.github.com/"
        ((warnings++))
    fi

    # --- Docker (опционально) ---
    if [[ "${BIOETL_SKIP_DOCKER:-}" != "1" ]]; then
        print_step "Проверка Docker..."
        if command -v docker &> /dev/null; then
            if docker info &>/dev/null; then
                print_success "Docker: $(docker --version 2>/dev/null | head -1)"
            else
                print_warning "Docker установлен, но демон не запущен"
                ((warnings++))
            fi
        else
            print_warning "Docker не найден. docker-compose сервисы (Neo4j, мониторинг) недоступны."
            ((warnings++))
        fi
    fi

    # --- Node.js / npm (опционально, для диаграмм) ---
    print_step "Проверка Node.js (для Mermaid-диаграмм)..."
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node --version 2>/dev/null)"
        if command -v mmdc &> /dev/null; then
            print_success "mmdc (Mermaid CLI): установлен"
        else
            print_info "mmdc не найден. Установка: npm install -g @mermaid-js/mermaid-cli"
        fi
    else
        print_warning "Node.js не найден. Рендеринг Mermaid-диаграмм недоступен."
        print_info "Необходим только для: make render-diagrams, make diagrams-all"
        ((warnings++))
    fi

    # --- Итог ---
    if [[ $errors -gt 0 ]]; then
        print_error "Обнаружено критических ошибок: $errors. Устраните их и повторите попытку."
        STEP_RESULTS[prerequisites]="FAIL"
        exit 1
    fi

    if [[ $warnings -gt 0 ]]; then
        print_warning "Предупреждений: $warnings (не блокируют установку)"
        STEP_RESULTS[prerequisites]="WARN"
    else
        STEP_RESULTS[prerequisites]="PASS"
    fi

    record_step_time "prerequisites" "$step_start"
}

# ==============================================================================
# Шаг 2: Создание виртуального окружения
# ==============================================================================

step_create_venv() {
    print_header "Шаг 2/9: Создание виртуального окружения"
    local step_start
    step_start=$(now_ms)

    # uv создает venv самостоятельно при sync
    if [[ "$HAS_UV" == true ]]; then
        if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
            print_warning "Удаление существующего окружения (--force)..."
            rm -rf "$VENV_DIR"
        fi
        print_step "uv создаст виртуальное окружение автоматически при установке"
        STEP_RESULTS[venv]="PASS"
        record_step_time "venv" "$step_start"
        return 0
    fi

    if [[ -d "$VENV_DIR" ]]; then
        if [[ "$FORCE" == true ]]; then
            print_warning "Удаление существующего окружения (--force)..."
            rm -rf "$VENV_DIR"
        else
            # Проверяем что существующий venv валиден
            if resolve_venv_python &>/dev/null; then
                print_success "Виртуальное окружение уже существует и валидно: $VENV_DIR"
                print_info "Используйте --force для пересоздания"
                STEP_RESULTS[venv]="PASS"
                record_step_time "venv" "$step_start"
                return 0
            else
                print_warning "Виртуальное окружение повреждено, пересоздаем..."
                rm -rf "$VENV_DIR"
            fi
        fi
    fi

    print_step "Создание виртуального окружения..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    print_success "Виртуальное окружение создано: $VENV_DIR"
    STEP_RESULTS[venv]="PASS"
    record_step_time "venv" "$step_start"
}

# ==============================================================================
# Шаг 3: Установка зависимостей
# ==============================================================================

step_install_dependencies() {
    print_header "Шаг 3/9: Установка зависимостей"
    local step_start
    step_start=$(now_ms)

    local quiet_flag=""
    if [[ "$VERBOSE" != true ]]; then
        quiet_flag="--quiet"
    fi

    if [[ "$HAS_UV" == true ]]; then
        print_step "Установка зависимостей с помощью uv..."
        if uv sync --group dev --extra tracing --extra performance --extra export; then
            print_success "Зависимости установлены через uv"
        else
            print_error "Ошибка установки через uv"
            STEP_RESULTS[dependencies]="FAIL"
            record_step_time "dependencies" "$step_start"
            exit 1
        fi
    else
        VENV_PYTHON=$(resolve_venv_python) || {
            print_error "Не удалось найти python в $VENV_DIR"
            STEP_RESULTS[dependencies]="FAIL"
            record_step_time "dependencies" "$step_start"
            exit 1
        }

        print_step "Обновление pip, setuptools, wheel..."
        "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel $quiet_flag

        print_step "Установка зависимостей разработки..."
        "$VENV_PYTHON" -m pip install -e ".[dev,tracing,performance,export]" $quiet_flag

        print_success "Зависимости установлены через pip"
    fi

    # Определяем venv python для последующих шагов
    VENV_PYTHON=$(resolve_venv_python) || {
        print_error "Не удалось найти python в $VENV_DIR после установки"
        STEP_RESULTS[dependencies]="FAIL"
        record_step_time "dependencies" "$step_start"
        exit 1
    }
    print_step "Venv Python: $($VENV_PYTHON --version 2>&1)"
    STEP_RESULTS[dependencies]="PASS"
    record_step_time "dependencies" "$step_start"
}

# ==============================================================================
# Шаг 4: Настройка pre-commit hooks
# ==============================================================================

step_setup_precommit() {
    print_header "Шаг 4/9: Настройка pre-commit hooks"
    local step_start
    step_start=$(now_ms)

    # Поддержка переменной окружения для пропуска
    if [[ "${BIOETL_SKIP_PRECOMMIT:-}" == "1" ]]; then
        print_warning "Пропущено (BIOETL_SKIP_PRECOMMIT=1)"
        STEP_RESULTS[precommit]="SKIP"
        record_step_time "precommit" "$step_start"
        return 0
    fi

    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        print_warning "Файл .pre-commit-config.yaml не найден, пропускаем"
        STEP_RESULTS[precommit]="SKIP"
        record_step_time "precommit" "$step_start"
        return 0
    fi

    # Проверяем, что мы в git-репозитории
    if ! git rev-parse --git-dir &>/dev/null; then
        print_warning "Не в git-репозитории, пропускаем pre-commit"
        STEP_RESULTS[precommit]="SKIP"
        record_step_time "precommit" "$step_start"
        return 0
    fi

    # Установка pre-commit hooks
    local install_cmd
    if [[ "$HAS_UV" == true ]]; then
        install_cmd="uv run python -m pre_commit"
    else
        install_cmd="$VENV_PYTHON -m pre_commit"
    fi

    if ! $install_cmd --version &>/dev/null; then
        print_step "Установка pre-commit..."
        if [[ "$HAS_UV" == true ]]; then
            uv pip install pre-commit
        else
            "$VENV_PYTHON" -m pip install pre-commit --quiet
        fi
    fi

    print_step "Установка pre-commit hooks..."
    if $install_cmd install --install-hooks 2>/dev/null; then
        print_success "Pre-commit hooks настроены"
        STEP_RESULTS[precommit]="PASS"
    else
        print_warning "pre-commit hooks не установлены"
        STEP_RESULTS[precommit]="WARN"
    fi

    record_step_time "precommit" "$step_start"
}

# ==============================================================================
# Шаг 5: Настройка переменных окружения и директорий
# ==============================================================================

step_setup_env() {
    print_header "Шаг 5/9: Настройка переменных окружения и директорий"
    local step_start
    step_start=$(now_ms)

    # Создание рабочих директорий
    local dirs_created=0
    for dir in data data/bronze data/silver data/gold logs reports; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            ((dirs_created++))
        fi
    done
    if [[ $dirs_created -gt 0 ]]; then
        print_success "Создано директорий: $dirs_created (data/{bronze,silver,gold}, logs, reports)"
    else
        print_success "Все рабочие директории существуют"
    fi

    # .env из примера
    if [[ -f ".env" ]]; then
        print_success "Файл .env уже существует"

        # Проверяем наличие новых переменных в .env.example
        if [[ -f ".env.example" ]]; then
            local missing_vars=0
            while IFS= read -r line; do
                # Пропускаем комментарии и пустые строки
                [[ "$line" =~ ^[[:space:]]*# ]] && continue
                [[ -z "$line" ]] && continue
                local var_name="${line%%=*}"
                if ! grep -q "^${var_name}=" .env 2>/dev/null; then
                    ((missing_vars++))
                fi
            done < .env.example
            if [[ $missing_vars -gt 0 ]]; then
                print_warning "$missing_vars новых переменных в .env.example отсутствуют в .env"
                print_info "Сравните: diff .env.example .env"
            fi
        fi
    elif [[ -f ".env.example" ]]; then
        print_step "Копирование .env.example -> .env..."
        cp .env.example .env
        print_success "Файл .env создан из примера"
        print_warning "Отредактируйте .env для добавления API-ключей при необходимости"
    else
        print_warning "Файл .env.example не найден, пропускаем"
    fi

    # Проверяем .gitignore для .env
    if [[ -f ".gitignore" ]]; then
        if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
            print_warning ".env не в .gitignore! Убедитесь, что секреты не попадут в git."
        fi
    fi

    STEP_RESULTS[env]="PASS"
    record_step_time "env" "$step_start"
}

# ==============================================================================
# Шаг 6: Проверка MCP/AI-инструментов
# ==============================================================================

step_check_ai_tools() {
    print_header "Шаг 6/9: Проверка AI-инструментов"
    local step_start
    step_start=$(now_ms)

    local found_tools=0

    # Claude Code
    if command -v claude &> /dev/null; then
        print_success "Claude Code CLI: установлен"
        ((found_tools++))
    fi

    # Codex
    if command -v codex &> /dev/null; then
        print_success "Codex CLI: установлен"
        ((found_tools++))

        # MCP preflight
        if [[ -x "scripts/ops/check_mcp.sh" ]]; then
            print_step "Проверка MCP-конфигурации..."
            if bash scripts/ops/check_mcp.sh 2>/dev/null; then
                print_success "MCP-конфигурация валидна"
            else
                print_warning "MCP-конфигурация: обнаружены проблемы"
            fi
        fi
    fi

    # Проверяем .claude/ конфигурацию
    if [[ -d ".claude" ]]; then
        local agent_count
        agent_count=$(find .claude/agents -name "*.md" 2>/dev/null | wc -l)
        local skill_count
        skill_count=$(find .claude/skills -name "SKILL.md" 2>/dev/null | wc -l)
        local cmd_count
        cmd_count=$(find .claude/commands -name "*.md" 2>/dev/null | wc -l)
        print_success "Claude конфигурация: $agent_count агентов, $skill_count скиллов, $cmd_count команд"
    fi

    if [[ $found_tools -eq 0 ]]; then
        print_info "AI CLI не найдены (claude, codex). Это не блокирует разработку."
    fi

    STEP_RESULTS[ai_tools]="PASS"
    record_step_time "ai_tools" "$step_start"
}

# ==============================================================================
# Шаг 7: Проверка установки
# ==============================================================================

step_verify_installation() {
    print_header "Шаг 7/9: Проверка установки"
    local step_start
    step_start=$(now_ms)
    local has_errors=false

    # Импорт основного модуля
    print_step "Проверка импорта bioetl..."
    if run_py -c "import bioetl; print(f'BioETL v{bioetl.__version__}')" 2>/dev/null; then
        print_success "Модуль bioetl импортируется корректно"
    else
        print_error "Ошибка импорта модуля bioetl"
        has_errors=true
    fi

    # Критические runtime-зависимости
    print_step "Проверка критических зависимостей..."
    if run_py -c "
import pandas, pandera, deltalake, polars, httpx, pydantic, structlog
print(f'  pandas={pandas.__version__}, polars={polars.__version__}')
print(f'  pandera={pandera.__version__}, deltalake={deltalake.__version__}')
print(f'  httpx={httpx.__version__}, pydantic={pydantic.__version__}')
" 2>/dev/null; then
        print_success "Критические зависимости доступны"
    else
        print_error "Критические зависимости не найдены!"
        has_errors=true
    fi

    # Dev-зависимости
    print_step "Проверка dev-зависимостей..."
    local dev_ok=true
    for tool in ruff mypy; do
        if run_py -m $tool --version &>/dev/null; then
            print_success "  $tool: $(run_py -m $tool --version 2>/dev/null | head -1)"
        else
            print_warning "  $tool: не найден"
            dev_ok=false
        fi
    done
    if run_py -c "import pytest; print(f'  pytest: {pytest.__version__}')" 2>/dev/null; then
        true  # already printed
    else
        print_warning "  pytest: не найден"
        dev_ok=false
    fi

    # CLI
    print_step "Проверка CLI..."
    if run_py -m bioetl --help &>/dev/null; then
        print_success "CLI работает корректно"
    else
        print_warning "CLI недоступен (возможно, требуется настройка)"
    fi

    if [[ "$has_errors" == true ]]; then
        STEP_RESULTS[verify]="FAIL"
        print_error "Критические ошибки при проверке установки"
        record_step_time "verify" "$step_start"
        exit 1
    elif [[ "$dev_ok" != true ]]; then
        STEP_RESULTS[verify]="WARN"
    else
        STEP_RESULTS[verify]="PASS"
    fi

    record_step_time "verify" "$step_start"
}

# ==============================================================================
# Шаг 8: Запуск проверок качества
# ==============================================================================

step_run_checks() {
    print_header "Шаг 8/9: Запуск проверок качества"
    local step_start
    step_start=$(now_ms)

    if [[ "$QUICK_MODE" == true ]]; then
        print_warning "Быстрый режим: проверки пропущены (--quick)"
        STEP_RESULTS[checks]="SKIP"
        record_step_time "checks" "$step_start"
        return 0
    fi

    local check_warnings=0

    # Ruff check
    print_step "Запуск ruff check..."
    if run_py -m ruff check src/ tests/ --quiet 2>/dev/null; then
        print_success "Ruff check: без ошибок"
    else
        print_warning "Ruff check: обнаружены проблемы (make lint-fix)"
        ((check_warnings++))
    fi

    # Ruff format
    print_step "Проверка форматирования..."
    if run_py -m ruff format --check src/ tests/ --quiet 2>/dev/null; then
        print_success "Ruff format: код отформатирован"
    else
        print_warning "Ruff format: проблемы форматирования (make lint-fix)"
        ((check_warnings++))
    fi

    # mypy
    print_step "Запуск mypy..."
    if run_py -m mypy src/bioetl --no-error-summary 2>/dev/null; then
        print_success "Mypy: без ошибок"
    else
        print_warning "Mypy: обнаружены проблемы с типами"
        ((check_warnings++))
    fi

    # Architecture tests
    print_step "Запуск architecture тестов..."
    if run_py -m pytest tests/architecture/ -q --tb=line 2>/dev/null; then
        print_success "Architecture tests: без нарушений"
    else
        print_warning "Architecture tests: обнаружены нарушения"
        ((check_warnings++))
    fi

    # Smoke tests (быстрые)
    print_step "Запуск smoke тестов..."
    if run_py -m pytest tests/smoke/ -q --tb=short 2>/dev/null; then
        print_success "Smoke tests: пройдены"
    else
        print_warning "Smoke tests: есть проблемы"
        ((check_warnings++))
    fi

    # Полные тесты
    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Полные тесты пропущены (--skip-tests)"
    else
        print_step "Запуск полного набора тестов..."
        if run_py -m pytest tests/ -p no:xdist -m "not e2e and not benchmark and not slow" -q --tb=short 2>/dev/null; then
            print_success "Все тесты пройдены"
        else
            print_warning "Некоторые тесты не прошли (проверьте: make test)"
            ((check_warnings++))
        fi
    fi

    if [[ $check_warnings -gt 0 ]]; then
        STEP_RESULTS[checks]="WARN"
        print_warning "Предупреждений: $check_warnings (не блокируют работу)"
    else
        STEP_RESULTS[checks]="PASS"
    fi

    record_step_time "checks" "$step_start"
}

# ==============================================================================
# Шаг 9: Настройка плагинов и навыков (setup_plugins + setup_skills)
# ==============================================================================

step_setup_plugins() {
    print_header "Шаг 9/9: Настройка плагинов"
    local step_start
    step_start=$(now_ms)

    # setup_plugins.sh
    if [[ -f "scripts/ops/setup_plugins.sh" ]]; then
        print_step "Запуск setup_plugins.sh --pytest-only..."
        if bash scripts/ops/setup_plugins.sh --pytest-only 2>/dev/null; then
            print_success "Pytest плагины настроены"
        else
            print_warning "Проблемы с настройкой pytest-плагинов"
        fi
    fi

    # setup_skills.sh (только если codex/claude установлен)
    if command -v codex &>/dev/null || command -v claude &>/dev/null; then
        if [[ -f "scripts/ops/setup_skills.sh" ]]; then
            print_step "Синхронизация навыков (setup_skills.sh)..."
            if bash scripts/ops/setup_skills.sh 2>/dev/null; then
                print_success "Навыки синхронизированы"
            else
                print_warning "Проблемы с синхронизацией навыков"
            fi
        fi
    fi

    STEP_RESULTS[plugins]="PASS"
    record_step_time "plugins" "$step_start"
}

# ==============================================================================
# Итоговая таблица результатов
# ==============================================================================

print_summary_table() {
    echo ""
    echo -e "${BOLD}Результаты настройки:${NC}"
    echo "  ──────────────────────────────────────────"

    local step_names=("prerequisites" "venv" "dependencies" "precommit" "env" "ai_tools" "verify" "checks" "plugins")
    local step_labels=("Предварительные требования" "Виртуальное окружение" "Зависимости" "Pre-commit hooks" "Окружение (.env, dirs)" "AI-инструменты" "Проверка установки" "Проверки качества" "Плагины")

    for i in "${!step_names[@]}"; do
        local name="${step_names[$i]}"
        local label="${step_labels[$i]}"
        local result="${STEP_RESULTS[$name]:-N/A}"
        local icon=""

        case "$result" in
            PASS) icon="${GREEN}PASS${NC}" ;;
            WARN) icon="${YELLOW}WARN${NC}" ;;
            FAIL) icon="${RED}FAIL${NC}" ;;
            SKIP) icon="${DIM}SKIP${NC}" ;;
            *)    icon="${DIM}----${NC}" ;;
        esac

        printf "  %-28s %b\n" "$label" "$icon"
    done

    echo "  ──────────────────────────────────────────"

    # Timing
    if [[ ${#STEP_TIMINGS[@]} -gt 0 ]]; then
        echo ""
        echo -e "${DIM}Время выполнения:${NC}"
        for entry in "${STEP_TIMINGS[@]}"; do
            local step_name="${entry%%|*}"
            local step_time="${entry##*|}"
            printf "  ${DIM}%-28s %s${NC}\n" "$step_name" "$step_time"
        done
    fi

    # Общее время
    if [[ -n "$SETUP_START_TIME" ]]; then
        local total_end
        total_end=$(now_ms)
        local total_ms=$(( total_end - SETUP_START_TIME ))
        local total_s=$(( total_ms / 1000 ))
        echo ""
        echo -e "${BOLD}Общее время: ${total_s}s${NC}"
    fi
}

# ==============================================================================
# Финальные инструкции
# ==============================================================================

print_final_instructions() {
    print_header "Окружение разработки настроено"

    print_summary_table

    echo ""
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

3. Основные команды:
   ${BLUE}make help${NC}              Список всех команд
   ${BLUE}make test${NC}              Запуск тестов
   ${BLUE}make test-quick${NC}        Быстрые тесты (fastest)
   ${BLUE}make lint${NC}              Проверка кода
   ${BLUE}make lint-fix${NC}          Автоисправление
   ${BLUE}make arch-test${NC}         Архитектурные тесты
   ${BLUE}make run-local${NC}         Запуск пайплайна на фикстурах
   ${BLUE}make docs-serve${NC}        Локальный просмотр документации
   ${BLUE}make security${NC}          Аудит безопасности

4. Документация:
   ${YELLOW}docs/03-guides/quick-start.md${NC}         Быстрый старт
   ${YELLOW}docs/00-project/RULES.md${NC}              Конституция проекта (v5.23)
   ${YELLOW}docs/00-project/ai/agents/AGENT.md${NC}    Инструкции для разработчика
   ${YELLOW}docs/00-project/ai/agents/CLAUDE.md${NC}   Справочник для Claude Code

EOF
    else
        cat << EOF

${GREEN}Следующие шаги:${NC}

1. Активируйте виртуальное окружение:
   ${BLUE}source ${activate_path}${NC}

2. Проверьте статус проекта:
   ${BLUE}make lint && make test${NC}

3. Основные команды:
   ${BLUE}make help${NC}              Список всех команд
   ${BLUE}make test${NC}              Запуск тестов
   ${BLUE}make test-quick${NC}        Быстрые тесты (fastest)
   ${BLUE}make lint${NC}              Проверка кода
   ${BLUE}make lint-fix${NC}          Автоисправление
   ${BLUE}make arch-test${NC}         Архитектурные тесты
   ${BLUE}make run-local${NC}         Запуск пайплайна на фикстурах
   ${BLUE}make docs-serve${NC}        Локальный просмотр документации
   ${BLUE}make security${NC}          Аудит безопасности

4. Документация:
   ${YELLOW}docs/03-guides/quick-start.md${NC}         Быстрый старт
   ${YELLOW}docs/00-project/RULES.md${NC}              Конституция проекта (v5.23)
   ${YELLOW}docs/00-project/ai/agents/AGENT.md${NC}    Инструкции для разработчика
   ${YELLOW}docs/00-project/ai/agents/CLAUDE.md${NC}   Справочник для Claude Code

EOF
    fi
}

# ==============================================================================
# Главная функция
# ==============================================================================

main() {
    parse_args "$@"
    setup_colors

    print_header "BioETL v6.0.0 — Настройка окружения разработки"
    SETUP_START_TIME=$(now_ms)

    # Переходим в корень проекта
    cd "$REPO_ROOT"

    step_check_prerequisites      # 1/9
    step_create_venv              # 2/9
    step_install_dependencies     # 3/9
    step_setup_precommit          # 4/9
    step_setup_env                # 5/9
    step_check_ai_tools           # 6/9
    step_verify_installation      # 7/9
    step_run_checks               # 8/9
    step_setup_plugins            # 9/9
    print_final_instructions
}

# Запуск
main "$@"
