# Архитектурное тестирование

## Обзор

Архитектурные тесты в `tests/test_architecture_enforcement.py` автоматически проверяют соблюдение правил чистой архитектуры. Они используют AST-анализ (Abstract Syntax Tree) для проверки импортов и вызовов функций.

## Принцип работы

Тесты создают "железный занавес" между слоями:
- **Domain** — чистый слой, не зависит ни от чего кроме стандартной библиотеки
- **Application** — зависит только от Domain портов, не от конкретных Infrastructure реализаций
- **Infrastructure** — зависит только от Domain портов, не от Application

## Категории тестов

### 1. Domain Layer Purity (REQ-ARCH-DOMAIN-001)

#### `test_domain_no_external_frameworks`
Проверяет, что Domain не импортирует внешние фреймворки:
- ❌ Запрещены: `prefect`, `boto3`, `click`, `fastapi`, `httpx`, `redis`, `polars`, `sqlalchemy`
- ✅ Разрешены: Стандартная библиотека Python + `pydantic`

**Почему:**
- Domain должен быть фреймворк-независимым
- Легко переиспользовать в других проектах
- Максимально быстрое unit-тестирование

#### `test_domain_no_infrastructure_imports`
Проверяет, что Domain не импортирует Infrastructure или Application:
```python
# ❌ Запрещено в Domain
from bioetl.infrastructure.storage import S3Storage
from bioetl.application.core.executor import PipelineExecutor

# ✅ Разрешено в Domain
from bioetl.domain.ports import StoragePort
from bioetl.domain.types import RunID
```

#### `test_domain_only_allowed_imports`
Белый список разрешенных импортов в Domain:
```python
ALLOWED_DOMAIN_IMPORTS = {
    # Стандартная библиотека
    "abc", "collections", "dataclasses", "datetime",
    "decimal", "enum", "functools", "itertools",
    "pathlib", "typing", "uuid", "warnings", "__future__",
    # Validation
    "pydantic",
}
```

### 2. Application Layer Rules (REQ-ARCH-APP-001)

#### `test_application_no_concrete_infrastructure_imports`
Проверяет, что Application зависит только от интерфейсов:
```python
# ❌ Запрещено в Application
from bioetl.infrastructure.adapters.chembl import ChEMBLClient
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3CheckpointAdapter

# ✅ Разрешено в Application
from bioetl.domain.ports import DataSourcePort, CheckpointPort
from bioetl.infrastructure.factories import create_data_source
```

**Исключения:**
- `infrastructure.factories` — для создания адаптеров
- `infrastructure.observability` — для логирования

#### `test_application_no_direct_adapter_imports`
Запрещает прямые импорты из `infrastructure.adapters`:
```python
# ❌ Нарушение
from bioetl.infrastructure.adapters.chembl.client import ChEMBLClient

# ✅ Правильно
if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.chembl.client import ChEMBLClient
```

### 3. Security Checks (REQ-SECURITY-001)

#### `test_no_print_statements`
Запрещает использование `print()` и `pprint()`:
```python
# ❌ Нарушение
print(f"Processing record: {record_id}")

# ✅ Правильно
logger.info("Processing record", record_id=record_id)
```

**Исключения:** `cli.py`, `__main__.py`

#### `test_no_unsafe_builtins`
Запрещает небезопасные функции: `eval()`, `exec()`, `compile()`, `__import__()`

### 4. Infrastructure Rules (REQ-ARCH-INFRA-001)

#### `test_infrastructure_no_application_imports`
Infrastructure не должен зависеть от Application:
```python
# ❌ Нарушение в Infrastructure
from bioetl.application.core.executor import PipelineExecutor

# ✅ Правильно
from bioetl.domain.ports import DataSourcePort
```

## Запуск тестов

### Локально
```bash
# Все архитектурные тесты
pytest tests/test_architecture_enforcement.py -v

# Конкретный тест
pytest tests/test_architecture_enforcement.py::test_domain_no_external_frameworks -v

# С подробным выводом
pytest tests/test_architecture_enforcement.py -vv
```

### В CI/CD
```yaml
# .github/workflows/ci.yml
- name: Architecture tests
  run: |
    pytest tests/test_architecture_enforcement.py \
      --tb=short \
      --maxfail=1
```

## Что делать при нарушении

### Пример нарушения
```
FAILED tests/test_architecture_enforcement.py::test_domain_no_external_frameworks

bioetl/domain/context.py:15: Forbidden framework import 'httpx' in Domain layer

Domain layer must not import external frameworks.
Allowed: Standard library, Pydantic
```

### Исправление

1. **Определите причину импорта**
   - Нужна ли эта зависимость в Domain?
   - Может быть, это должен быть Infrastructure адаптер?

2. **Рефакторинг**
   ```python
   # Было (нарушение)
   # domain/fetcher.py
   import httpx

   class DataFetcher:
       def fetch(self):
           response = httpx.get("...")

   # Стало (правильно)
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

3. **Обновите импорты**
   - Используйте Domain порты вместо конкретных реализаций
   - Инжектируйте зависимости через конструктор

## Добавление новых правил

### Расширение белого списка Domain
```python
# tests/test_architecture_enforcement.py
ALLOWED_DOMAIN_IMPORTS = {
    # ... существующие ...
    "new_module",  # добавьте с комментарием
}
```

### Добавление запрещенных фреймворков
```python
FORBIDDEN_DOMAIN_FRAMEWORKS = {
    # ... существующие ...
    "new_framework",
}
```

### Создание нового теста
```python
def test_custom_architectural_rule(src_dir: Path):
    """Описание правила."""
    violations = []

    for py_file in (src_dir / "bioetl" / "specific_layer").rglob("*.py"):
        imports, calls = analyze_python_file(py_file)

        # Ваша логика проверки
        for imp in imports:
            if condition_violated:
                violations.append(
                    format_violation(py_file, imp["lineno"], message, src_dir)
                )

    assert not violations, "Error message with guidance"
```

## Интеграция с import-linter

Архитектурные тесты дополняют `.importlinter`:

```ini
# .importlinter
[importlinter:contract:domain-independence]
name = Domain layer must be independent
type = independence
modules =
    bioetl.domain
```

### Различия

| Аспект | AST-тесты | import-linter |
|--------|-----------|---------------|
| **Granularity** | Файл + строка | Модуль |
| **Feedback** | Pytest output | CLI report |
| **Speed** | Быстро | Медленно |
| **Custom rules** | Легко | Ограничено |

**Рекомендация:** Используйте оба подхода:
- AST-тесты — для быстрых локальных проверок
- import-linter — для CI/CD gate

## Метрики качества

### Цели
- ✅ **100%** Domain файлов без внешних зависимостей
- ✅ **0** прямых импортов конкретных Infrastructure в Application
- ✅ **0** использований `print()` (кроме CLI)
- ✅ **0** небезопасных функций

### Отслеживание
```bash
# Количество нарушений
pytest tests/test_architecture_enforcement.py --tb=no -q

# Подробный отчет
pytest tests/test_architecture_enforcement.py -v > architecture_report.txt
```

## FAQ

### Q: Можно ли импортировать `typing.Protocol` в Domain?
**A:** Да, `typing` входит в стандартную библиотеку и разрешен.

### Q: Можно ли использовать `pydantic` в Domain?
**A:** Да, но только для Value Objects. Не используйте специфичные для Pydantic фичи (Field, validators).

### Q: Что делать с TYPE_CHECKING импортами?
**A:** TYPE_CHECKING блоки разрешены для type hints, но не должны нарушать архитектуру в рантайме.

### Q: Как тестировать код без внешних зависимостей?
**A:** Используйте моки:
```python
@pytest.fixture
def mock_data_source() -> DataSourcePort:
    class MockDataSource:
        async def fetch(self) -> AsyncIterator[dict]:
            yield {"id": "test"}
    return MockDataSource()
```

## Ссылки

- [Clean Architecture (Robert Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [import-linter](https://import-linter.readthedocs.io/)
