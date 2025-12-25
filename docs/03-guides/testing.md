# Testing Guide

Этот документ описывает стратегию и инструменты тестирования в проекте BioETL.

## 1. Стек Тестирования

- **Фреймворк**: `pytest`
- **Покрытие**: `pytest-cov`
- **Запись HTTP**: `VCR.py`
- **Property-based**: `Hypothesis`
- **Mocking**: `unittest.mock` (для инфраструктуры), in-memory fakes (для домена)

## 2. Уровни Тестирования

### 2.1. Unit Tests (`tests/unit/`)
Изолированные тесты бизнес-логики и трансформаций.
- **Domain**: Тестирование сущностей и чистых функций в `src/bioetl/domain/`.
- **Application**: Тестирование трансформеров и логики пайплайнов с использованием моков портов.
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

## 5. План по устранению избыточности (ChEMBL Target Component)

В ходе аудита пайплайна `chembl_target_component` был выявлен риск многократного извлечения одних и тех же данных. План исправления:
1. **Дедупликация на стороне клиента**: Внедрение `seen_ids` в `ChemblAdapter.fetch_filtered` для обработки дублей, возвращаемых API при использовании сложных фильтров.
2. **Исправление пагинации**: Переход от фиксированного `offset += batch_size` к `offset += len(records)` для предотвращения пропусков данных в Degraded режиме.
3. **Оптимизация параметров**: Передача `limit` напрямую в API запросы для исключения выкачивания лишних записей из ChEMBL.
