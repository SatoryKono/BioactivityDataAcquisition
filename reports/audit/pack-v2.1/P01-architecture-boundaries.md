# P01. Архитектурные границы и dependency rules

## A. Audit Manifest
- **Repo**: `https://github.com/SatoryKono/BioactivityDataAcquisition`
- **Branch**: `main`
- **Pinned Revision**: `82e3000d380aeb0bf30b55bfa8a4f0f4d9782f8e`
- **Scope**: repo-wide architecture boundaries (interfaces, application, domain, infrastructure, composition)
- **Date**: 2026-11-02
- **Mode**: READ_ONLY

## B. Scope/ownership и exclusions
- **Включено**: Взаимосвязи между слоями Hexagonal Architecture (`domain`, `application`, `infrastructure`, `interfaces`, `composition`).
- **Исключено**: Внутреннее устройство `src/memory` (scaffolding и tooling). Type-checking импорты (`TYPE_CHECKING`) отделены от runtime/dynamic-импортов и не считаются архитектурными зависимостями в рантайме.
- **Инструменты**: `uv run lint-imports` (importlinter), внутренние тесты на циклические зависимости (`tests/architecture/test_runtime_import_scc.py`), строгие проверки границ (`tests/architecture/test_strict_architecture_contracts.py`), и анализ графа импортов (`scripts.engineering.qa.import_graph_inventory`).

## C. Evidence Ledger
- `E2-STATIC-LINTER`: `.importlinter` configuration and `uv run lint-imports` passing results.
- `E2-STATIC-TEST-STRICT`: `tests/architecture/test_strict_architecture_contracts.py` ensuring pure domain layer and interface rules.
- `E3-EXECUTABLE-SCC`: `uv run pytest tests/architecture/test_runtime_import_scc.py` execution output confirming cycle checks pass.
- `E4-RUNTIME-GRAPH`: Generated runtime dependency graph using internal QA scripts, showing 0 unreviewed runtime edges crossing forbidden layers.

## D. Findings Register
*No violations were found in the static layer contracts and the `static_runtime_base_modules` projection checked below. Other ownership-graph SCCs remain unclassified by this audit.*

## E. Quantitative Scorecard
**Score: 4 (Strong Implementation; projection-limited evidence)**
- Layer boundaries are enforced by the listed import-linter contracts and architecture tests.
- Матрица зависимостей ниже ограничена проверенной проекцией. Core directions: `interfaces -> application -> domain`; `interfaces -> composition` разрешён через composition-owned entrypoints; `composition -> application/infrastructure/domain`; `infrastructure -> domain`. Зависимость `composition -> interfaces` запрещена контрактом `composition-no-interfaces`.
- SCC выводы зависят от проекции графа. Тесты ниже проверяют только `static_runtime_base_modules`; ownership projection содержит дополнительные SCC и не трактуется автоматически как набор import-time runtime-циклов или архитектурных дефектов.

## F. Cross-cutting/root-cause clusters
- Не применимо. Нет обнаруженных дефектов.

## G. Prioritized roadmap P0→P3
- Дефектов нет, roadmap для исправлений пуст.

## H. Verification Matrix
- `uv run lint-imports`: PASS (6 contracts kept)
- `uv run pytest tests/architecture/test_runtime_import_scc.py`: PASS (4 passed)
- `uv run pytest tests/architecture/test_strict_architecture_contracts.py`: PASS (21 passed)

## I. NOT_VERIFIABLE и missing evidence
- SCC classification for the broader ownership projection remains `NOT_VERIFIABLE`. The tests below do not establish that every ownership SCC is an import-time cycle or an approved exception.

## J. Self-check
- Проверки привязаны к pinning revision `82e3000d380aeb0bf30b55bfa8a4f0f4d9782f8e`. Результат `static_runtime_base_modules` не распространяется на ownership projection. Остальные SCC требуют отдельной классификации; этот отчёт не объявляет их одобренными или дефектными.

## K. Verdict
В закреплённой ревизии статические проверки перечисленных контрактов не обнаружили нарушений в своей области. Этот вывод не распространяется на все SCC ownership-графа.

## Local Output (P01 Специфика)

### Dependency Matrix
Взаимодействия между слоями (направление импорта), основанные на результатах анализа графа и правил. Разрешенные потоки:
- **interfaces** -> **application**, **domain**
- **interfaces** -> **composition** (через composition-owned entrypoints; direct infrastructure imports remain forbidden)
- **application** -> **domain**
- **infrastructure** -> **domain**
- **composition** -> **application**, **infrastructure**, **domain**
- **domain** -> нет внешних зависимостей.

### Edge Register
Для проверенной проекции `static_runtime_base_modules` запрещённые рёбра не обнаружены: анализ 3041 layer-crossing edges не выявил нарушений. Результат относится только к этой статической проекции, а не к остальным проекциям графа.

### Cycle Inventory
- **Проекция `static_runtime_base_modules`, покрытая `test_runtime_import_scc.py`**: один разрешённый SCC. Это ограниченный статический граф, а не полный ownership-граф.
- **Ownership-проекция `find_import_sccs(report.projections.ownership)`**: 9 SCC по review evidence для закреплённой ревизии. Проекция включает ownership/deferred связи, поэтому SCC не являются автоматически import-time runtime-циклами или архитектурными дефектами. Пример: `domain.value_objects.dq_metrics` и `dq_metrics_calculations` связаны отложенным импортом. Девять SCC остаются `NOT_VERIFIABLE` до отдельной классификации; этот аудит не объявляет их `allowed` или `defect`.
- **Цикл в тестируемой статической проекции**:
  - `interfaces.http.control_plane_identity.anchor_values`
  - `interfaces.http.control_plane_identity.checkpoint_extractors`
  - `interfaces.http.control_plane_identity.ledger_extractors`
  - `interfaces.http.control_plane_identity.manifest_extractors`
  - `interfaces.http.control_plane_identity.replay_extractors`
  - *Обоснование (ADR #6037)*: Функционально связанная группа для работы с идентичностью.

### Guardrail Coverage Matrix
| Guardrail | Enforcement Method | Coverage / Exclusions |
| --- | --- | --- |
| Domain purity | `.importlinter` / `test_strict_architecture_contracts` | 100% |
| App layer isolation | `.importlinter` / `test_strict_architecture_contracts` | 100% |
| DI Injection Root | `importlinter:contract:no-direct-instantiation-in-application` | 100% (only via composition root allowed) |
| Runtime SCC budgets | `test_runtime_import_scc.py` | 1 allowed SCC, strict limit enforced |

### Target Dependency Matrix
Только для подтвержденных дефектов. Так как дефектов нет, матрица пуста.
