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
*No defects found.*

## E. Quantitative Scorecard
**Score: 5 (Mature Implementation)**
- Архитектурные границы строго изолированы и проверяются автоматически (`import-linter` contracts: Domain Independence, Application Independence, Infrastructure Independence, Composition No Interfaces, Interfaces No Direct Infrastructure).
- Все слои соблюдают правила зависимостей (interfaces -> application -> domain; infrastructure -> domain; composition -> application + infrastructure).
- Рантайм циклы жестко контролируются. Обнаружен только 1 легитимный (reviewed) цикл в `interfaces.http.control_plane_identity` (зафиксирован в `test_runtime_import_scc.py`).

## F. Cross-cutting/root-cause clusters
- Не применимо. Нет обнаруженных дефектов.

## G. Prioritized roadmap P0→P3
- Дефектов нет, roadmap для исправлений пуст.

## H. Verification Matrix
- `uv run lint-imports`: PASS (6 contracts kept)
- `uv run pytest tests/architecture/test_runtime_import_scc.py`: PASS (4 passed)
- `uv run pytest tests/architecture/test_strict_architecture_contracts.py`: PASS (21 passed)

## I. NOT_VERIFIABLE и missing evidence
- Не применимо. Все проверки и инструменты (линтеры, AST проверки, тесты) были успешно выполнены.

## J. Self-check
- Все зависимости и циклы проверены на pinning revision `82e3000d380aeb0bf30b55bfa8a4f0f4d9782f8e`. Одобренные исключения явно описаны в контрактах тестов (ADR #6037). Данные полностью актуальны.

## K. Verdict
Дефектов архитектурных границ не обнаружено. Слой Composition корректно работает как единая точка сборки. Domain полностью изолирован от I/O и infrastructure. Проект демонстрирует образцовую реализацию слоистой архитектуры и строгих проверок зависимостей.

## Local Output (P01 Специфика)

### Dependency Matrix
Взаимодействия между слоями (направление импорта), основанные на результатах анализа графа и правил. Разрешенные потоки:
- **interfaces** -> **application**, **domain**
- **application** -> **domain**
- **infrastructure** -> **domain**
- **composition** -> **interfaces**, **application**, **infrastructure**, **domain**
- **domain** -> нет внешних зависимостей.

### Edge Register
Все импорты строго соответствуют правилам, межслойные запрещенные ребра (forbidden edges) отсутствуют:
- **0 forbidden runtime edges** обнаружено скриптами анализа (анализ 3041 layer crossing edges не выявил нарушений).
- При обнаружении все ребра имели вердикт `allowed`.

### Cycle Inventory
- **Отклоненные / неревьюированные циклы (unreviewed SCCs)**: 0
- **Разрешенные циклы (sanctioned exception)**:
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
