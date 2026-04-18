# Сравнение: script-mistrallvibe vs scripts/dev/

## Архитектура

### `scripts/dev/` (Canonical Scripts Pattern)
```
scripts/
├── run.py                      # Universal launcher (список всех скриптов по группам)
└── dev/
    ├── __main__.py             # Entry point: python -m scripts.dev <cmd>
    ├── install_deps.py         # Scripts (Python, Shell)
    ├── run_tests.py
    ├── pretest_guardrails.sh
    └── ... (другие скрипты)
```

**Принцип:**
- Единая точка входа через `__main__.py`
- Маршрутизация команд в словари: `COMMANDS` (Python) и `SHELL_COMMANDS` (Bash)
- Динамическое обнаружение скриптов в группах (ci, dev, qa, etc.)
- Unified launcher `scripts/run.py` для всех групп

### `script-mistrallvibe/` (Simple Wrapper Pattern)
```
script-mistrallvibe/
├── run-mistrallvibe.ps1        # Windows entry point
├── run-mistrallvibe.sh         # Linux/WSL entry point
├── vibe-cli.py                 # Direct executable
├── vibe-server.js              # Direct executable
└── helper/
    ├── check-env.*.ps1/.sh     # Sub-helpers
    ├── setup-env.*.ps1/.sh
    └── run-mistrallvibe-impl.*.ps1/.sh
```

**Принцип:**
- Отдельные entry points для каждой ОС (PS1, SH)
- Helper scripts для модульности
- Прямые исполняемые скрипты (CLI, server)

---

## Запуск

### `scripts/dev/` (Единая команда для всех скриптов)

```bash
# Python скрипт
python -m scripts.dev install-deps
python -m scripts.dev run-tests
python -m scripts.dev probe-quality

# Bash скрипт
python -m scripts.dev setup
python -m scripts.dev pretest-guardrails
python -m scripts.dev pytest-sharded

# Специальные команды
python -m scripts.dev test-changed
python -m scripts.dev help
```

**Особенности:**
✓ Все команды через один интерфейс (`python -m scripts.dev`)
✓ Скрипты не нужно делать исполняемыми
✓ Кроссплатформенно (работает везде через Python)
✓ Автоматическая маршрутизация

### `script-mistrallvibe/` (Отдельные entry points)

```bash
# Linux/WSL
./run-mistrallvibe.sh chat large
./run-mistrallvibe.sh start
./run-mistrallvibe.sh status

# Windows (PowerShell)
.\run-mistrallvibe.ps1 chat large
.\run-mistrallvibe.ps1 start
.\run-mistrallvibe.ps1 status

# Прямой запуск (любая ОС)
python vibe-cli.py large
node vibe-server.js
```

**Особенности:**
✓ Отдельные скрипты для каждой ОС
✓ Прямой запуск исполняемых файлов
✓ Удобно для разработки (отладка отдельных частей)
✗ Требует разных команд для Windows/Linux

---

## Модульность

### `scripts/dev/`

```python
COMMANDS = {
    "install-deps": "install_deps.py",      # Имя файла -> Исполняемый скрипт
    "run-tests": "run_tests.py",
    "setup-mcp": "setup_copilot_codex_mcp.py",
}

SHELL_COMMANDS = {
    "setup": "dev_setup.sh",                 # Bash скрипты отдельно
    "pretest-guardrails": "pretest_guardrails.sh",
}
```

**Способ вызова:**
```python
def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode
```

**Плюсы:**
- Декларативная регистрация команд
- Легко добавлять новые команды (просто добавь в словарь)
- Явное разделение Python и Bash скриптов

### `script-mistrallvibe/`

```bash
# В run-mistrallvibe.ps1 / run-mistrallvibe.sh
case "$COMMAND" in
    start)
        bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" start "$@"
        ;;
    
    chat|cli)
        python vibe-cli.py @Args
        ;;
    
    stop)
        bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" stop "$@"
        ;;
esac
```

**Плюсы:**
- Императивный подход (видно что происходит)
- Прямой контроль над вызовом
- Легче отладить для конкретной задачи

---

## Преимущества и недостатки

### `scripts/dev/` (Canonical Pattern)

| Плюсы | Минусы |
|-------|--------|
| ✓ Единый интерфейс для всех скриптов | ✗ Нужно учить новый паттерн |
| ✓ Кроссплатформенность (Python везде) | ✗ Все скрипты должны быть в одном месте |
| ✓ Масштабируемость (легко добавлять) | ✗ Сложнее для одиночных инструментов |
| ✓ Декларативный подход | ✗ Требует Python для запуска |
| ✓ Динамическое обнаружение (`find`) | |

**Когда использовать:**
- Много скриптов разного типа
- Нужна единая точка входа
- Разработка в одной группе (dev, qa, ops)
- Масштабируемый проект

### `script-mistrallvibe/` (Simple Wrapper Pattern)

| Плюсы | Минусы |
|-------|--------|
| ✓ Простота (нет абстракций) | ✗ Разные команды для Windows/Linux |
| ✓ Прямой запуск скриптов | ✗ Сложнее масштабировать |
| ✓ Возможность прямого вызова (python/node) | ✗ Нужны права на execute |
| ✓ Отладка отдельных частей | ✗ Дублирование логики |
| ✓ Минимум зависимостей | |

**Когда использовать:**
- Один инструмент / одна задача
- Нужна гибкость в вызове
- Разработка определённого компонента
- Минимум сложности

---

## Как переделать script-mistrallvibe под canonical pattern

### Вариант 1: Минимальный (используй существующие скрипты)

```python
# script-mistrallvibe/__main__.py
"""Mistral Vibe commands"""

import subprocess
import sys
from pathlib import Path

COMMANDS = {
    "chat": "vibe-cli.py",
    "server": "vibe-server.js",
}

SHELL_COMMANDS = {
    "setup": "helper/setup-env.sh",
    "check": "helper/check-env.sh",
}

_DIR = Path(__file__).parent

def main(argv=None):
    args = argv or sys.argv[1:]
    if not args:
        print("Usage: python -m script_mistrallvibe <command> [args...]")
        return 2
    
    cmd, rest = args[0], args[1:]
    
    if cmd in COMMANDS:
        script = _DIR / COMMANDS[cmd]
        return subprocess.run([sys.executable, str(script), *rest]).returncode
    
    if cmd in SHELL_COMMANDS:
        script = _DIR / SHELL_COMMANDS[cmd]
        return subprocess.run(["bash", str(script), *rest]).returncode
    
    print(f"Unknown command: {cmd}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
```

**Использование:**
```bash
python -m script_mistrallvibe chat large
python -m script_mistrallvibe server
python -m script_mistrallvibe check
```

### Вариант 2: Добавить в scripts/run.py

```python
# Добавить в scripts/run.py
CANONICAL_GROUPS: tuple[str, ...] = (
    # ... существующие ...
    "ai-tools",  # Новая группа
)

# Затем
python scripts/run.py exec ai-tools vibe chat large
```

---

## Рекомендация

Для `script-mistrallvibe` оптимально оставить **Simple Wrapper Pattern** потому что:

1. ✓ Это **один инструмент** (Mistral Vibe), не группа скриптов
2. ✓ Нужна **гибкость в вызове** (server, cli, browser)
3. ✓ Простота и минимум зависимостей
4. ✓ Удобство отладки отдельных компонентов

Но если добавлять **другие AI инструменты** (Gemini, Codex, итак есть):
- Создать группу `scripts/ai-tools/` 
- Переделать под canonical pattern
- Запускать через `python scripts/run.py exec ai-tools vibe chat large`
