---
Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-02'
---

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
- `configs/quality/test_matrix.yaml`
- `configs/quality/integration_vcr_policy.yaml`

Canonical named pytest lanes are defined in
`configs/quality/test_matrix.yaml` under `test_lanes.lanes`. Test-health tooling
must use these `suite_name` values for comparable local and CI runs:

- `unit-fast`: `tests/unit/`, excluding `slow`, `benchmark`, and `memory`;
- `integration-replay`: `tests/integration/` in VCR replay-only mode;
- `contracts`: schema, contract, and snapshot tests;
- `architecture`: layer boundary, contract, and governance checks;
- `e2e`: dedicated slow end-to-end lane;
- `memory`: dedicated Neo4j project-memory and MCP lane, outside coverage;
- `coverage-verify`: the only lane that enforces the repo-wide coverage gate.

Large local runs should use the maintained sharded runner rather than invoking
pytest directly:

```powershell
$env:PYTHONPATH="src"
bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=html
```

The same execution contract is represented in `test_lanes.execution_defaults`;
future test-health tooling should preserve the logical `suite_name` while
recording sharded runner details separately.

Canonical local execution paths:

- **CI / single-OS checkout**: `uv run python -m ...` или поддерживаемые
  Make targets (`make test`, `make test-fast`, `make test-architecture`).
- **Mixed Windows + WSL checkout (PowerShell)**:
  `.\scripts\engineering\dev\setup_env_windows.ps1`,
  `.\scripts\engineering\dev\run_pytest.ps1`, `.\scripts\engineering\dev\run_mypy.ps1`.
- **Mixed Windows + WSL checkout (WSL/Linux)**:
  `bash scripts/engineering/dev/setup_env_wsl.sh`,
  `bash scripts/engineering/dev/run_pytest.sh`, `bash scripts/engineering/dev/run_mypy.sh`.

Wrappers `run_pytest.ps1|.sh` по умолчанию добавляют флаги
`--cov=src/bioetl --cov-report=term -q --maxfail=1`, если запуск не был вызван
с `--help` / `--version`. WSL-обёртка дополнительно вызывает
`scripts/ops/launchers/codex/setup_plugins.sh --pytest-only` перед запуском pytest.

Supported policy slice for issue `#2598`:

- **Integration**: canonical roots `tests/integration/adapters/`,
  `tests/integration/chembl/`, `tests/integration/composite/`,
  `tests/integration/config/`, `tests/integration/infrastructure/`,
  `tests/integration/interfaces/`, `tests/integration/pipelines/`,
  `tests/integration/validation/`, `tests/integration/ci/`.
- **Integration provider families**: replay-first adapter coverage for `chembl`,
  `pubchem`, `pubmed`, `semanticscholar`, `uniprot`; mixed replay/mock adapter
  coverage for `crossref` and `openalex`; pipeline replay smoke for
  `chembl_activity`, `chembl_cell_line`, `chembl_compound_record`,
  `chembl_target_component`, `pubchem_compound`, `uniprot_protein`.
- **E2E provider families**: `chembl_activity`, `chembl_assay`,
  `chembl_molecule`, `chembl_publication`, `chembl_publication_term`,
  `chembl_target`, `crossref_publication`, `openalex_publication`,
  `pubchem_compound`, `pubmed_publication`, `semanticscholar_publication`,
  `uniprot_protein`.
- **E2E scenario families**: `advanced_scenarios`, `checkpoint`,
  `full_pipeline`, `full_pipeline_chain`, `run_types`.
- **Default replay mode**: local development should prefer replay with
  `--vcr-record=none` for stable feedback loops. Targeted refresh is supported
  via `--vcr-record=new_episodes`; broad cassette rewrites are not the
  supported default path.

Текущее состояние rollout по ADR-042:
- mutation testing в CI блокирует только `domain/` с порогом `70%`
- `application/` mutation target (`60%`) задокументирован, но пока staged и не является blocking gate
- VCR cassette metadata (`*_meta.yaml`) перешли в `partial` rollout: в `configs/quality/test_matrix.yaml` теперь явно объявлен current seeded sidecar slice, минимальный provider-coverage rule (`at least one sidecar per VCR-managed provider`) и текущие expected sidecar counts per provider, а canonical backfill tool уже зафиксирован как supported path, но metadata coverage пока не repo-wide и потому enforcement остаётся неполным
- `vcr_cassette_max_age_days: 90` уже является нормативным stale-age threshold, а repo-wide age rollout теперь `partial`: архитектурные тесты требуют наличие `_meta.yaml` inventory, но CI пока не делает stale-age blocking gate для всего дерева
- canonical VCR metadata catalog теперь существует как tracked artifact в `reports/quality/vcr-metadata-catalog.json`
- canonical tooling paths активированы для partial rollout: `scripts/engineering/qa/report_vcr_metadata_catalog.py` генерирует/проверяет catalog, а `scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py` служит canonical backfill entry point; при этом workflow-level automated backfill всё ещё не включён
- descriptive test-health taxonomy теперь canonical-фиксируется в `configs/quality/test_health_reporting.yaml`; статусы `fully_exercised_green`, `staged_green`, `environment_limited_green` остаются informational и не заменяют merge-blocking CI status
- monthly `contract-tests.yml` остаётся активным live-network workflow и должен запускать `tests/contract/` с `BIOETL_LIVE_API_TESTS=true`, `BIOETL_NETWORK_TESTS=true` и `--network`
- monthly `contract-tests.yml` выполняется только в canonical repository `SatoryKono/BioactivityDataAcquisition`, а failure issue внутри workflow ссылается на этот guide как на поддерживаемый policy/runbook entry point
- минимальный live-contract baseline теперь полностью enforceable: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar` обязаны иметь live contract suites
- для `semanticscholar` live governance теперь разделена:
  - `tests/contract/test_semanticscholar_contract.py` содержит promotion-grade путь;
  - `tests/contract/test_semanticscholar_contract_pilot.py` содержит richer pilot-soak проверки и требует `BIOETL_PILOT_SOAK_TESTS=true` или `--pilot-soak`
- текущие silver schema snapshots уже живут в `tests/contract/silver_schemas/snapshots/`; внешний provider-facing registry `tests/fixtures/contracts/{provider}/v{version}.json` тоже уже активирован как bounded live-provider baseline для `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar` и не заменяет schema snapshots
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

#### 2.1.2. Pure Transformation Logic Baseline

Pure transformation logic считается отдельным high-signal unit-test surface для:

- функций в `src/bioetl/domain/transformations/`;
- pure helpers и dict-level transformers в `src/bioetl/application/core/`,
  если они работают только in-memory и не оркестрируют adapters, storage или
  runtime lifecycle.

Для такого класса тестов canonical expectations следующие:

- тесты должны быть детерминированными и работать только в памяти;
- входы и ожидаемые выходы должны быть зафиксированы явно, без скрытой
  зависимости от времени, сети, filesystem, random state или глобального
  runtime context;
- failure/edge behavior должен проверяться так же явно, как happy path;
- in-memory fakes допустимы только там, где helper нельзя протестировать как
  чистую функцию, но для pure transformation logic прямой input/output assertion
  остаётся предпочитаемым стилем.

Минимальный edge-case baseline для новых и изменяемых pure transformation tests:

- empty inputs;
- malformed inputs;
- Unicode значения и строковая нормализация без потери смысла;
- `null` / missing values и их deterministic fallback semantics.

Подходящие canonical examples в репозитории:

- `tests/unit/domain/transformations/test_coercion.py`
- `tests/unit/domain/test_transformations.py`
- `tests/unit/application/core/test_dict_transformers.py`

Рекомендуемый execution path для этого baseline:

```bash
# CI / single-OS
uv run python -m pytest -q tests/unit/domain/transformations/test_coercion.py
uv run python -m pytest -q tests/unit/application/core/test_dict_transformers.py
uv run python -m pytest -q tests/architecture/test_domain_unit_test_purity.py

# Mixed Windows + WSL checkout (WSL)
bash scripts/engineering/dev/run_pytest.sh tests/unit/domain/transformations/test_coercion.py
bash scripts/engineering/dev/run_pytest.sh tests/unit/application/core/test_dict_transformers.py
bash scripts/engineering/dev/run_pytest.sh tests/architecture/test_domain_unit_test_purity.py
```

Если изменение затрагивает только pure transformation logic, такой targeted run
считается поддерживаемым local feedback path до более широкого `make test-fast`
или полного `make test`.

### 2.2. Integration Tests (`tests/integration/`)

Проверка взаимодействия компонентов с внешними API и хранилищем.

- **Адаптеры**: Тестирование HTTP-клиентов (ChEMBL, PubChem, UniProt) с использованием VCR-кассет.
- **Storage**: Проверка записи в Delta Lake и Bronze хранилище (используются локальные временные пути).
- **VCR Policy**: canonical machine-readable policy живёт в `configs/quality/integration_vcr_policy.yaml`. Кассеты хранятся в `tests/fixtures/vcr/`, а стандартный CI path использует `--vcr-record=none`.
- **Compatibility Policy**: `pytest-vcr` должен импортироваться против locked `wrapt` dependency из активного окружения. Repo-root workaround'ы вроде `wrapt/` или `sitecustomize.py` не считаются поддерживаемым fix path; если импорт ломается, нужно чинить environment/lock, а не shadowing dependency.
- **Fixture Governance**: `_meta.yaml` sidecars и stale-age policy находятся в `partial` rollout. Репозиторий уже держит matrix-declared seeded sidecar inventory и canonical catalog, но глобальный enforcement ещё не repo-wide.
- **Catalog / Backfill Policy**: canonical VCR metadata catalog и canonical backfill script уже существуют, но automated workflow rollout всё ещё остаётся неполным; это состояние фиксируется matrix и architecture guard'ами.
- **Live Contract Baseline**: live-network enforcement обязателен для `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`; richer pilot-soak coverage for Semantic Scholar remains opt-in and does not redefine the enforced baseline.

#### 2.2.1. Supported integration families

В рамках tracked policy `#2598` проект явно поддерживает следующие integration
surface areas:

- `tests/integration/adapters/` — adapter-level HTTP replay и mixed-mode adapter
  checks.
- `tests/integration/pipelines/` — pipeline-level replay smoke для
  `chembl_activity`, `chembl_cell_line`, `chembl_compound_record`,
  `chembl_target_component`.
- `tests/integration/test_pubchem_pipeline.py` и
  `tests/integration/test_uniprot_pipeline.py` — репрезентативные provider
  pipeline smoke paths.
- `tests/integration/interfaces/`, `tests/integration/config/`,
  `tests/integration/composite/`, `tests/integration/validation/`,
  `tests/integration/ci/` — governance/runtime-facing integration surfaces,
  которые не обязаны использовать VCR, но входят в canonical integration scope.

CrossRef и OpenAlex допускают mixed replay/mock режим на adapter-level coverage.
Это считается supported policy, а не отклонением, пока machine-readable policy и
guide остаются синхронизированными.

Concrete file-level inventory для canonical integration surface живёт в
`configs/quality/integration_vcr_policy.yaml -> tracked_suite_inventory.integration`.
Новые `tests/integration/test_*.py` и `tests/integration/**/test_*.py` должны либо
попасть в этот inventory, либо считаться policy drift.

#### 2.2.2. Canonical replay and refresh commands

```bash
# CI / single-OS replay
uv run python -m pytest tests/integration/ --vcr-record=none -m "integration and not e2e"

# Windows replay
.\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"

# WSL replay
bash scripts/engineering/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"

# Targeted refresh only
uv run python -m pytest tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v
```

`--vcr-record=once` остаётся локальным compatibility default в `tests/conftest.py`
для ad-hoc runs без явного режима, но policy-first execution path для supported
integration replay должен задавать `--vcr-record=none`. Это уменьшает риск
случайной перезаписи кассет во время обычного dev feedback loop.

### 2.3. End-to-End (E2E) Tests (`tests/e2e/`)

Тестирование полного цикла работы пайплайна.

- **Сценарий**: `Run ID` -> `Fetch` -> `Bronze` -> `Silver` -> `Gold`.
- **Архитектура**: Local-Only (MemoryLock, LocalCheckpoint, FileSystem Storage).
- **Запуск**: `uv run python -m pytest tests/e2e/ -m e2e -v`.

#### 2.3.1. Supported E2E families

Canonical provider-facing E2E families:

- `chembl_activity`
- `chembl_assay`
- `chembl_molecule`
- `chembl_publication`
- `chembl_publication_term`
- `chembl_target`
- `crossref_publication`
- `openalex_publication`
- `pubchem_compound`
- `pubmed_publication`
- `semanticscholar_publication`
- `uniprot_protein`

Concrete file-level inventory для canonical E2E surface живёт в
`configs/quality/integration_vcr_policy.yaml -> tracked_suite_inventory.e2e`.
Это включает provider runs, scenario runs и tracked governance/resilience
surfaces. Новый `tests/e2e/test_*.py` без inventory update считается policy drift.

Canonical scenario E2E families:

- `advanced_scenarios`
- `checkpoint`
- `full_pipeline`
- `full_pipeline_chain`
- `run_types`

Supported replay/refresh commands:

```bash
# Replay-first E2E run
uv run python -m pytest tests/e2e/ -m e2e --vcr-record=none -v

# Windows replay
.\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none

# WSL replay
bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none

# Targeted refresh only
uv run python -m pytest tests/e2e/test_pubchem_compound_e2e.py -m e2e --vcr-record=new_episodes -v
```

Standard CI replay path for E2E — это не полный `tests/e2e/` run, а
control-plane smoke target
`tests/e2e/test_pubchem_compound_e2e.py::test_pubchem_compound_full_cycle` с
`VCR_RECORD_MODE=none` и `--vcr-record=none`.

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

- **Blocking CI Threshold**: merge-gate в CI использует `coverage report --fail-under=85`, то есть blocking threshold для репозитория составляет **>=85%** общего line coverage.
- **Domain Coverage Goal**: для доменного слоя по-прежнему желателен более высокий локальный стандарт, но он не является отдельным blocking CI gate, пока workflow не вводит отдельный `fail-under` для domain-only coverage.
- **Branch Coverage**: Проверяется автоматически через `pytest-cov`.
- **Regression**: Все исправления багов обязаны сопровождаться регрессионным тестом.
- **Coverage Configuration**: Подробная информация о настройке покрытия, исключаемых паттернах и troubleshooting — см. [Coverage Configuration Guide](./coverage-configuration.md)

## 4. Как запускать тесты

```bash
# Запуск локального стабильного test suite (без E2E)
make test

# Быстрый локальный feedback loop
make test-fast

# Быстрый и стабильный coverage-run (parallel non-serial + serial pass)
make test-cov-fast-stable

# CI-подобный устойчивый прогон (parallel + fallback + serial pass)
make test-ci

# Запуск E2E в Local-Only режиме
uv run python -m pytest tests/e2e/ -m e2e -v

# Mixed Windows + WSL checkout (PowerShell)
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf

# Mixed Windows + WSL checkout (WSL/Linux)
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n 4 --lf

# Запуск только архитектурных тестов
make test-architecture

# Точечное обновление VCR кассет
uv run python -m pytest tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v

# Генерация HTML coverage report после coverage-run
uv run coverage html -d reports/coverage/htmlcov
```

### 4.2. Integration / E2E execution matrix

| Surface | CI / single-OS | Windows PowerShell | WSL/Linux | Notes |
| ------- | --------------- | ------------------ | --------- | ----- |
| Integration replay | `uv run python -m pytest tests/integration/ --vcr-record=none -m "integration and not e2e"` | `.\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"` | `bash scripts/engineering/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"` | canonical stable feedback path |
| E2E replay | `uv run python -m pytest tests/e2e/ -m e2e --vcr-record=none -v` | `.\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none` | `bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none` | local-only execution, no live network |
| Targeted cassette refresh | `uv run python -m pytest <target> --vcr-record=new_episodes -v` | `.\scripts\engineering\dev\run_pytest.ps1 <target> --vcr-record=new_episodes -v` | `bash scripts/engineering/dev/run_pytest.sh <target> --vcr-record=new_episodes -v` | supported refresh path |
| Live contract verification | `uv run pytest tests/contract/ -v --tb=short --network` | n/a | n/a | scheduled/manual workflow path, separate from replay policy |

### 4.3. Cassette lifecycle rules

- **Standard CI** must keep VCR replay locked to `none`.
- **Default local supported path** should also prefer explicit replay via
  `--vcr-record=none`.
- **Targeted refresh** should use `--vcr-record=new_episodes`; repo-wide
  cassette rewrites are not the supported default path.
- **Refresh triggers** include missing cassette for an already-supported path,
  intentional adapter request-shape change, or replay divergence confirmed by a
  contract/schema-drift investigation.
- **Review is required** after refresh when request parameters, headers,
  pagination shape, redaction coverage, or extensionless filename status
  change.
- **Stale signals** include `_meta.yaml` age above `90` days where metadata
  exists, moved provider/pipeline paths without policy updates, or replay shape
  changes without review note.
- **Pre-refresh checks**:
  - `python -m scripts.engineering.qa.vcr check-placement`
  - `python -m scripts.engineering.qa.vcr check-naming`
- **Post-refresh checks**:
  - `python -m scripts.engineering.qa.vcr check-placement`
  - `python -m scripts.engineering.qa.vcr check-naming`
  - `python -m scripts.engineering.qa.vcr check-secrets`
  - `python -m scripts.engineering.qa report-vcr-metadata --check`

### 4.1. Быстрый старт для рекомендуемого локального прогона

| Шаг | Команда | Назначение |
| --- | ------- | ---------- |
| 1 | `make install` | CI/single-OS bootstrap через `uv sync` или `.venv` fallback |
| 2 | `setup_env_windows.ps1` / `setup_env_wsl.sh` | Mixed-checkout bootstrap в `.venv-win` или `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` |
| 3 | `make test-fast` | Получить быстрый feedback для unit + architecture |
| 4 | `make test` | Выполнить стабильный локальный прогон с coverage gate 85% |
| 5 | `make test-cov-fast-stable` | Выполнить ускоренный split-run для локального coverage анализа |
| 6 | `uv run coverage html -d reports/coverage/htmlcov` | Сгенерировать HTML coverage report при необходимости |
| 7 | `uv run python -m pytest tests/e2e/ -m e2e -v` | Отдельно запустить E2E в Local-Only режиме |

**Примечания:**

- Если нужен быстрый coverage-run без полного serial suite, используйте `make test-cov-fast-stable`.
- Для корректного прохождения трассировки и мониторинга установите опциональные зависимости (`psutil`, `opentelemetry-*`).
- `make test` не генерирует `reports/coverage/htmlcov/` автоматически; HTML-отчёт создаётся отдельной командой `uv run coverage html -d reports/coverage/htmlcov`.
- В CI используется `.github/workflows/tests.yml`, а локальный `make test-ci` служит способом воспроизвести resilient flow вручную.
- В mixed Windows + WSL checkout `.venv` не должен быть общим между PowerShell и WSL: используйте `.venv-win` и внешний WSL venv через `setup_env_windows.ps1` / `setup_env_wsl.sh`.

## 5. План по устранению избыточности (ChEMBL Target Component)

В ходе аудита пайплайна `chembl_target_component` был выявлен риск многократного извлечения одних и тех же данных. План исправления:

1. **Дедупликация на стороне клиента**: Внедрение `seen-ids` в `ChemblAdapter.fetch-filtered` для обработки дублей, возвращаемых API при использовании сложных фильтров.
1. **Исправление пагинации**: Переход от фиксированного `offset += batch-size` к `offset += len(records)` для предотвращения пропусков данных в Degraded режиме.
1. **Оптимизация параметров**: Передача `limit` напрямую в API запросы для исключения выкачивания лишних записей из ChEMBL.

## 6. Оптимизация Тестов

### 6.1. Параллельное Выполнение (pytest-xdist)

Тесты поддерживают параллельное выполнение через `pytest-xdist`, но локальный
дефолт остаётся serial для стабильности. Каноническая стратегия такая:

```bash
# Локальный стабильный дефолт (serial)
make test

# Быстрый локальный feedback loop (parallel-safe subset)
make test-fast

# Быстрый split coverage run
make test-cov-fast-stable

# Serial execution (для отладки)
make test-serial

# Явный параллельный запуск вручную
uv run pytest tests/ -m "not serial" -n auto --dist loadscope --max-worker-restart=0
```

Текущие правила:

- `xdist` используется только для explicit local runs и CI lanes;
- тесты с `@pytest.mark.serial` не смешиваются с parallel-safe subset;
- для worker grouping используется `--dist loadscope`;
- для прозрачной диагностики worker crashes используется `--max-worker-restart=0`;
- benchmark runs выполняются отдельно и без `xdist`.

Репозиторий не использует hard-coded performance SLA в документации, потому что
timings зависят от hardware, Python version, coverage mode и состава shard-ов.
Для актуального baseline используйте `make test-profile` и фиксируйте команду,
дату и окружение.

### 6.2. Hypothesis Профили

Hypothesis настроен с профилями для разных сценариев (см. `tests/conftest.py`):

| Профиль    | max-examples | Использование                  |
| ---------- | ------------ | ------------------------------ |
| `ci`       | 10           | Автоматически в CI (CI=true)   |
| `fast`     | 5            | Быстрый smoke test             |
| `dev`      | 50           | Более глубокий локальный прогон |
| `thorough` | 200          | Pre-release тестирование       |

```bash
# Использование профилей
HYPOTHESIS_PROFILE=fast uv run python -m pytest tests/unit/
HYPOTHESIS_PROFILE=dev uv run python -m pytest tests/unit/  # Более широкий локальный прогон
HYPOTHESIS_PROFILE=thorough uv run python -m pytest tests/  # Перед релизом
```

**Default profile**: `fast`, если `HYPOTHESIS_PROFILE` не задан.

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
- `serial` — Тесты, которые должны идти без `xdist`
- `benchmark` — Benchmark-тесты, исключённые из стандартных запусков
- `contracts` — Contract tests
- `no_api` — Contract tests, не требующие live API access

### 6.4. CI Test Layering

CI использует job-based layering, а не один линейный `pytest` прогон:

```
tests.yml
├── smoke-check
├── governance-preflight
├── config-schema-preflight
├── test-fast
├── test-matrix
├── performance-budgets
├── coverage-verify
├── duration-telemetry
├── control-plane-e2e
├── track-d-gates
└── dq-consistency-gate

contract-tests.yml
└── scheduled/manual live contract workflow for tests/contract/

provider-contract-drift.yml
└── replay-based provider API drift gate for provider-facing snapshots
```

Ключевые свойства текущего CI:

- `test-fast` даёт быстрый feedback для unit + architecture;
- `test-matrix` шардирует unit/integration/security по test groups и Python versions;
- `coverage-verify` не rerun-ит весь suite, а объединяет shard coverage и отдельно догоняет только `serial` subset;
- live contract tests вынесены в отдельный workflow и не являются частью обычного PR path;
- replay drift gate работает отдельно от live path и использует существующие
  `tests/fixtures/contracts/{provider}/v{version}.json` + curated VCR cassettes
  как default PR/CI baseline;
- live contract workflow guarded to repository `SatoryKono/BioactivityDataAcquisition`; в нём `tests/contract/` запускаются только при `BIOETL_LIVE_API_TESTS=true`, `BIOETL_NETWORK_TESTS=true` и флаге `--network`;
- `provider-contract-drift.yml` генерирует machine-readable artifact
  `reports/quality/provider-contract-drift-report.json` и hard-fail'ит только на `breaking`
  drift; `warning` остаётся видимым в artifact для PR review;
- `duration-telemetry` собирает JUnit telemetry и публикует slow-test artifact.

## 7. Воспроизводимость и Проверка Зависимостей

Для обеспечения стабильной работы Quality Gates (особенно расчёта покрытия и линтинга) в CI-окружении и на машинах разработчиков, проект использует строгую проверку зависимостей.

### 7.1. Полная настройка окружения

Для первичной настройки или восстановления окружения используйте:
```bash
# Канонический локальный bootstrap
make install
make test-deps
make setup-plugins

# Mixed Windows + WSL checkout
.\scripts\engineering\dev\setup_env_windows.ps1
bash scripts/engineering/dev/setup_env_wsl.sh
```

`make setup-dev` остаётся удобным aggregate target поверх `make install` и
dependency verification. `scripts/engineering/dev/dev_setup.sh` — legacy placeholder и не
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
2. В mixed Windows + WSL checkout пересоберите правильное OS-specific окружение через `setup_env_windows.ps1` или `setup_env_wsl.sh`, а затем запускайте `run_pytest.ps1|.sh` / `run_mypy.ps1|.sh`.
3. Проверьте статус инструментов через `make test-deps-dev`.

В CI для этого используется не `make test`, а отдельный набор шагов в
`.github/workflows/tests.yml`: короткий `smoke-check`, затем независимые
`governance-preflight` и `config-schema-preflight`, после чего стартуют
`test-fast` / `test-matrix`, а в финале `coverage-verify` объединяет coverage
shard-ы и отдельно догоняет только `serial`-тесты. Pytest/Hypothesis cache
при этом кэшируется не по всему `tests/**/*.py`, а по scoped fingerprint для
конкретного workflow или test-family, чтобы локальные изменения не
инвалидировали весь test-cache в CI. Отдельный `duration-telemetry` job
собирает JUnit telemetry из быстрых lanes и публикует artifact со списком
самых медленных тестов.
