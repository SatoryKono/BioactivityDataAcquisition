# Architecture Audit Report

Date: 2026-03-03
Scope: `src/bioetl`, `tests/architecture`, active documentation consistency checks.

## Verification Log (executed)

- `uv run python -m pytest tests/architecture -q` → **failed** (1 failure in documentation sync test).
- `uv run python -m mypy --strict src/bioetl` → **passed** (`Success: no issues found in 550 source files`).
- `rg --files tests/architecture` → architecture guardrail suite is extensive and active.
- `wc -l ...` + `rg -n '^[[:space:]]*(def|async def) '` on core modules → identified large orchestrator/writer/factory files.

## Executive Summary

- Total findings: **5**
- Critical (P1 / MUST): **1**
- Moderate (P2 / SHOULD): **3**
- Informational (P3): **1**

Проект архитектурно зрелый: есть сильные автоматические барьеры (архитектурные тесты + strict typing), соблюдается Medallion и Hexagonal дисциплина в ключевых местах. При этом накапливается локальный технический долг в виде очень крупных модулей и большого списка baseline-exemptions, а также есть активное нарушение в документационном контуре (падает архитектурный тест).

______________________________________________________________________

## Числовая оценка по 10 категориям

| Категория                                    | Что оценивается                                                              |  Вес | Оценка (1–10) | Взвешенный балл |
| -------------------------------------------- | ---------------------------------------------------------------------------- | ---: | ------------: | --------------: |
| 1. Слоистая архитектура                      | Соблюдение границ `domain/application/infrastructure/composition/interfaces` | 0.15 |           8.5 |           1.275 |
| 2. Hexagonal (Ports & Adapters) + DDD        | Контракты портов, инверсия зависимостей, выразительность доменной логики     | 0.12 |           8.0 |           0.960 |
| 3. Модульность и связность                   | Размер модулей, SRP, отсутствие god-modules                                  | 0.10 |           6.0 |           0.600 |
| 4. Типизация и корректность API              | Полнота аннотаций и прохождение `mypy --strict`                              | 0.10 |           9.5 |           0.950 |
| 5. Тестирование и архитектурные guardrails   | Полнота автопроверок, стабильность прогона                                   | 0.12 |           8.0 |           0.960 |
| 6. Обработка ошибок и устойчивость           | Единообразие исключений, retry/circuit-breaker/политики сбоев                | 0.08 |           8.0 |           0.640 |
| 7. Наблюдаемость (логирование/метрики/аудит) | Порты наблюдаемости, запрет print/f-string в логах                           | 0.08 |           8.0 |           0.640 |
| 8. Данные и Medallion-инварианты             | Bronze/Silver/Gold политики, Delta-only в Silver                             | 0.10 |           9.0 |           0.900 |
| 9. Документация и консистентность артефактов | Актуальность активных доков и CI workflow-требований                         | 0.07 |           5.5 |           0.385 |
| 10. Технический долг и сопровождаемость      | Exemptions, сложность изменений, прогноз расширяемости                       | 0.08 |           6.0 |           0.480 |

**Интегральный балл: 7.79 / 10**

### Интерпретация

- **0–4.9**: архитектура в рисковой зоне.
- **5.0–7.9**: архитектура рабочая, но с заметным долгом и зонами риска.
- **8.0–10**: зрелая архитектура с управляемым долгом.

Текущий статус: **верхняя граница среднего диапазона (5.0–7.9)**, близко к зрелому состоянию, но не дотягивает из-за документационного рассинхрона и чрезмерной концентрации ответственности в ряде модулей.

______________________________________________________________________

## Оценка целевой архитектуры

### 1) Слоистая структура

- Позитив: в проекте есть целевой набор архитектурных тестов на границы слоев и purity domain (`test_layer_dependencies.py`, `test_domain_purity.py`).
- Позитив: strict типизация проходит на всем `src/bioetl`.
- Риск: крупные orchestration-модули в `application/` и крупные writer/factory модули размывают практические границы ответственности внутри слоя.

### 2) Ports & Adapters / DDD

- Позитив: `domain/ports` хорошо развит; инфраструктурные writer/adapters реализуют работу через порты и policy объекты.
- Позитив: `SilverWriter` работает через Delta Lake (`deltalake` + merge/upsert), что соответствует Medallion правилам.
- Риск: часть application/composition модулей превращается в «узлы знания обо всем», что снижает заменяемость отдельных адаптеров и orchestration-сценариев.

### 3) Явность границ модулей и зависимостей

- Позитив: автоматические проверки ограничивают запрещенные импорты.
- Риск: высокий LOC и число методов в нескольких ключевых файлах указывает на слабую модульную декомпозицию на уровне пакетов.

### 4) Единообразие naming / package layout

- Позитив: есть явные архитектурные тесты naming/DI/contract policy.
- Риск: исторические исключения в лимитах размера/сложности уже зафиксированы как baseline, что маскирует постепенное разрастание.

______________________________________________________________________

## Findings

## [Critical P1] Active documentation sync breach (pipeline IDs / legacy naming traces)

**Location**: `tests/architecture/test_documentation_sync.py` (assert в `test_no_legacy_kebab_pipeline_ids_in_active_docs`), `docs/exports/full-documentation-no-plans-reports-skills.merged.md`.

**Evidence**:

- Архитектурный тест падает на активной документации: найден legacy kebab-case контент в `docs/exports/full-documentation-no-plans-reports-skills.merged.md`.
- В merged-файле присутствуют legacy source references (`04-reference/pipelines/chembl-activity.md`, `chembl-assay.md`, и т.п.).

**Impact**:

- Красный архитектурный gate в CI для documentation sync.
- Снижение доверия к документации как к источнику истины для pipeline ID conventions.

**Recommendation**:

- Обновить генерацию merged-документа: нормализовать legacy ссылки/идентификаторы в процессе merge.
- Добавить pre-merge check скрипт для docs/exports.

**Verification command**: `uv run python -m pytest tests/architecture -q`

## [Moderate P2] God-module risk in composite orchestration

**Location**: `src/bioetl/application/composite/merger.py` (~1850 LOC, ~44 методов), `src/bioetl/application/composite/runner.py` (~1143 LOC, ~24 методов).

**Evidence**:

- Модули значительно превышают типичный SRP-размер и концентрируют много разнотипной логики (join strategies, key resolution, enrichment flow, retries, writes).

**Impact**:

- Высокая цена изменений и ревью.
- Риск неявных регрессий при добавлении новых composite flow.

**Recommendation**:

- Декомпозировать в набор специализированных сервисов: `JoinPlannerService`, `ConflictResolverService`, `DependencyJoinService`, `MergeExecutionService`, `CheckpointResumeService`.

**Verification command**: `wc -l ...` + `rg -n '^[[:space:]]*(def|async def) ' ...`

## [Moderate P2] Storage writer concentration and policy coupling

**Location**: `src/bioetl/infrastructure/storage/silver_writer.py` (~1230 LOC, ~29 методов).

**Evidence**:

- В одном классе объединены schema coercion, write mode policy handling, retry/merge semantics, metadata coordination, optional validator wiring.

**Impact**:

- Сложность unit-тестирования и локализации дефектов.
- Затрудненная эволюция write policies (особенно при добавлении новых режимов).

**Recommendation**:

- Выделить сервисы: `SilverMergeEngine`, `SilverSchemaCoercionService`, `SilverMetadataFacade`, `SilverWritePolicyExecutor`.

**Verification command**: `wc -l src/bioetl/infrastructure/storage/silver_writer.py`

## [Moderate P2] Baseline-exemption debt is institutionalized

**Location**: `tests/architecture/test_code_metrics.py` (`EXEMPTIONS` large allowlist).

**Evidence**:

- Большой список исключений по LOC/сложности закрепляет исторический долг как норму.

**Impact**:

- Guardrails частично теряют превентивную силу.
- Новые изменения склонны следовать path of least resistance (добавлять в большие модули).

**Recommendation**:

- Ввести «debt burndown policy»: на каждом релизе уменьшать лимиты/exemptions на N%.
- Добавить mandatory ADR для любого нового exemption.

**Verification command**: `sed -n '1,260p' tests/architecture/test_code_metrics.py`

## [Informational P3] Strong architecture controls are a key asset

**Location**: `tests/architecture/*`, `src/bioetl/domain/services/identity_service.py`, `src/bioetl/infrastructure/storage/silver_writer.py`.

**Evidence**:

- Широкий набор architecture tests, strict mypy, отсутствие `print(` в `src/bioetl`, доменная логика хеширования изолирована в domain service, Silver слой использует Delta Lake.

**Impact**:

- Хорошая база для безопасного поэтапного рефакторинга.

**Recommendation**:

- Использовать существующие guardrails как safety-net для инкрементальной декомпозиции крупных модулей.

______________________________________________________________________

## Приоритизированный план рефакторинга

### Шаг 1 (Критично): Восстановить documentation architecture gate

- **Цель**: устранить текущий красный gate архитектурных тестов.
- **Конкретные правки**:
  - Нормализация legacy pipeline-id/path в генераторе `docs/exports/*.merged.md`.
  - Добавить отдельный script/check: fail при kebab-case pipeline-id в активных docs.
- **Риски**: случайно сломать ссылки в архивных документах.
- **Минимизация рисков**: ограничить check scope активными docs (как в текущем тесте), архив исключить.
- **Критерии готово**:
  - `uv run python -m pytest tests/architecture/test_documentation_sync.py -q` зеленый.
  - Нет legacy kebab-case в активных docs/workflows.

### Шаг 2 (Критично): Разделить `CompositeMerger` на domain-agnostic application services

- **Цель**: убрать god-module, снизить связность.
- **Конкретные правки**:
  - Из `application/composite/merger.py` выделить пакеты:
    - `application/composite/join_planning.py`
    - `application/composite/conflict_resolution.py`
    - `application/composite/dependency_joins.py`
    - `application/composite/merge_execution.py`
  - Сохранить фасад `CompositeMerger` как orchestration coordinator.
- **Риски**: изменение порядка операций merge и скрытые регрессии данных.
- **Минимизация рисков**: golden-master tests для merge outputs + snapshot на ключевые composite pipelines.
- **Критерии готово**:
  - LOC `merger.py` < 500.
  - Поведение merge эквивалентно baseline на regression dataset.

### Шаг 3 (Высокий): Декомпозировать `CompositeRunner`

- **Цель**: разделить FSM/checkpoint/lock/orchestration concerns.
- **Конкретные правки**:
  - Выделить `RunStateMachineService`, `CheckpointResumeService`, `ExecutionPhaseScheduler`.
  - Runner оставить как thin coordinator.
- **Риски**: race-condition/lock-handling regressions.
- **Минимизация рисков**: scenario tests (resume, interruption, lock timeout).
- **Критерии готово**:
  - Явный контракт фаз (prepare/load/merge/write/finalize).
  - Сокращение cyclomatic complexity критических методов.

### Шаг 4 (Высокий): Разделить `SilverWriter` по обязанностям

- **Цель**: повысить тестируемость и эволюционность Silver write path.
- **Конкретные правки**:
  - Вынести merge retry/execution в `SilverMergeEngine`.
  - Вынести schema/null coercion в `SilverSchemaCoercionService`.
  - Вынести metadata/audit orchestration в `SilverMetadataFacade`.
- **Риски**: нарушение ACID/merge semantics.
- **Минимизация рисков**: contract tests на idempotency, schema evolution, write mode policy.
- **Критерии готово**:
  - `silver_writer.py` становится orchestration-классом (< 450 LOC).
  - Все существующие storage и architecture tests проходят.

### Шаг 5 (Средний): Упростить composition factory layer

- **Цель**: сделать DI graph прозрачным и предсказуемым.
- **Конкретные правки**:
  - Разбить `pipeline_factory.py` на `provider_factories/*` + `shared_factory_utils.py`.
  - Ввести typed factory protocols для ключевых веток сборки.
- **Риски**: неверная сборка pipeline в edge-конфигурациях.
- **Минимизация рисков**: matrix tests по всем provider/entity конфигам.
- **Критерии готово**:
  - Локальные фабрики по bounded context (chembl/pubmed/uniprot/...)
  - Читаемость DI-графа повышена (1 фабрика = 1 зона ответственности).

### Шаг 6 (Средний): Debt governance — сократить EXEMPTIONS

- **Цель**: вернуть силу quality-gates.
- **Конкретные правки**:
  - В `test_code_metrics.py` ввести политику авто-ужесточения лимитов.
  - Добавить CI check: «новый exemption требует ADR/обоснование».
- **Риски**: краткосрочный рост числа фейлов в CI.
- **Минимизация рисков**: staged rollout (warning mode → fail mode).
- **Критерии готово**:
  - Количество exemptions уменьшается релиз к релизу.
  - Нет новых бесконтрольных исключений.

### Шаг 7 (Желательный): Усилить module boundary observability

- **Цель**: превратить архитектурный аудит в непрерывную метрику.
- **Конкретные правки**:
  - Добавить автоматический экспорт метрик: LOC/CC/file, coupling index, import violations trend.
  - Публиковать dashboard в CI artifacts.
- **Риски**: overhead CI и шум метрик.
- **Минимизация рисков**: ограничить критический набор KPI + weekly trend.
- **Критерии готово**:
  - Видна динамика ключевых архитектурных KPI по времени.

______________________________________________________________________

## Рекомендуемые метрики и тесты против регрессий

1. **Architecture Compliance Index (ACI)**
   - Доля пройденных архитектурных тестов (`tests/architecture`) в %.
1. **Layer Purity Violations**
   - Количество forbidden imports/side effects по слоям.
1. **God-Module Index**
   - Количество файлов > 500 LOC и/или > 20 методов.
1. **Exemption Debt Index**
   - Количество и «вес» записей в `EXEMPTIONS`.
1. **Type Safety Score**
   - Статус `mypy --strict` + количество игнорирований/any-исключений.
1. **Docs Sync Health**
   - Процент проходящих документационных тестов + 0 legacy pipeline IDs.
1. **Silver Contract Health**
   - Контрактные тесты Silver merge/idempotency/schema evolution.
1. **Observability Coverage**
   - Наличие `run_id`/structured logging в pipeline-контексте.
1. **Refactor Safety Coverage**
   - Regression snapshots по composite merge results.
1. **Change Risk Lead Time**

- Среднее время от change request до green CI для core пайплайнов.

### Связка с интегральным баллом

Предлагаемая модель улучшений после выполнения ключевых шагов (1–4 + 6):

- Категория 3 (Модульность): **6.0 → 8.0**
- Категория 5 (Тестирование/guardrails): **8.0 → 8.8**
- Категория 9 (Документация): **5.5 → 8.5**
- Категория 10 (Техдолг): **6.0 → 7.8**

Ожидаемый интегральный балл: **7.79 → ~8.45** при сохранении текущей дисциплины по слоям и типизации.
