# Naming Compliance Audit Prompt
*BioETL Project — RULES.md v5.0 Alignment*

## Цель

Провести полный аудит наименований сущностей проекта на соответствие политике именования (§2 RULES.md, 01-project-rules.md §2). Сформировать перечень нарушений с рекомендациями по переименованию.

---

## 1. Правила именования (Reference)

### 1.1. Классы (PascalCase + обязательные суффиксы)

| Роль | Суффикс | Пример |
|------|---------|--------|
| Фабрика | `*Factory` | `ChemblClientFactory` |
| Клиент API | `*Client` | `ChemblDataClient` |
| Фасад | `*Facade` | `PipelineRunnerFacade` |
| Реестр | `*Registry` | `SchemaRegistry` |
| Адаптер | `*Adapter` | `HTTPTransportAdapter` |
| Интерфейс/Protocol | `*Protocol` / `*ABC` | `DataClientProtocol` |
| Конфигурация | `*Config` / `*Model` / `*Params` | `PipelineConfig` |
| Исключение | `*Error` | `SchemaValidationError` |
| Реализация | `*Impl` | `ChemblDataClientHTTPImpl` |
| Сервис | `*Service` | `HashService`, `ValidationService` |
| Writer | `*Writer` | `DeltaLakeWriter`, `BronzeWriter` |

**Нарушения для поиска**:
- Классы без соответствующего суффикса
- camelCase вместо PascalCase
- Несоответствие роли и суффикса

### 1.2. Модули/файлы (snake_case)

| Тип | Формат | Пример |
|-----|--------|--------|
| Python-модуль | `snake_case.py` | `unified_api_client.py` |
| Документация | `kebab-case.md` | `01-pipeline-overview.md` |
| Конфиг YAML | `snake_case.yaml` | `chembl_activity.yaml` |

### 1.3. Функции/методы (snake_case + префиксы)

| Тип функции | Префикс | Пример |
|-------------|---------|--------|
| Чтение локальных данных | `get_` | `get_local_config()` |
| Сетевые запросы | `fetch_` | `fetch_chembl_page()` |
| Генераторы | `iter_` | `iter_batches()` |
| Создание объектов | `create_` / `build_` / `make_` / `default_` | `build_pipeline()` |
| Регистрация | `register_` | `register_schema()` |
| Валидация | `validate_` | `validate_dataframe()` |
| Парсинг | `parse_` / `serialize_` | `parse_response()` |
| Обработчики | `on_` | `on_pipeline_error()` |
| Булевы проверки | `is_` / `has_` / `can_` | `is_valid()` |
| Приватные | `_` prefix | `_normalize_value()` |

### 1.4. Переменные и константы

| Тип | Формат | Пример |
|-----|--------|--------|
| Переменная | `snake_case` | `batch_size` |
| Константа | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Приватный атрибут | `_snake_case` | `_client` |

### 1.5. Пайплайны и сущности

| Артефакт | Формат | Пример |
|----------|--------|--------|
| ID пайплайна | `{entity}_{provider}` | `activity_chembl` |
| Папка пайплайна | `{provider}/{entity}/` | `chembl/activity/` |
| Стадии | `extract.py`, `transform.py`, `validate.py`, `export.py` | — |

---

## 2. Инструкции по анализу

### 2.1. Сбор данных

Выполнить для каждой категории:
```bash
# 1. Собрать все Python-классы
grep -rn "^class " src/bioetl/ --include="*.py" | \
  awk -F: '{print $1":"$2":"$3}' > /tmp/classes.txt

# 2. Собрать все функции/методы  
grep -rn "^\s*def " src/bioetl/ --include="*.py" | \
  awk -F: '{print $1":"$2":"$3}' > /tmp/functions.txt

# 3. Собрать все Python-файлы
find src/bioetl/ -name "*.py" -type f > /tmp/modules.txt

# 4. Собрать документацию
find docs/ -name "*.md" -type f > /tmp/docs.txt

# 5. Собрать конфиги
find configs/ -name "*.yaml" -type f > /tmp/configs.txt

# 6. Собрать тесты
find tests/ -name "*.py" -type f > /tmp/tests.txt
```

### 2.2. Критерии проверки

Для каждой сущности проверить:

| Категория | Проверки |
|-----------|----------|
| **Классы** | PascalCase? Суффикс соответствует роли? Нет camelCase/snake_case? |
| **Модули** | snake_case? Нет дефисов/CamelCase? |
| **Функции** | snake_case? Префикс соответствует семантике? |
| **Константы** | UPPER_SNAKE_CASE? |
| **Документация** | kebab-case? Есть NN- префикс для упорядоченных? |
| **Пайплайны** | Формат `{entity}_{provider}`? Стадии названы корректно? |

### 2.3. Исключения

Файл `configs/naming_exceptions.yaml` может содержать допустимые исключения. Проверить перед включением в отчёт.

---

## 3. Формат выходного отчёта

### 3.1. Структура отчёта
```markdown
# Naming Compliance Report
*Generated: YYYY-MM-DD HH:MM UTC*
*Scope: src/bioetl/, docs/, configs/, tests/*

## Summary

| Категория | Всего | Нарушений | % соответствия |
|-----------|-------|-----------|----------------|
| Классы | N | M | X% |
| Модули | N | M | X% |
| Функции | N | M | X% |
| Документация | N | M | X% |
| Конфиги | N | M | X% |

## Violations

### Classes

| Файл | Строка | Текущее имя | Проблема | Рекомендация |
|------|--------|-------------|----------|--------------|
| `path/to/file.py` | 42 | `chemblClient` | camelCase | `ChemblClient` |
| `path/to/file.py` | 85 | `DataLoader` | Нет суффикса | `DataLoaderService` или `DataLoaderImpl` |

### Modules

| Путь | Текущее имя | Проблема | Рекомендация |
|------|-------------|----------|--------------|
| `src/bioetl/...` | `ChemblClient.py` | PascalCase | `chembl_client.py` |

### Functions

| Файл | Строка | Текущее имя | Проблема | Рекомендация |
|------|--------|-------------|----------|--------------|
| `path/to/file.py` | 100 | `loadData()` | camelCase | `load_data()` |
| `path/to/file.py` | 150 | `data()` | Нет префикса (чтение) | `get_data()` |

### Documentation

| Путь | Текущее имя | Проблема | Рекомендация |
|------|-------------|----------|--------------|
| `docs/...` | `PipelineOverview.md` | PascalCase | `pipeline-overview.md` |

### Pipeline Artifacts

| Путь | Текущее имя | Проблема | Рекомендация |
|------|-------------|----------|--------------|
| `pipelines/chembl/` | `Activity/` | PascalCase | `activity/` |

## Refactoring Plan

### Phase 1: High-Impact (Breaking)
*Публичные API, импортируемые классы*

1. `OldName` → `NewName` (file.py:NN)
   - Импортёры: [список файлов]
   - Тесты: [список тестов]

### Phase 2: Internal
*Приватные функции, внутренние модули*

1. ...

### Phase 3: Documentation
*Файлы документации — минимальный риск*

1. ...

## Dependencies Map

Для каждого переименования указать:
- Файлы-импортёры
- Re-exports в `__init__.py`
- Тесты
- Документация с упоминаниями
```

---

## 4. Автоматизация (опционально)

### 4.1. Скрипт валидации
```python
# src/tools/naming_audit.py
"""
Автоматический аудит naming conventions.

Usage:
    python src/tools/naming_audit.py --output report.md
    python src/tools/naming_audit.py --check  # CI mode, exit 1 if violations
"""

import re
import ast
from pathlib import Path
from dataclasses import dataclass
from typing import Literal

@dataclass
class Violation:
    category: Literal["class", "function", "module", "doc", "config"]
    path: str
    line: int | None
    current_name: str
    issue: str
    recommendation: str

SUFFIX_MAP = {
    "Factory": ["Factory"],
    "Client": ["Client"],
    "Service": ["Service"],
    "Writer": ["Writer"],
    "Impl": ["Impl"],
    "ABC": ["ABC", "Base"],
    "Protocol": ["Protocol", "Port"],
    "Config": ["Config", "Params", "Settings"],
    "Error": ["Error", "Exception"],
    # ...
}

PREFIX_MAP = {
    "get_": "read local data",
    "fetch_": "network I/O",
    "iter_": "generator",
    "create_": "object creation",
    "build_": "object creation",
    "validate_": "validation",
    "parse_": "parsing",
    "is_": "boolean check",
    "has_": "boolean check",
    "on_": "event handler",
}

def check_class_name(name: str, context: str) -> Violation | None:
    # PascalCase check
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return Violation(...)
    # Suffix check based on context
    ...

def check_function_name(name: str, is_method: bool) -> Violation | None:
    # snake_case check
    if not re.match(r'^_?[a-z][a-z0-9_]*$', name):
        return Violation(...)
    # Prefix semantic check
    ...

def audit_file(path: Path) -> list[Violation]:
    ...

def main():
    ...
```

### 4.2. Pre-commit hook
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: naming-audit
      name: Naming Convention Check
      entry: python src/tools/naming_audit.py --check
      language: python
      types: [python]
      pass_filenames: false
```

---

## 5. Чеклист выполнения

- [ ] Собраны все классы из `src/bioetl/`
- [ ] Собраны все функции/методы
- [ ] Собраны все Python-модули
- [ ] Собраны все файлы документации
- [ ] Собраны все YAML-конфиги
- [ ] Проверены исключения из `naming_exceptions.yaml`
- [ ] Сформирован отчёт в заданном формате
- [ ] Построена карта зависимостей для breaking changes
- [ ] Определены фазы рефакторинга
- [ ] Отчёт сохранён в `reports/naming_audit_YYYYMMDD.md`