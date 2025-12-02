<!-- SUMMARY: Краткая сводка правил для быстрого доступа. Полные документы консолидированы сюда. -->
# Свод правил проекта BioETL

> **Авторитетный источник**: Этот файл объединяет все действующие правила. Прежние документы в каталоге `docs/00-styleguide/` заменены ссылками на эту сводку.

## 1. Именование документации

- **Файлы документации**: kebab-case, двузначный префикс `NN-`, формат `NN-<entity>-<provider>-<topic>.md` для pipeline docs
- **Индексные файлы**: `INDEX.md` или `README.md` без префикса
- **Язык**: английский, lowercase, разделители `-` (не `_`)
- **H1 заголовок**: дублирует имя файла в Title Case
- **Автогенерация**: секции помечаются `<!-- generated -->`
- **Канонические идентификаторы**: в коде/configs используется `snake_case`, в docs filenames — `kebab-case`

## 2. Политика создания ABC/Default/Impl

### Трёхслойный паттерн (обязателен)
- **Contract/Protocol/ABC**: `src/bioetl/clients/<domain>/contracts.py` или `base/contracts.py`
- **Default factory**: `src/bioetl/clients/<domain>/factories.py`, функция `default_<domain>_<entity>()`
- **Impl**: `src/bioetl/clients/<domain>/impl/`, классы с суффиксом `Impl`

### Обязательные реестры
- `src/bioetl/clients/base/abc_registry.yaml` — машинный реестр ABC
- `src/bioetl/clients/base/abc_impls.yaml` — мэппинг Default/Impl
- `docs/01-ABC/INDEX.md` — человекочитаемый каталог

### Правила создания
- При создании ABC **обязательно** создать Default (может быть stub)
- Default может быть stub с `NotImplementedError` если нет реальных Impl
- Добавление Impl не требует нового Default
- ABC **обязан** иметь структурированный докстринг (краткое описание, публичный интерфейс, локализация, указатели на Default/Impl)

## 3. Именование сущностей

### Базовые правила
- **Модули**: `^[a-z0-9_]+$` (snake_case)
- **Классы**: PascalCase, `^[A-Z][A-Za-z0-9]+$`
- **Функции**: snake_case, `^[a-z_][a-z0-9_]*$`
- **Константы**: UPPER_SNAKE_CASE, `^[A-Z][A-Z0-9_]*$`
- **Приватные**: ведущий `_`

### Суффиксы классов (роли)
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

### Префиксы функций
- `get_` — дешёвые локальные чтения
- `fetch_` — сетевые/IO операции
- `iter_` — ленивые генераторы/итераторы
- `create_`/`build_`/`make_`/`default_` — создание объектов/фабрики
- `register_` — регистрация в реестрах
- `resolve_`/`ensure_` — нормализация/подготовка
- `validate_`/`parse_`/`serialize_` — валидация/парсинг/сериализация
- `on_` — callback/обработчики
- `is_`/`has_`/`can_` — булевы проверки

### Pipelines
- Путь: `src/bioetl/pipelines/<provider>/<entity>/<stage>.py`
- Provider: `^[a-z0-9_]+$`
- Entity: `^[a-z0-9_]+$`
- Stage: `extract`, `transform`, `validate`, `normalize`, `write`, `run`, `errors`, `descriptor`, `metrics`, `backfill`, `cleanup`

### Тесты
- Unit: `tests/bioetl/.../test_<module>.py`
- Pipeline: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py`
- Integration: `tests/integration/` или суффикс `_integration.py`
- Golden: `tests/golden/test_<area>_golden.py`

### Конфиги
- Файлы: `^[a-z0-9_]+.ya?ml$` в `configs/`
- Pipelines: `configs/pipelines/<provider>/<entity>.yaml`
- Ключи внутри YAML: lower_snake_case

## 4. Стандарты документации

- **Синхронизация**: документация **обязательно** синхронизируется с кодом и схемами
- **Автогенерация**: секции помечаются `<!-- generated -->`, не редактируются вручную
- **При добавлении сущности**: обновлять `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`, `docs/01-ABC/INDEX.md`, реестры
- **Breaking changes**: фиксируются в `CHANGELOG.md`

## 5. CI и enforcement

- Naming linter проверяет соответствие regex-паттернам
- CI блокирует PR при MUST-нарушениях
- Исключения регистрируются в `configs/naming_exceptions.yaml` с полями: `path`, `rule_id`, `reason`, `owner`, `expiry`
- Pre-commit hook рекомендуется для локальной проверки

