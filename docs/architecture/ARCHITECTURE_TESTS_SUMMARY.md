# Ужесточение архитектурных тестов — Summary

## Цель

Создать "железный занавес" между слоями архитектуры с помощью автоматизированных AST-тестов, которые гарантируют, что любой PR, нарушающий архитектуру, будет автоматически отклонен CI.

## Реализованные компоненты

### 1. `tests/test_architecture_enforcement.py` — Строгие архитектурные тесты

**Использует AST-анализ** (Abstract Syntax Tree) для проверки:
- ✅ Импортов на соответствие архитектурным границам
- ✅ Вызовов функций (print, eval, exec)
- ✅ Соблюдения принципов Clean Architecture

#### Категории тестов

**Domain Layer Purity (REQ-ARCH-DOMAIN-001)**
- `test_domain_no_external_frameworks` — запрет prefect, boto3, click, fastapi, httpx, redis
- `test_domain_no_infrastructure_imports` — запрет импортов Infrastructure/Application
- `test_domain_only_allowed_imports` — белый список (stdlib + pydantic)

**Application Layer Rules (REQ-ARCH-APP-001)**
- `test_application_no_concrete_infrastructure_imports` — запрет конкретных адаптеров
- `test_application_no_direct_adapter_imports` — запрет прямых импортов adapters

**Security Checks (REQ-SECURITY-001)**
- `test_no_print_statements` — только logger (исключения: cli.py, __main__.py)
- `test_no_unsafe_builtins` — запрет eval, exec, compile, __import__

**Infrastructure Rules (REQ-ARCH-INFRA-001)**
- `test_infrastructure_no_application_imports` — Infrastructure зависит только от Domain

### 2. `docs/architecture/ARCHITECTURE_TESTING.md` — Полная документация

**Содержит:**
- Описание всех правил и категорий тестов
- Примеры нарушений и способы исправления
- Руководство по запуску тестов
- Интеграция с import-linter
- FAQ и best practices

### 3. Обновленный `Makefile` — Новые команды

```bash
make test-architecture           # Быстрые AST-тесты
make test-architecture-strict    # AST + import-linter
```

## Архитектурные правила

### Domain Layer

```python
# ✅ Разрешено
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol
from pydantic import BaseModel

# ❌ Запрещено
from prefect import task           # внешний фреймворк
from httpx import AsyncClient      # I/O библиотека
from bioetl.infrastructure import S3Storage  # нарушение границ
```

### Application Layer

```python
# ✅ Разрешено
from bioetl.domain.ports import DataSourcePort
from bioetl.infrastructure.factories import create_data_source
from bioetl.infrastructure.observability import create_logger

# ❌ Запрещено
from bioetl.infrastructure.adapters.chembl import ChEMBLClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3CheckpointAdapter
```

### Безопасность

```python
# ✅ Разрешено
logger.info("Processing record", record_id=record_id)

# ❌ Запрещено
print(f"Processing record: {record_id}")
result = eval(user_input)
```

## Как работают тесты

### AST Visitor для импортов

```python
class ImportVisitor(ast.NodeVisitor):
    def visit_Import(self, node):
        # Анализирует: import foo
        ...

    def visit_ImportFrom(self, node):
        # Анализирует: from foo import bar
        ...
```

### Проверка на каждый файл

```python
for py_file in domain_path.rglob("*.py"):
    imports, calls = analyze_python_file(py_file)

    for imp in imports:
        if imp["module"] in FORBIDDEN_FRAMEWORKS:
            violations.append(f"{py_file}:{imp['lineno']}: ...")
```

### Детальные отчеты

```
FAILED test_domain_no_external_frameworks

bioetl/domain/context.py:15: Forbidden framework import 'httpx'

Domain layer must not import external frameworks.
Allowed: Standard library, Pydantic
```

## Интеграция в разработку

### Pre-commit hooks (рекомендуется)

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: architecture-tests
      name: Architecture Tests
      entry: pytest tests/test_architecture_enforcement.py --tb=short
      language: system
      pass_filenames: false
```

### CI/CD Gate

```yaml
# .github/workflows/ci.yml
- name: Architecture Tests
  run: |
    pytest tests/test_architecture_enforcement.py \
      --tb=short \
      --maxfail=1
```

### Local Development

```bash
# Перед коммитом
make test-architecture

# Полная проверка
make test-architecture-strict
```

## Метрики качества

### Цели (100% compliance)
- ✅ Domain: 0 внешних фреймворков
- ✅ Application: 0 прямых импортов Infrastructure
- ✅ Codebase: 0 использований print()
- ✅ Codebase: 0 небезопасных функций (eval, exec)

### Отслеживание

```bash
# Количество нарушений
pytest tests/test_architecture_enforcement.py --tb=no -q

# Детальный отчет
pytest tests/test_architecture_enforcement.py -vv > report.txt
```

## Преимущества

### 1. Автоматизация
- ❌ Было: "Помним, что Domain не должен импортировать boto3"
- ✅ Стало: Тест автоматически падает при нарушении

### 2. Быстрая обратная связь
- Локально: `make test-architecture` (~2-3 секунды)
- CI/CD: Падает до мерджа в main

### 3. Документирование правил
- Тесты = живая документация
- Четкие error messages с примерами исправления

### 4. Защита от регрессии
- Новые разработчики не смогут случайно нарушить архитектуру
- Рефакторинг становится безопасным

### 5. Code Review
- Меньше комментариев "это нарушает архитектуру"
- Больше фокуса на бизнес-логике

## Примеры реальных нарушений

### Пример 1: Прямой импорт httpx в Domain

**Нарушение:**
```python
# domain/fetcher.py
import httpx

class DataFetcher:
    async def fetch_data(self, url: str):
        async with httpx.AsyncClient() as client:
            return await client.get(url)
```

**Исправление:**
```python
# domain/ports.py
class DataSourcePort(Protocol):
    async def fetch(self) -> AsyncIterator[dict]: ...

# infrastructure/adapters/http_client.py
import httpx

class HTTPDataSource:
    async def fetch(self) -> AsyncIterator[dict]:
        async with httpx.AsyncClient() as client:
            ...
```

### Пример 2: Application импортирует конкретную реализацию

**Нарушение:**
```python
# application/core/pipeline.py
from bioetl.infrastructure.adapters.chembl import ChEMBLClient

class Pipeline:
    def __init__(self):
        self.client = ChEMBLClient()
```

**Исправление:**
```python
# application/core/pipeline.py
from bioetl.domain.ports import DataSourcePort

class Pipeline:
    def __init__(self, data_source: DataSourcePort):
        self.data_source = data_source  # инжектируется

# bootstrap.py
from bioetl.infrastructure.factories import create_chembl_client

pipeline = Pipeline(data_source=create_chembl_client())
```

### Пример 3: Использование print() вместо logger

**Нарушение:**
```python
# application/core/executor.py
def process_batch(self, batch):
    print(f"Processing batch of {len(batch)} records")
```

**Исправление:**
```python
# application/core/executor.py
def process_batch(self, batch):
    self.logger.info("Processing batch", batch_size=len(batch))
```

## Расширение тестов

### Добавление нового правила

```python
# tests/test_architecture_enforcement.py

def test_custom_rule(src_dir: Path):
    """Описание правила."""
    violations = []

    for py_file in (src_dir / "bioetl" / "layer").rglob("*.py"):
        imports, calls = analyze_python_file(py_file)

        # Ваша логика
        for imp in imports:
            if condition:
                violations.append(
                    format_violation(py_file, imp["lineno"], msg, src_dir)
                )

    assert not violations, "Error message"
```

### Обновление белого списка

```python
ALLOWED_DOMAIN_IMPORTS = {
    # ... существующие ...
    "new_module",  # Причина добавления
}
```

## Следующие шаги

### 1. Интеграция в CI/CD
- [ ] Добавить в `.github/workflows/ci.yml`
- [ ] Настроить pre-commit hooks

### 2. Мониторинг метрик
- [ ] Dashboard с количеством нарушений
- [ ] Трендинг: уменьшение технического долга

### 3. Дополнительные правила
- [ ] Проверка циклических зависимостей
- [ ] Анализ сложности модулей (cohesion)
- [ ] Проверка naming conventions

### 4. Документация
- [ ] Видео-туториал по архитектурным тестам
- [ ] Onboarding checklist для новых разработчиков

## Заключение

Архитектурные тесты превращают **договоренности в автоматизированные правила**:

| До | После |
|----|-------|
| "Помним, что..." | Тест падает |
| Code review субъективен | Объективные критерии |
| Регрессия возможна | Защита от регрессии |
| Долгое обучение | Быстрый feedback |

**Результат:** Архитектура становится **проверяемой** и **защищенной** от эрозии.

## Команды для запуска

```bash
# Локальная разработка
make test-architecture              # Быстро (~2-3 сек)

# Перед коммитом
make test-architecture-strict       # AST + import-linter

# CI/CD
pytest tests/test_architecture_enforcement.py --maxfail=1 --tb=short
```

## Ссылки

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python AST](https://docs.python.org/3/library/ast.html)
- [import-linter](https://import-linter.readthedocs.io/)
- [Полная документация](./ARCHITECTURE_TESTING.md)
