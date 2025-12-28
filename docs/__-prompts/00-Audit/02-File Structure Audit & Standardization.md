# BioETL Structure Audit & Standardization Prompt
*Version 1.0 | Aligned with RULES.md v5.0*

## Цель

Провести аудит структуры проекта BioETL и привести её в соответствие с File Policy (03-file-policy.md) и Physical Layout (05-physical-layout.md).

---

## 1. Допустимые Корневые Каталоги (MUST)

### 1.1. Whitelist

Разрешённые папки в корне репозитория:

| Каталог | Назначение |
|---------|------------|
| `src/` | Исходный код (bioetl, tools) |
| `tests/` | Тесты (зеркалят src/) |
| `docs/` | Документация |
| `configs/` | Runtime конфигурации (YAML) |
| `data/` | Данные (Bronze/Silver/Gold) |
| `qc/` | Quality Control артефакты |
| `.github/` | GitHub workflows |
| `.cursor/` | Cursor rules |
| `.trae/` | Trae rules |
| `.windsurf/` | Windsurf rules |
| `reports/` | Временные отчёты (не коммитятся) |
| `scripts/` | Операционные скрипты (vacuum, salt rotation) |

### 1.2. Запрещённые действия

- Создание новых папок в корне **MUST NOT**
- Утилиты и скрипты вне `src/tools/` или `scripts/` **MUST NOT**

---

## 2. Структура Кода (MUST)

### 2.1. Допустимые расположения Python-кода

```
src/
├── bioetl/              # Основной пакет
│   ├── domain/          # Чистая логика, Protocols, схемы
│   ├── application/     # Пайплайны, use cases
│   ├── infrastructure/  # Адаптеры (HTTP, Storage, Locking)
│   └── interfaces/      # CLI (Typer)
│
└── tools/               # Утилиты проекта
    ├── cleanup_project.py
    └── ...

tests/                   # Тесты (зеркалят src/)
├── unit/
├── integration/
├── contract/
└── golden/

scripts/                 # Операционные скрипты
├── vacuum_delta.py
├── salt_rotate.py
└── dq_baseline_update.py
```

### 2.2. Запрещённые расположения кода

| Путь | Причина |
|------|---------|
| `docs/*.py` | Документация, не код |
| `configs/*.py` | YAML конфигурации, не код |
| `data/*.py` | Данные, не код |
| Корень репозитория `*.py` | Только setup.py, conftest.py допустимы |
| `notebooks/` (если есть) | Переместить в `src/tools/` или удалить |

---

## 3. Команды Аудита

### 3.1. Поиск Python-файлов в неположенных местах

```bash
# Найти все .py файлы вне допустимых директорий
find . -name "*.py" \
  -not -path "./src/*" \
  -not -path "./tests/*" \
  -not -path "./scripts/*" \
  -not -path "./.venv/*" \
  -not -path "./venv/*" \
  -not -path "./.git/*" \
  -not -path "./build/*" \
  -not -path "./dist/*" \
  -not -name "setup.py" \
  -not -name "conftest.py" \
  -not -name "__init__.py" \
  2>/dev/null
```

### 3.2. Проверка корневых каталогов

```bash
# Вывести только директории верхнего уровня
ls -d */ 2>/dev/null | grep -v -E "^(src|tests|docs|configs|data|qc|scripts|reports|\.github|\.cursor|\.trae|\.windsurf|\.venv|venv|build|dist|\.git|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|htmlcov|\.egg-info)/"
```

### 3.3. Проверка структуры src/bioetl

```bash
# Должны быть только эти папки
ls src/bioetl/ | grep -v -E "^(domain|application|infrastructure|interfaces|__pycache__|__init__\.py|py\.typed)$"
```

### 3.4. Проверка именования документации

```bash
# Найти .md файлы с неправильным именованием (не kebab-case)
find docs/ -name "*.md" | grep -E "[A-Z]|_" | grep -v -E "(README|INDEX|CHANGELOG|ADR)"
```

---

## 4. Чек-лист Аудита

### 4.1. Структура каталогов

- [ ] В корне только допустимые папки (§1.1)
- [ ] `src/bioetl/` содержит только domain, application, infrastructure, interfaces
- [ ] `src/tools/` существует для утилит
- [ ] `scripts/` для операционных скриптов (vacuum, rotation)
- [ ] `tests/` зеркалит структуру `src/`

### 4.2. Расположение кода

- [ ] Нет `.py` файлов в `docs/`
- [ ] Нет `.py` файлов в `configs/`
- [ ] Нет `.py` файлов в `data/`
- [ ] Нет `.py` файлов в корне (кроме setup.py, conftest.py)
- [ ] Нет `.py` файлов в `notebooks/` (если существует — мигрировать или удалить)

### 4.3. Именование файлов

- [ ] Документация: kebab-case (`01-getting-started.md`)
- [ ] Модули Python: snake_case (`unified_api_client.py`)
- [ ] Классы: PascalCase + суффикс (`ChemblDataClientImpl`)
- [ ] Тесты: `test_*.py`
- [ ] ADR: `NNNN-title-in-kebab-case.md`

### 4.4. Структура configs/

- [ ] `configs/pipelines/{provider}/{entity}.yaml`
- [ ] `configs/providers/{provider}.yaml`
- [ ] Нет Python-кода

### 4.5. Структура docs/

- [ ] `docs/application/pipelines/{provider}/{entity}/`
- [ ] `docs/architecture/decisions/` для ADR
- [ ] `docs/contracts/gold/` для Data Contracts
- [ ] `docs/templates/` для шаблонов

---

## 5. Скрипт Автоматической Проверки

Создать `src/tools/audit_structure.py`:

```python
#!/usr/bin/env python3
"""
BioETL Structure Audit Tool.

Проверяет соответствие структуры проекта File Policy.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator

# Допустимые корневые каталоги
ALLOWED_ROOT_DIRS = {
    "src", "tests", "docs", "configs", "data", "qc", "scripts", "reports",
    ".github", ".cursor", ".trae", ".windsurf",
    # Технические (генерируемые)
    ".venv", "venv", "build", "dist", ".git", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov",
    ".eggs", "*.egg-info",
}

# Допустимые расположения Python-кода
ALLOWED_PYTHON_PATHS = {
    "src/",
    "tests/",
    "scripts/",
}

# Допустимые Python-файлы в корне
ALLOWED_ROOT_PY_FILES = {
    "setup.py",
    "conftest.py",
    "pyproject.toml",  # не .py, но для полноты
}

# Структура src/bioetl
REQUIRED_BIOETL_LAYERS = {
    "domain",
    "application", 
    "infrastructure",
    "interfaces",
}


@dataclass
class Violation:
    """Нарушение политики."""
    category: str
    path: str
    message: str
    severity: str  # MUST | SHOULD


def find_violations(project_root: Path) -> Iterator[Violation]:
    """Найти все нарушения File Policy."""
    
    # 1. Проверка корневых каталогов
    for item in project_root.iterdir():
        if item.is_dir():
            name = item.name
            if name.startswith("."):
                # Скрытые папки проверяем по whitelist
                if name not in {".github", ".cursor", ".trae", ".windsurf", 
                               ".venv", ".git", ".pytest_cache", ".mypy_cache", 
                               ".ruff_cache", ".eggs"}:
                    yield Violation(
                        category="ROOT_DIR",
                        path=str(item),
                        message=f"Неразрешённая скрытая папка в корне: {name}",
                        severity="SHOULD",
                    )
            elif name not in ALLOWED_ROOT_DIRS and not name.endswith(".egg-info"):
                yield Violation(
                    category="ROOT_DIR",
                    path=str(item),
                    message=f"Неразрешённая папка в корне: {name}",
                    severity="MUST",
                )
    
    # 2. Проверка Python-файлов в неположенных местах
    for py_file in project_root.rglob("*.py"):
        rel_path = py_file.relative_to(project_root)
        str_path = str(rel_path)
        
        # Пропускаем технические директории
        if any(part in str_path for part in [".venv", "venv", ".git", "build", 
                                              "dist", "__pycache__", ".egg"]):
            continue
        
        # Проверяем допустимость
        is_allowed = any(str_path.startswith(p) for p in ALLOWED_PYTHON_PATHS)
        is_root_allowed = py_file.parent == project_root and py_file.name in ALLOWED_ROOT_PY_FILES
        
        if not is_allowed and not is_root_allowed:
            yield Violation(
                category="PYTHON_LOCATION",
                path=str_path,
                message=f"Python-файл в недопустимом месте: {str_path}",
                severity="MUST",
            )
    
    # 3. Проверка структуры src/bioetl
    bioetl_path = project_root / "src" / "bioetl"
    if bioetl_path.exists():
        existing_layers = {
            d.name for d in bioetl_path.iterdir() 
            if d.is_dir() and not d.name.startswith("_")
        }
        
        missing = REQUIRED_BIOETL_LAYERS - existing_layers
        for layer in missing:
            yield Violation(
                category="LAYER_MISSING",
                path=f"src/bioetl/{layer}/",
                message=f"Отсутствует обязательный слой: {layer}",
                severity="MUST",
            )
        
        extra = existing_layers - REQUIRED_BIOETL_LAYERS
        for layer in extra:
            yield Violation(
                category="LAYER_EXTRA",
                path=f"src/bioetl/{layer}/",
                message=f"Неожиданный каталог в src/bioetl/: {layer}",
                severity="SHOULD",
            )
    
    # 4. Проверка docs/ на Python-файлы
    docs_path = project_root / "docs"
    if docs_path.exists():
        for py_file in docs_path.rglob("*.py"):
            yield Violation(
                category="DOCS_CODE",
                path=str(py_file.relative_to(project_root)),
                message="Python-код в docs/ запрещён",
                severity="MUST",
            )
    
    # 5. Проверка configs/ на Python-файлы
    configs_path = project_root / "configs"
    if configs_path.exists():
        for py_file in configs_path.rglob("*.py"):
            yield Violation(
                category="CONFIGS_CODE",
                path=str(py_file.relative_to(project_root)),
                message="Python-код в configs/ запрещён",
                severity="MUST",
            )


def main():
    """Entry point."""
    project_root = Path.cwd()
    
    violations = list(find_violations(project_root))
    
    must_violations = [v for v in violations if v.severity == "MUST"]
    should_violations = [v for v in violations if v.severity == "SHOULD"]
    
    print("=" * 60)
    print("BioETL Structure Audit Report")
    print("=" * 60)
    print()
    
    if must_violations:
        print(f"## MUST Violations ({len(must_violations)})")
        print()
        for v in must_violations:
            print(f"  [{v.category}] {v.path}")
            print(f"    → {v.message}")
        print()
    
    if should_violations:
        print(f"## SHOULD Violations ({len(should_violations)})")
        print()
        for v in should_violations:
            print(f"  [{v.category}] {v.path}")
            print(f"    → {v.message}")
        print()
    
    if not violations:
        print("✓ Структура проекта соответствует File Policy")
        print()
    
    print("=" * 60)
    print(f"Total: {len(must_violations)} MUST, {len(should_violations)} SHOULD")
    print("=" * 60)
    
    # Exit code: 1 если есть MUST violations
    sys.exit(1 if must_violations else 0)


if __name__ == "__main__":
    main()
```

---

## 6. Миграционный План

### 6.1. Перемещение кода

При обнаружении кода в неположенных местах:

```bash
# Пример: перемещение notebook в tools
git mv notebooks/data_exploration.py src/tools/data_exploration.py

# Пример: перемещение скрипта из корня
git mv run_pipeline.py src/tools/run_pipeline.py

# Пример: перемещение скрипта в scripts/
git mv vacuum_tables.py scripts/vacuum_delta.py
```

### 6.2. Обновление импортов

После перемещения обновить импорты:

```bash
# Найти все импорты перемещённого модуля
grep -r "from old_location import" src/ tests/
grep -r "import old_location" src/ tests/
```

### 6.3. Обновление документации

- Обновить `docs/00-map.md` при изменении структуры
- Добавить запись в `CHANGELOG.md`

---

## 7. CI Интеграция

### 7.1. Добавить workflow `.github/workflows/structure-audit.yml`

```yaml
name: Structure Audit

on:
  pull_request:
    paths:
      - '**/*.py'
      - 'docs/**'
      - 'configs/**'

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run Structure Audit
        run: python src/tools/audit_structure.py
```

### 7.2. Pre-commit hook

Добавить в `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: structure-audit
        name: Structure Audit
        entry: python src/tools/audit_structure.py
        language: python
        pass_filenames: false
        always_run: true
```

---

## 8. Исключения и Обоснования

Если необходимо отклонение от политики, документировать в ADR:

```markdown
# ADR-XXXX: Исключение для <path>

## Статус
Принято

## Контекст
<почему нужно исключение>

## Решение
<что разрешено и почему>

## Последствия
<ограничения исключения>
```

---

## TL;DR

1. **Код только в**: `src/bioetl/`, `src/tools/`, `tests/`, `scripts/`
2. **Документация только в**: `docs/`
3. **Конфигурации только в**: `configs/`
4. **Корневые папки**: whitelist из §1.1
5. **Автоматизация**: `src/tools/audit_structure.py` + CI + pre-commit
6. **Нарушения**: MUST = блокер, SHOULD = требует обоснования