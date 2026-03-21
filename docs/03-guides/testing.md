# Testing Guide

Этот документ описывает стратегию и инструменты тестирования в проекте BioETL.

## 1. Стек Тестирования

- **Фреймворк**: `pytest`
- **Покрытие**: `pytest-cov`
- **Запись HTTP**: `VCR.py`
- **Property-based**: `Hypothesis`
- **Mocking**: In-memory fakes предпочтительны, `unittest.mock.MagicMock` допустим

Source of truth для тестовой governance:
- [ADR-042](../02-architecture/decisions/ADR-042-testing-strategy-matrix.md)
- [configs/quality/test_matrix.yaml](../../configs/quality/test_matrix.yaml)

Текущее состояние rollout по ADR-042:
- mutation testing в CI блокирует только `domain/` с порогом `70%`
- `application/` mutation target (`60%`) задокументирован, но пока staged и не является blocking gate
- VCR cassette metadata (`*_meta.yaml`) перешли в `partial` rollout: в репозитории уже есть seeded sidecar inventory и canonical backfill tool, но metadata coverage пока не repo-wide и потому enforcement остаётся неполным
- `vcr_cassette_max_age_days: 90` уже является нормативным stale-age threshold, а repo-wide age rollout теперь `partial`: архитектурные тесты требуют наличие `_meta.yaml` inventory, но CI пока не делает stale-age blocking gate для всего дерева
- canonical VCR metadata catalog теперь существует как tracked artifact в `reports/quality/vcr-metadata-catalog.json`
- canonical tooling paths активированы для partial rollout: `scripts/qa/report_vcr_metadata_catalog.py` генерирует/проверяет catalog, а `scripts/migrations/active/backfill_vcr_metadata_sidecars.py` служит canonical backfill entry point; при этом workflow-level automated backfill всё ещё не включён
- descriptive test-health taxonomy теперь canonical-фиксируется в `configs/quality/test_health_reporting.yaml`; статусы `fully_exercised_green`, `staged_green`, `environment_limited_green` остаются informational и не заменяют merge-blocking CI status
- monthly `contract-tests.yml` остаётся активным live-network workflow и должен запускать `tests/contract/` с `BIOETL_LIVE_API_TESTS=true`, `BIOETL_NETWORK_TESTS=true` и `--network`
- минимальный live-contract baseline уже enforceable: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex` обязаны иметь live contract suites; `semanticscholar` переведён в явный `pilot`
- текущие silver schema snapshots уже живут в `tests/contract/silver_schemas/snapshots/`; внешний registry `tests/fixtures/contracts/{provider}/v{version}.json` остаётся future target из ADR-042
- canonical VCR placement уже enforced в CI: кассеты вне `tests/fixtures/vcr/{provider}/` блокируются
- extensionless VCR files пока допустимы только через `.github/vcr-noext-allowlist.txt`; новые такие файлы добавлять нельзя

## 2. Уровни Тестирования

### 2.1. Unit Tests (`tests/unit/`)

Изолированные тесты бизнес-логики и трансформаций.

- **Domain**: Тестирование сущностей и чистых функций в `src/bioetl/domain/`.
- **Application**: Тестирование трансформеров и логики пайплайнов. In-memory fakes предпочтительны, MagicMock допустим.
- **Правило**: Никакого сетевого взаимодействия или реального ввода-вывода.

#### 2.1.1. Source-to-Test Ownership

Для тонких пакетов (`package/__init__.py` + один содержательный `.py`-модуль) проект
держит явную source-to-test ownership symmetry:

- по умолчанию такой модуль должен иметь same-path sibling
  `tests/unit/.../test_<module>.py`;
- исключения фиксируются machine-readable в
  `configs/quality/source_test_mapping_exceptions.yaml`;
- архитектурный guard находится в
  `tests/architecture/test_source_test_mapping_policy.py`.

Это правило staged и не требует на текущем этапе зеркального `test_<module>.py` для
каждого файла в `src/bioetl/`. Для aggregate/contract/facade coverage исключения
должны быть перечислены явно, чтобы contributor мог быстро понять canonical owner
test для модуля.

Для behavior-heavy модулей второго этапа используется отдельный curated inventory:

- `configs/quality/source_test_owner_inventory.yaml`
- `tests/architecture/test_curated_source_test_ownership.py`

Текущий curated scope уже покрывает high-signal seams в `application/core`,
`application/composite`, `infrastructure/storage` и `infrastructure/adapters`.
Для таких модулей ownership фиксируется либо через direct same-path test, либо
через явно перечисленный focused cluster-owner suite.

Там допускаются два режима:

- `direct_test`: same-path owner test обязателен;
- `cluster_owner`: модуль intentionally owned через focused aggregate suite, и это
  должно быть явно перечислено в inventory.

Для stable façade и arch-owned seams есть отдельный inventory:

- `configs/quality/source_test_facade_inventory.yaml`
- `tests/architecture/test_source_test_facade_ownership.py`

Этот слой зарезервирован для package facades, retained canonical entrypoints и
compatibility facades, где mirror-path `test_<module>.py` был бы ложным сигналом,
а реальный owner живёт в contract или architecture suite.

### 2.2. Integration Tests (`tests/integration/`)

Проверка взаимодействия компонентов с внешними API и хранилищем.

- **Адаптеры**: Тестирование HTTP-клиентов (ChEMBL, PubChem, UniProt) с использованием VCR-кассет.
- **Storage**: Проверка записи в Delta Lake и Bronze хранилище (используются локальные временные пути).
- **VCR Policy**: Кассеты хранятся в `tests/fixtures/vcr/`. При запуске в CI сетевые вызовы запрещены (`--vcr-record=none`).
- **Fixture Governance**: `_meta.yaml` sidecars и stale-age policy находятся в `partial` rollout. Репозиторий уже держит seeded sidecar inventory и canonical catalog, но глобальный enforcement ещё не repo-wide.
- **Catalog / Backfill Policy**: canonical VCR metadata catalog и canonical backfill script уже существуют, но automated workflow rollout всё ещё остаётся неполным; это состояние фиксируется matrix и architecture guard'ами.
- **Live Contract Baseline**: live-network enforcement обязателен для `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`; `semanticscholar` сейчас проходит как `pilot`.

### 2.3. End-to-End (E2E) Tests (`tests/e2e/`)

Тестирование полного цикла работы пайплайна.

- **Сценарий**: `Run ID` -> `Fetch` -> `Bronze` -> `Silver` -> `Gold`.
- **Архитектура**: Local-Only (MemoryLock, LocalCheckpoint, FileSystem Storage).
- **Запуск**: `uv run python -m pytest tests/e2e/ -m e2e -v`.

### 2.4. Architecture Tests (`tests/architecture/`)

Автоматизированный контроль за соблюдением архитектурных правил проекта.

- **Layer Separation**: Проверка отсутствия импортов `infrastructure` в `domain/application` через `import-linter`.
- **Rules Enforcement**:
  - `test-no-random-in-writers` (REQ-ARCH-030): Запрет на использование `random` в слое хранилища для детерминизма.
    - Проверяет: `import random`, `from random import`, `random.uniform()`, `random.choice()`
    - Область: `src/bioetl/infrastructure/storage/*.py`
  - `test-no-datetime-now-in-infrastructure`: Запрет на создание временных меток в инфраструктурном слое.
    - Проверяет: `datetime.now()`, `datetime.datetime.now()`
    - Область: `src/bioetl/infrastructure/**/*.py` (с исключениями)
  - `test-all-ports-have-implementations`: Проверка наличия реализаций для всех протоколов (портов).
  - `test_test_matrix_coverage`: Проверка, что ADR-042 matrix, fixture rollout и mutation governance не расходятся с текущим состоянием репозитория и workflow.

**Документация:** См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) для обоснования детерминизма.

### 2.5. Security Tests (`tests/security/`)

- Проверка санитизации секретов в VCR-кассетах.
- Проверка отсутствия паролей и ключей в логах.
- Тестирование обработки PII (Personal Identifiable Information).

## 3. Метрики и Покрытие

- **Line Coverage Target**: **>=90%** для доменного слоя и **>=85%** для проекта в целом.
- **Branch Coverage**: Проверяется автоматически через `pytest-cov`.
- **Regression**: Все исправления багов обязаны сопровождаться регрессионным тестом.
- **Coverage Configuration**: Подробная информация о настройке покрытия, исключаемых паттернах и troubleshooting — см. [Coverage Configuration Guide](./coverage-configuration.md)

## 4. Как запускать тесты

```bash
# Запуск локального стабильного test suite (без E2E)
make test

# CI-подобный устойчивый прогон (parallel + fallback + serial pass)
make test-ci

# Запуск E2E в Local-Only режиме
uv run python -m pytest tests/e2e/ -m e2e -v

# Запуск только архитектурных тестов
make test-architecture

# Запуск с обновлением VCR кассет
pytest --vcr-record=once tests/integration/

# Проверка покрытия
pytest --cov=src/bioetl tests/
```

### 4.1. Быстрый старт для рекомендуемого локального прогона

| Шаг | Команда                     | Назначение                                                           |
| --- | --------------------------- | -------------------------------------------------------------------- |
| 1   | `make install`              | Создать `.venv` и установить зависимости `[dev]` (pytest, cov, lint) |
| 2   | `source .venv/bin/activate` | Активировать окружение для дальнейших команд                         |
| 3   | `make test`                 | Запустить локальный стабильный прогон с покрытием ≥85% (без E2E)     |
| 4   | `uv run python -m pytest tests/e2e/ -m e2e -v` | Отдельно запустить E2E в Local-Only режиме |
| 5   | `htmlcov/index.html`        | Открыть HTML coverage report локально в браузере                     |

**Примечания:**

- Если нужен быстрый прогон без HTML-отчёта и без бенчмарков, используйте `make test-fast`.
- Для корректного прохождения трассировки и мониторинга установите опциональные зависимости (`psutil`, `opentelemetry-*`).
- В CI для полного устойчивого прогона используется `make test-ci`; локальный запуск `make test` обязателен перед коммитом.

## 5. План по устранению избыточности (ChEMBL Target Component)

В ходе аудита пайплайна `chembl_target_component` был выявлен риск многократного извлечения одних и тех же данных. План исправления:

1. **Дедупликация на стороне клиента**: Внедрение `seen-ids` в `ChemblAdapter.fetch-filtered` для обработки дублей, возвращаемых API при использовании сложных фильтров.
1. **Исправление пагинации**: Переход от фиксированного `offset += batch-size` к `offset += len(records)` для предотвращения пропусков данных в Degraded режиме.
1. **Оптимизация параметров**: Передача `limit` напрямую в API запросы для исключения выкачивания лишних записей из ChEMBL.

## 6. Оптимизация Тестов

### 6.1. Параллельное Выполнение (pytest-xdist)

Тесты поддерживают параллельное выполнение через `pytest-xdist`, но локальный
дефолт теперь serial для стабильности:

```bash
# Локальный стабильный дефолт (serial)
make test

# Явный CI-подобный режим (parallel + fallback при worker crash)
make test-ci

# Serial execution (для отладки)
make test-serial

# Явный параллельный запуск вручную
pytest tests/ -m "not serial" -n auto --dist loadscope --max-worker-restart=0
```

**Производительность** (verified 2026-01-19):

- Serial: ~150-180s (зависит от hardware)
- Parallel (auto): ~55-75s (зависит от hardware)
- Улучшение: **~60-65%**

**Статус pytest-xdist**: Используется в CI и explicit local runs; serial tests выполняются отдельным serial-pass.

### 6.2. Hypothesis Профили

Hypothesis настроен с профилями для разных сценариев (см. `tests/conftest.py`):

| Профиль    | max-examples | Использование                  |
| ---------- | ------------ | ------------------------------ |
| `ci`       | 10           | Автоматически в CI (CI=true)   |
| `fast`     | 5            | Быстрый smoke test             |
| `dev`      | 50           | Локальная разработка (default) |
| `thorough` | 200          | Pre-release тестирование       |

```bash
# Использование профилей
HYPOTHESIS_PROFILE=fast uv run python -m pytest tests/unit/
HYPOTHESIS_PROFILE=thorough uv run python -m pytest tests/  # Перед релизом
```

**Важно**: Тесты НЕ должны переопределять `max-examples` в декораторе `@settings()`, чтобы профили работали корректно.

### 6.3. Test Markers

Используйте маркеры для выборочного запуска:

```bash
# Исключить медленные тесты
uv run python -m pytest tests/ -m "not slow"

# Только unit тесты
uv run python -m pytest tests/ -m "unit"

# Только Hypothesis тесты
uv run python -m pytest tests/ -m "hypothesis"

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
├── uv run python -m pytest tests/unit/ -m "not slow"
└── uv run python -m pytest tests/architecture/

Stage 3: Integration (~20s)
└── uv run python -m pytest tests/integration/ --vcr-record=none

Stage 4: E2E (на PR merge)
└── uv run python -m pytest tests/e2e/ -m e2e

Stage 5: Contract (ежемесячно)
└── BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true uv run python -m pytest tests/contract/ --network
```

## 7. Воспроизводимость и Проверка Зависимостей

Для обеспечения стабильной работы Quality Gates (особенно расчёта покрытия и линтинга) в CI-окружении и на машинах разработчиков, проект использует строгую проверку зависимостей.

### 7.1. Полная настройка окружения

Для первичной настройки или восстановления окружения используйте:
```bash
# Канонический локальный bootstrap
make install
make test-deps
make setup-plugins
```

`make setup-dev` остаётся удобным aggregate target поверх `make install` и
dependency verification. `scripts/dev/dev_setup.sh` — legacy placeholder и не
является поддерживаемым onboarding/testing path.

### 7.2. Smoke-check зависимостей и инструментов

Перед запуском основного набора тестов или линтеров необходимо убедиться, что все критические зависимости и инструменты установлены.

**Runtime зависимости:**
```bash
make test-deps
```
Проверяет доступность `pandas`, `pandera`, `polars` и др. Локально это быстрый smoke-check перед `make test`; в CI аналогичная проверка выполняется отдельным `smoke-check` job в `.github/workflows/tests.yml`.

**Инструменты разработки:**
```bash
make test-deps-dev
```
Дополнительно проверяет наличие `ruff`, `mypy`, `detect-secrets` и других инструментов аудита.

### 7.3. Решение проблем с воспроизводимостью

Если аудит или CI падают с ошибками `ModuleNotFoundError`:
1. Выполните `make install` или `make setup-dev`.
2. Убедитесь, что используете `uv run` или активировали виртуальное окружение.
3. Проверьте статус инструментов через `make test-deps-dev`.

В CI для этого используется не `make test`, а отдельный набор шагов в `.github/workflows/tests.yml`: `smoke-check`, quality gates и затем `test-fast` / `test-matrix` / `coverage-verify`.
