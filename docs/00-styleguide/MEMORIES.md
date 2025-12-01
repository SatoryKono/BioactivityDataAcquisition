# Memories для проекта BioETL

Этот файл содержит ключевые правила и паттерны, которые должны быть запомнены при работе с проектом.

## Критически важные правила (MUST)

### 1. Именование документации
- **Файлы документации**: kebab-case, двузначный префикс `NN-`
- **Pipeline docs**: формат `NN-<entity>-<provider>-<topic>.md`
- **Язык**: английский, lowercase, разделители `-` (не `_`)
- **H1 заголовок**: дублирует имя файла в Title Case
- **Автогенерация**: секции помечаются `<!-- generated -->`
- **Канонические идентификаторы**: в коде/configs используется `snake_case`, в docs filenames — `kebab-case`
- **Индексные файлы**: `INDEX.md` или `README.md` без префикса

### 2. Трёхслойный паттерн ABC/Default/Impl (обязателен)
- **Contract/Protocol/ABC**: `src/bioetl/clients/<domain>/contracts.py` или `base/contracts.py`
- **Default factory**: `src/bioetl/clients/<domain>/factories.py`, функция `default_<domain>_<entity>()`
- **Impl**: `src/bioetl/clients/<domain>/impl/`, классы с суффиксом `Impl`
- При создании ABC **обязательно** создать Default (может быть stub с `NotImplementedError`)
- Добавление Impl не требует нового Default
- ABC **обязан** иметь структурированный докстринг (краткое описание, публичный интерфейс, локализация, указатели на Default/Impl)

### 3. Обязательные реестры
- `src/bioetl/clients/base/abc_registry.yaml` — машинный реестр ABC
- `src/bioetl/clients/base/abc_impls.yaml` — мэппинг Default/Impl
- `docs/ABC_INDEX.md` — человекочитаемый каталог
- При создании/изменении ABC/Default/Impl **обязательно** обновлять все три реестра

### 4. Именование в коде
- **Модули**: `snake_case` (`^[a-z0-9_]+$`)
- **Классы**: PascalCase (`^[A-Z][A-Za-z0-9]+$`)
- **Функции**: snake_case (`^[a-z_][a-z0-9_]*$`)
- **Константы**: UPPER_SNAKE_CASE (`^[A-Z][A-Z0-9_]*$`)
- **Приватные**: ведущий `_`

### 5. Суффиксы классов (роли)
- `Factory` — общие фабрики
- `ClientFactory` — фабрики клиентов
- `DataClient` — реализации контрактов
- `Client` — общие клиенты
- `Facade` — фасады верхнего уровня
- `Registry` — реестры
- `Adapter`/`Transport` — низкоуровневые адаптеры/транспорты
- `Protocol`/`ABC` — контракты
- `Config`/`Model`/`Params` — конфигурационные/модельные типы
- `Error` — исключения
- `Impl` — реализации (например, `ChemblDataClientHTTPImpl`)

### 6. Префиксы функций
- `get_` — дешёвые локальные чтения
- `fetch_` — сетевые/IO операции
- `iter_` — ленивые генераторы/итераторы
- `create_`/`build_`/`make_`/`default_` — создание объектов/фабрики
- `register_` — регистрация в реестрах
- `resolve_`/`ensure_` — нормализация/подготовка
- `validate_`/`parse_`/`serialize_` — валидация/парсинг/сериализация
- `on_` — callback/обработчики
- `is_`/`has_`/`can_` — булевы проверки

### 7. Pipelines структура
- **Путь**: `src/bioetl/pipelines/<provider>/<entity>/<stage>.py`
- **Provider**: `snake_case` (`^[a-z0-9_]+$`), канонический список в `configs/providers.yaml`
- **Entity**: `snake_case` (`^[a-z0-9_]+$`)
- **Stage**: один из `extract`, `transform`, `validate`, `normalize`, `write`, `run`, `errors`, `descriptor`, `metrics`, `backfill`, `cleanup`
- **Конфиг**: `configs/pipelines/<provider>/<entity>.yaml`

### 8. Тесты
- **Unit**: `tests/bioetl/.../test_<module>.py`
- **Pipeline**: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py`
- **Integration**: `tests/integration/` или суффикс `_integration.py`
- **Golden**: `tests/golden/test_<area>_golden.py`
- **CLI**: `tests/bioetl/cli/test_<command>.py`

### 9. Конфиги
- **Файлы**: `^[a-z0-9_]+.ya?ml$` в `configs/`
- **Pipelines**: `configs/pipelines/<provider>/<entity>.yaml`
- **Ключи внутри YAML**: lower_snake_case
- **Примеры**: `*.example.yaml` или `.env.example`

### 10. Детерминизм (критически важно)
- Фиксированный порядок колонок/строк
- UTC-время
- Каноническая сериализация
- Атомарная запись (temp → os.replace) для файлов с данными/артефактами
- НЕЛЬЗЯ вносить silent-изменения публичных API/CLI/схем
- Любой breaking change сопровождается миграционной заметкой и изменением версий

### 11. Документация
- **Синхронизация**: документация **обязательно** синхронизируется с кодом и схемами
- **Автогенерация**: секции помечаются `<!-- generated -->`, не редактируются вручную
- **При добавлении сущности**: обновлять `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`, `docs/ABC_INDEX.md`, реестры
- **Breaking changes**: фиксируются в `CHANGELOG.md`

### 12. CI и enforcement
- Naming linter проверяет соответствие regex-паттернам
- CI блокирует PR при MUST-нарушениях
- Исключения регистрируются в `configs/naming_exceptions.yaml` с полями: `path`, `rule_id`, `reason`, `owner`, `expiry`
- Pre-commit hook рекомендуется для локальной проверки

## Часто используемые паттерны

### Создание нового клиента (ABC/Default/Impl)
1. Создать Protocol/ABC в `src/bioetl/clients/<domain>/contracts.py` (или `base/contracts.py` для shared)
2. Добавить структурированный докстринг с обязательными полями:
   - Краткое описание (1-2 предложения)
   - Публичный интерфейс (методы с сигнатурами)
   - Локализация (путь к файлу)
   - Default/Impl pointers (ссылки на фабрику и реестр)
3. Создать Default factory в `src/bioetl/clients/<domain>/factories.py` (может быть stub с `NotImplementedError`)
4. Обновить `src/bioetl/clients/base/abc_registry.yaml` (машинный реестр)
5. Обновить `src/bioetl/clients/base/abc_impls.yaml` (мэппинг Default/Impl)
6. Обновить `docs/ABC_INDEX.md` (человекочитаемый каталог)
7. Создать Impl в `src/bioetl/clients/<domain>/impl/` при необходимости
8. Добавить тесты и документацию

### Создание нового pipeline
1. Создать структуру: `src/bioetl/pipelines/<provider>/<entity>/`
2. Создать stage файлы: `extract.py`, `transform.py`, `validate.py`, `write.py`, и т.д.
3. Создать конфиг: `configs/pipelines/<provider>/<entity>.yaml` (lower_snake_case ключи)
4. Создать документацию: `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`
   - Формат: `NN-<entity>-<provider>-<topic>.md` (kebab-case)
   - H1 заголовок дублирует имя файла в Title Case
5. Добавить тесты: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py`
6. При необходимости создать схему: `src/bioetl/schemas/<provider>_<entity>_schema.py`

### Формат Default factory
```python
# src/bioetl/clients/<domain>/factories.py
from ..base.contracts import <Entity>Protocol
from .impl.<impl_file> import <Domain><Entity>Impl

def default_<domain>_<entity>(api_key: str, *, timeout: float = 30.0) -> <Entity>Protocol:
    """Return a ready-to-use <Entity>Client with recommended settings."""
    return <Domain><Entity>Impl(api_key=api_key, timeout=timeout)
```

### Формат ABC docstring (обязательная структура)
```python
class <Entity>Protocol(Protocol):
    """
    Краткое описание (1-2 предложения). Цель и область применения ABC.
    
    Публичный интерфейс:
    - method1(self, param: Type) -> ReturnType
    - method2(self) -> None
    
    Локализация: src/bioetl/clients/<domain>/contracts.py
    
    Default factory: src/bioetl/clients/<domain>/factories.py::default_<domain>_<entity>
    Impls: см. abc_impls.yaml
    
    Примечания/ограничения: кратко о допустимых вариантах использования.
    """
```

### Формат Impl класса
```python
# src/bioetl/clients/<domain>/impl/<impl_file>.py
from ...base.contracts import <Entity>Protocol

class <Domain><Entity>Impl:
    """Реализация <Entity>Protocol для <Domain>."""
    
    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.timeout = timeout
    
    def method1(self, param: Type) -> ReturnType:
        # реализация
        ...
```

### Атомарная запись файлов (детерминизм)
```python
import os
from pathlib import Path

def write_atomic(path: Path, content: str) -> None:
    """Атомарная запись с использованием временного файла."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
```

### PR-чеклист
- [ ] Имена публичных классов и файлов соответствуют паттернам
- [ ] Публичный API экспортирован через `__all__` в `__init__.py`
- [ ] Для нового ABC присутствует Default factory (может быть stub)
- [ ] Обновлены реестры: `abc_registry.yaml`, `abc_impls.yaml`, `docs/ABC_INDEX.md`
- [ ] Добавлены unit-тесты и при необходимости integration tests
- [ ] Документация обновлена (pipeline docs, ABC_INDEX)
- [ ] При исключениях заполнена запись в `configs/naming_exceptions.yaml`
- [ ] Breaking changes зафиксированы в `CHANGELOG.md`

## Источники истины

### Основные документы правил
- `.cursorrules` — основные правила проекта (детерминизм, стабильность, контракты)
- `docs/00-styleguide/00-naming-conventions.md` — именование документации (kebab-case, формат pipeline docs)
- `docs/00-styleguide/00-rules-summary.md` — краткая сводка правил
- `docs/00-styleguide/01-new-entity-implementation-policy.md` — политика ABC/Default/Impl (трёхслойный паттерн)
- `docs/00-styleguide/02-new-entity-naming-policy.md` — полная политика именования (regex, таблицы правил)
- `docs/00-styleguide/03-python-code-style.md` — стиль Python кода (PEP 8, типы, mypy)
- `docs/00-styleguide/10-documentation-standards.md` — стандарты документации (синхронизация, автогенерация)
- `docs/00-styleguide/RULES_QUICK_REFERENCE.md` — краткая сводка для быстрого доступа

### Реестры и конфигурации
- `src/bioetl/clients/base/abc_registry.yaml` — машинный реестр ABC (source of truth)
- `src/bioetl/clients/base/abc_impls.yaml` — мэппинг Default/Impl (source of truth)
- `docs/ABC_INDEX.md` — человекочитаемый каталог ABC
- `configs/providers.yaml` — канонический список провайдеров
- `configs/pipelines/<provider>/<entity>.yaml` — конфигурации пайплайнов
- `configs/naming_exceptions.yaml` — исключения из правил именования (path, rule_id, reason, owner, expiry)

### Документация пайплайнов
- `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md` — документация пайплайнов
- `docs/02-pipelines/00-pipeline-base.md` — базовая архитектура пайплайнов

### Важные принципы
- **Детерминизм**: фиксированный порядок, UTC-время, атомарная запись
- **Стабильность контрактов**: НЕЛЬЗЯ silent-изменения публичных API
- **Синхронизация**: документация обязана синхронизироваться с кодом
- **Трёхслойный паттерн**: Contract → Default → Impl (обязателен)
- **Enforcement**: CI блокирует PR при MUST-нарушениях

