# Testing Guide

Этот документ описывает стратегию и инструменты тестирования в проекте BioETL.

## 1. Стек Тестирования

- **Фреймворк**: `pytest`
- **Покрытие**: `pytest-cov`
- **Запись HTTP**: `VCR.py`
- **Property-based**: `Hypothesis`
- **Mocking**: In-memory fakes предпочтительны, `unittest.mock.MagicMock` допустим

## 2. Уровни Тестирования

### 2.1. Unit Tests (`tests/unit/`)

Изолированные тесты бизнес-логики и трансформаций.

- **Domain**: Тестирование сущностей и чистых функций в `src/bioetl/domain/`.
- **Application**: Тестирование трансформеров и логики пайплайнов. In-memory fakes предпочтительны, MagicMock допустим.
- **Правило**: Никакого сетевого взаимодействия или реального ввода-вывода.

### 2.2. Integration Tests (`tests/integration/`)

Проверка взаимодействия компонентов с внешними API и хранилищем.

- **Адаптеры**: Тестирование HTTP-клиентов (ChEMBL, PubChem, UniProt) с использованием VCR-кассет.
- **Storage**: Проверка записи в Delta Lake и Bronze хранилище (используются локальные временные пути).
- **VCR Policy**: Кассеты хранятся в `tests/fixtures/vcr/`. При запуске в CI сетевые вызовы запрещены (`--vcr-record=none`).

### 2.3. End-to-End (E2E) Tests (`tests/e2e/`)

Тестирование полного цикла работы пайплайна.

- **Сценарий**: `Run ID` -> `Fetch` -> `Bronze` -> `Silver` -> `Gold`.
- **Архитектура**: Local-Only (MemoryLock, LocalCheckpoint, FileSystem Storage).
- **Запуск**: `make test-e2e` или `pytest tests/e2e/ -m e2e`.

### 2.4. Architecture Tests (`tests/architecture/`)

Автоматизированный контроль за соблюдением архитектурных правил проекта.

- **Layer Separation**: Проверка отсутствия импортов `infrastructure` в `domain/application` через `import-linter`.
- **Rules Enforcement**:
  - `test_no_random_in_writers` (REQ-ARCH-030): Запрет на использование `random` в слое хранилища для детерминизма.
    - Проверяет: `import random`, `from random import`, `random.uniform()`, `random.choice()`
    - Область: `src/bioetl/infrastructure/storage/*.py`
  - `test_no_datetime_now_in_infrastructure`: Запрет на создание временных меток в инфраструктурном слое.
    - Проверяет: `datetime.now()`, `datetime.datetime.now()`
    - Область: `src/bioetl/infrastructure/**/*.py` (с исключениями)
  - `test_all_ports_have_implementations`: Проверка наличия реализаций для всех протоколов (портов).

**Документация:** См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) для обоснования детерминизма.

### 2.5. Security Tests (`tests/security/`)

- Проверка санитизации секретов в VCR-кассетах.
- Проверка отсутствия паролей и ключей в логах.
- Тестирование обработки PII (Personal Identifiable Information).

## 3. Метрики и Покрытие

- **Line Coverage Target**: **>90%** для доменного слоя и **>80%** для проекта в целом.
- **Branch Coverage**: Проверяется автоматически через `pytest-cov`.
- **Regression**: Все исправления багов обязаны сопровождаться регрессионным тестом.

## 4. Как запускать тесты

```bash
# Запуск всех тестов (кроме E2E)
make test

# Запуск только архитектурных тестов
make test-architecture

# Запуск с обновлением VCR кассет
pytest --vcr-record=once tests/integration/

# Проверка покрытия
pytest --cov=src/bioetl tests/
```

### 4.1. Быстрый старт для полного набора тестов

| Шаг | Команда                     | Назначение                                                           |
| --- | --------------------------- | -------------------------------------------------------------------- |
| 1   | `make install`              | Создать `.venv` и установить зависимости `[dev]` (pytest, cov, lint) |
| 2   | `source .venv/bin/activate` | Активировать окружение для дальнейших команд                         |
| 3   | `make test`                 | Запустить весь набор тестов с покрытием ≥85% (архитектурные + e2e)   |
| 4   | `open htmlcov/index.html`   | Просмотреть детализированный отчёт покрытия локально                 |

**Примечания:**

- Если нужен быстрый прогон без HTML-отчёта и без бенчмарков, используйте `make test-fast`.
- Для корректного прохождения трассировки и мониторинга установите опциональные зависимости (`psutil`, `opentelemetry-*`).
- В CI используется тот же профиль `make test`, поэтому локальный запуск обязателен перед коммитом.

## 5. План по устранению избыточности (ChEMBL Target Component)

В ходе аудита пайплайна `chembl_target_component` был выявлен риск многократного извлечения одних и тех же данных. План исправления:

1. **Дедупликация на стороне клиента**: Внедрение `seen_ids` в `ChemblAdapter.fetch_filtered` для обработки дублей, возвращаемых API при использовании сложных фильтров.
1. **Исправление пагинации**: Переход от фиксированного `offset += batch_size` к `offset += len(records)` для предотвращения пропусков данных в Degraded режиме.
1. **Оптимизация параметров**: Передача `limit` напрямую в API запросы для исключения выкачивания лишних записей из ChEMBL.

## 6. Оптимизация Тестов

### 6.1. Параллельное Выполнение (pytest-xdist)

Тесты поддерживают параллельное выполнение через `pytest-xdist`:

```bash
# Параллельное выполнение (рекомендуется)
make test  # Использует -n auto --dist loadscope

# Serial execution (для отладки)
make test-serial
```

**Производительность** (verified 2026-01-19):

- Serial: ~150-180s (зависит от hardware)
- Parallel (auto): ~55-75s (зависит от hardware)
- Улучшение: **~60-65%**

**Статус pytest-xdist**: Работает корректно. Проблема с collection была решена в v5.9.0.

### 6.2. Hypothesis Профили

Hypothesis настроен с профилями для разных сценариев (см. `tests/conftest.py`):

| Профиль    | max_examples | Использование                  |
| ---------- | ------------ | ------------------------------ |
| `ci`       | 10           | Автоматически в CI (CI=true)   |
| `fast`     | 5            | Быстрый smoke test             |
| `dev`      | 50           | Локальная разработка (default) |
| `thorough` | 200          | Pre-release тестирование       |

```bash
# Использование профилей
HYPOTHESIS_PROFILE=fast pytest tests/unit/
HYPOTHESIS_PROFILE=thorough pytest tests/  # Перед релизом
```

**Важно**: Тесты НЕ должны переопределять `max_examples` в декораторе `@settings()`, чтобы профили работали корректно.

### 6.3. Test Markers

Используйте маркеры для выборочного запуска:

```bash
# Исключить медленные тесты
pytest tests/ -m "not slow"

# Только unit тесты
pytest tests/ -m "unit"

# Только Hypothesis тесты
pytest tests/ -m "hypothesis"

# Быстрый smoke
make test-smoke
```

**Доступные маркеры**:

- `unit` — Unit тесты (быстрые, без I/O)
- `integration` — Integration тесты с VCR
- `e2e` — End-to-end тесты
- `slow` — Медленные тесты (subprocess, vulture, security scans)
- `hypothesis` — Property-based тесты
- `architecture` — Архитектурные тесты
- `security` — Security тесты
- `smoke` — Быстрые smoke тесты

### 6.4. CI Test Layering

CI использует многоуровневую стратегию тестирования:

```
Stage 1: Lint + Smoke (~30s)
├── make lint
└── make test-smoke

Stage 2: Unit + Architecture (~60s)
├── pytest tests/unit/ -m "not slow"
└── pytest tests/architecture/

Stage 3: Integration (~20s)
└── pytest tests/integration/ --vcr-record=none

Stage 4: E2E (на PR merge)
└── pytest tests/e2e/ -m e2e

Stage 5: Contract (ежемесячно)
└── BIOETL_LIVE_API_TESTS=true pytest tests/contracts/
```

### 6.5. Best Practices

1. **Scope фикстур**: Используйте `scope="session"` или `scope="module"` для stateless фикстур
1. **In-memory fakes**: Предпочтительнее MagicMock для unit тестов
1. **VCR кассеты**: Обязательны для HTTP взаимодействий в integration тестах
1. **Маркеры**: Добавляйте `@pytest.mark.slow` для тестов >1s
