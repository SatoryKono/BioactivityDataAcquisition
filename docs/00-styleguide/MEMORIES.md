# Memories для проекта BioETL

Этот файл содержит ключевые правила и паттерны, которые должны быть запомнены при работе с проектом.

## Критически важные правила (MUST)

### 1. Именование документации
- Файлы документации: **kebab-case**, префикс `NN-`
- Pipeline docs: `NN-<entity>-<provider>-<topic>.md`
- **НЕ использовать underscores** в именах файлов документации
- H1 заголовок дублирует имя файла в Title Case

### 2. Трёхслойный паттерн ABC/Default/Impl
- При создании нового ABC **обязательно** создать Default factory
- Default может быть stub с `NotImplementedError`
- ABC **обязан** иметь структурированный докстринг
- Обновлять реестры: `abc_registry.yaml`, `abc_impls.yaml`, `docs/ABC_INDEX.md`

### 3. Именование в коде
- Модули: `snake_case` (`^[a-z0-9_]+$`)
- Классы: `PascalCase` (`^[A-Z][A-Za-z0-9]+$`)
- Функции: `snake_case` (`^[a-z_][a-z0-9_]*$`)
- Константы: `UPPER_SNAKE_CASE` (`^[A-Z][A-Z0-9_]*$`)

### 4. Суффиксы классов
- `Impl` — реализации (например, `ChemblDataClientHTTPImpl`)
- `Protocol`/`ABC` — контракты
- `Factory` — фабрики
- `DataClient` — реализации контрактов
- `Error` — исключения

### 5. Префиксы функций
- `get_` — дешёвые локальные чтения
- `fetch_` — сетевые/IO операции
- `iter_` — ленивые генераторы
- `default_` — фабрики по умолчанию
- `create_`/`build_`/`make_` — создание объектов

### 6. Pipelines структура
- Путь: `src/bioetl/pipelines/<provider>/<entity>/<stage>.py`
- Provider и Entity: `snake_case` (`^[a-z0-9_]+$`)
- Stage: один из `extract`, `transform`, `validate`, `normalize`, `write`, `run`, `errors`, `descriptor`, `metrics`, `backfill`, `cleanup`

### 7. Детерминизм
- Фиксированный порядок колонок/строк
- UTC-время
- Атомарная запись (temp → os.replace)
- НЕЛЬЗЯ silent-изменения публичных API

### 8. Документация
- **Обязательно** синхронизировать с кодом
- Автогенерируемые секции: `<!-- generated -->`
- Breaking changes в `CHANGELOG.md`

## Часто используемые паттерны

### Создание нового клиента
1. Создать Protocol/ABC в `contracts.py`
2. Добавить структурированный докстринг
3. Создать Default factory в `factories.py` (может быть stub)
4. Обновить `abc_registry.yaml` и `abc_impls.yaml`
5. Обновить `docs/ABC_INDEX.md`
6. Создать Impl в `impl/` при необходимости

### Создание нового pipeline
1. Создать структуру: `src/bioetl/pipelines/<provider>/<entity>/`
2. Создать stage файлы: `extract.py`, `transform.py`, и т.д.
3. Создать конфиг: `configs/pipelines/<provider>/<entity>.yaml`
4. Создать документацию: `docs/pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`
5. Добавить тесты: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py`

### Формат Default factory
```python
def default_<domain>_<entity>(...) -> <Protocol>:
    """Return a ready-to-use <Entity>Client with recommended settings."""
    return <Impl>(...)
```

### Формат ABC docstring
```python
class <Entity>Protocol(Protocol):
    """
    Краткое описание (1-2 предложения).
    
    Публичный интерфейс:
    - method1(self, param: Type) -> ReturnType
    - method2(self) -> None
    
    Локализация: src/bioetl/clients/<domain>/contracts.py
    
    Default factory: src/bioetl/clients/<domain>/factories.py::default_<domain>_<entity>
    Impls: см. abc_impls.yaml
    """
```

## Источники истины

- `.cursorrules` — основные правила проекта
- `docs/00-styleguide/00-naming-conventions.md` — именование документации
- `docs/00-styleguide/00-rules-summary.md` — краткая сводка правил
- `docs/00-styleguide/01-new-entity-implementation-policy.md` — ABC/Default/Impl
- `docs/00-styleguide/02-new-entity-naming-policy.md` — полная политика именования
- `docs/00-styleguide/03-python-code-style.md` — стиль Python кода
- `docs/00-styleguide/10-documentation-standards.md` — стандарты документации
- `docs/00-styleguide/RULES_QUICK_REFERENCE.md` — краткая сводка

