# Architecture Review And Refactor Plan

Дата: 2026-03-21  
Статус: supporting execution plan  
Язык: русский

## Назначение

Этот документ фиксирует полный архитектурный обзор проекта и приоритизированный
план рефакторинга на основе текущего состояния кода, active evidence packs,
архитектурных guardrails, `ruff`, `mypy --strict` и локальной валидации
структурных seams.

Это **не** второй competing backlog вместо
[consolidated-open-tasks-plan-2026-03-21.md](./consolidated-open-tasks-plan-2026-03-21.md).
Этот файл нужно использовать как архитектурную карту решений:

- для оценки качества текущего состояния;
- для выбора следующей refactor wave;
- для обоснования bounded implementation slices;
- для сравнения ожидаемого эффекта по интегральному баллу.

## Источники

- [architecture-foundations/SUMMARY.md](../reports/evidence/architecture-foundations/SUMMARY.md)
- [project-package-topology/SUMMARY.md](../reports/evidence/project-package-topology/SUMMARY.md)
- [project-import-governance/SUMMARY.md](../reports/evidence/project-import-governance/SUMMARY.md)
- [project-naming-drift/SUMMARY.md](../reports/evidence/project-naming-drift/SUMMARY.md)
- [project-documentation-drift/SUMMARY.md](../reports/evidence/project-documentation-drift/SUMMARY.md)
- [project-test-health/SUMMARY.md](../reports/evidence/project-test-health/SUMMARY.md)
- [technical-debt/SUMMARY.md](../reports/evidence/technical-debt/SUMMARY.md)
- [dependency-hotspots/SUMMARY.md](../reports/evidence/dependency-hotspots/SUMMARY.md)
- [refactor-backlog-calibration/SUMMARY.md](../reports/evidence/refactor-backlog-calibration/SUMMARY.md)
- [project-evidence-rebaseline cross-synthesis](../reports/evidence/project-evidence-rebaseline/03-synthesis/CROSS-SYNTHESIS-project-evidence-rebaseline.md)

## Итоговая оценка

Интегральный балл проекта: **7.16 / 10**

Интерпретация:

- `0.0–4.9` — критическое состояние
- `5.0–7.9` — удовлетворительно, требуется системный рефакторинг
- `8.0–10.0` — хорошее состояние, точечные улучшения

Текущий вывод: проект находится в **верхней части диапазона “удовлетворительно”**.
Архитектура в целом сильная и реально enforced, но несколько локальных seams
создают заметный drag на changeability, readability и governance clarity.

## Таблица оценки

| Категория | Описание | Вес | Оценка (1–10) | Взвешенный балл |
|---|---|---:|---:|---:|
| Соблюдение слоёв | Import matrix, чистота `domain`, отсутствие недопустимых связей | 0.14 | 7.0 | 0.98 |
| Hexagonal и DDD | Соответствие Ports & Adapters, Medallion, DDD primitives | 0.11 | 8.0 | 0.88 |
| Границы модулей | Явность package boundaries, фасадов и dependency seams | 0.10 | 7.0 | 0.70 |
| DI и composition | Constructor injection, composition root, отсутствие service locator | 0.10 | 8.0 | 0.80 |
| Нейминг и semantic contracts | Ясность имён, naming families, facade semantics | 0.08 | 6.0 | 0.48 |
| Конфигурация и governance | SSOT, compatibility inventories, policy vs derived surfaces | 0.12 | 5.0 | 0.60 |
| Тестовая архитектура | Regression net, architecture tests, guardrails | 0.12 | 9.0 | 1.08 |
| Документация и ADR | Согласованность active docs, ADR и кода | 0.08 | 8.5 | 0.68 |
| Технический долг | Hotspots, duplication, broad assembly hubs, complexity | 0.09 | 6.0 | 0.54 |
| Расширяемость | Простота добавления providers/entities и безопасного изменения seams | 0.06 | 7.0 | 0.42 |

Итого: **7.16**

## Краткая интерпретация по 4 критериям

### 1. Соблюдение слоёв

Слои `domain / application / infrastructure / composition / interfaces`
в проекте реальны, а не декларативны. Импортные guardrails и architecture tests
подтверждают, что import matrix в целом соблюдается. Основной риск — не broad
layer violation, а graph fragility в отдельных composition/import seams.

### 2. Соответствие Ports & Adapters и DDD

Проект хорошо соответствует Hexagonal/DDD модели. Ports, adapters, composition
root, provider registries и domain contracts читаются последовательно. Слабое
место — compatibility layers, которые иногда размазывают границу между
canonical contract и transitional public surface.

### 3. Явность границ модулей и зависимостей

На уровне package topology система выглядит зрелой, но часть public facades и
assembly hubs остаются слишком широкими. Это не разрушает архитектуру, но
делает reasoning о зависимостях дороже, чем должен быть.

### 4. Единообразие нейминга, структуры пакетов и файлов

Первая naming wave уже сняла несколько сильных mismatches, но compatibility
aliases, helper/factory vocabulary split и часть derivative docs всё ещё
удерживают проект ниже хорошего уровня по семантической ясности.

## Ключевые проблемы

1. **CrossRef circular-import fragility**
   Основной архитектурный риск сейчас сидит не в import-matrix violation, а в
   циклической хрупкости вокруг CrossRef composition/import chain. Это import-time
   risk, который способен тормозить и runtime, и дальнейшие refactor waves.

2. **Governance leakage**
   Compatibility aliases и derivative docs продолжают поддерживать старую
   терминологию и размазывать canonical contract. Это особенно бьёт по
   discoverability, onboarding и decision traceability.

3. **Broad assembly hubs**
   Registry/factory/pipeline assembly still carries too much orchestration in a
   few large surfaces. Это повышает change fan-out и усложняет bounded changes.

4. **Duplicated fallback/retry semantics**
   Retry/fallback policy распределена по нескольким слоям и модулям. Это
   создаёт риск расхождения поведения и затрудняет audit/maintenance.

5. **Residual semantic ambiguity**
   First-wave naming cleanup помог, но объектные naming families, compatibility
   aliases и часть фасадов всё ещё дают лишнюю неоднозначность.

## Приоритизированный план рефакторинга

### RF-001. Убрать CrossRef import fragility

- Цель: сделать CrossRef bootstrapping import-safe и ацикличным.
- Конкретные правки:
  - сузить ответственность `crossref/__init__.py`;
  - отделить response-model seams от composition bootstrap;
  - убрать раннюю связность между composition entrypoints и adapter internals;
  - удержать wiring внутри composition без import-time side effects.
- Основные файлы:
  - `src/bioetl/composition/entrypoints.py`
  - `src/bioetl/composition/_pipeline_execution.py`
  - `src/bioetl/composition/factories/datasource/crossref.py`
  - `src/bioetl/infrastructure/adapters/crossref/__init__.py`
  - `src/bioetl/infrastructure/adapters/crossref/models.py`
  - `src/bioetl/infrastructure/adapters/crossref/_response_models.py`
- Риски:
  - поломка bootstrap/import paths;
  - скрытые transitive imports;
  - regressions в CLI/runtime entrypoints.
- Минимизация:
  - сначала добавить characterization tests;
  - выполнять перенос в 2 шага: import hygiene, затем wiring hygiene;
  - временные compatibility shims только при реальной необходимости.
- Definition of Done:
  - CrossRef composition path импортируется без circular import;
  - architecture/import tests зелёные;
  - runtime behavior не меняется.

### RF-002. Закрыть governance leakage вокруг canonical и compatibility surfaces

- Цель: жёстко отделить canonical surfaces от compatibility-only surfaces.
- Конкретные правки:
  - классифицировать aliases как `canonical`, `compatibility`, `deprecated`;
  - синхронизировать compatibility inventory, docs и exports;
  - вычистить legacy naming из derivative docs, где это создаёт ложное current-state impression.
- Основные файлы/зоны:
  - compatibility inventories в `configs/quality/`
  - active reference docs
  - generated/exported docs
  - фасады в `application/core` и related compatibility surfaces
- Риски:
  - случайно удалить нужный compatibility contract;
  - ухудшить discoverability.
- Минимизация:
  - менять aliases только вместе с inventory/docs/tests;
  - не удалять public alias без поиска imports и guardrail validation.
- Definition of Done:
  - canonical surfaces названы явно;
  - compatibility aliases ограничены и задокументированы;
  - derivative docs не маскируются под canonical truth.

### RF-003. Декомпозировать broad registry/factory/pipeline assembly hubs

- Цель: уменьшить change fan-out и улучшить локальную тестируемость.
- Конкретные правки:
  - разделить assembly flow на меньшие стадии;
  - выделить отдельные responsibilities для registry resolution, datasource assembly,
    transformer assembly, runner assembly;
  - удержать одну orchestration facade при более узких внутренних модулях.
- Основные файлы:
  - `src/bioetl/composition/factories/pipeline/assembler.py`
  - `src/bioetl/composition/factories/pipeline/runner.py`
  - `src/bioetl/composition/providers/provider_registry.py`
- Риски:
  - over-fragmentation;
  - потеря читаемости bootstrap order;
  - случайный reorder provider registration logic.
- Минимизация:
  - сохранять public entrypoints стабильными;
  - выносить только внутренние seams;
  - покрыть registration/runner behavior characterization tests.
- Definition of Done:
  - широкие hubs стали уже и понятнее;
  - onboarding нового provider/entity требует меньше touch points;
  - public behavior не изменился.

### RF-004. Консолидировать fallback/retry behavior

- Цель: убрать дублирование resilience logic и сделать policy audit-friendly.
- Конкретные правки:
  - разделить transport retry, publication fallback и provider-specific override;
  - выделить единый policy contract;
  - убрать near-duplicate fallback logic из provider transformers.
- Основные файлы:
  - `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py`
  - `src/bioetl/infrastructure/adapters/common/fallback_policy_mixin.py`
  - `src/bioetl/infrastructure/adapters/http/_client_retry_policy.py`
  - `src/bioetl/infrastructure/adapters/decorators/retry.py`
  - `src/bioetl/application/pipelines/common/base_publication_transformer.py`
- Риски:
  - незаметный behavioral drift на edge cases;
  - over-generalization общей policy.
- Минимизация:
  - golden-path и failure-path tests до/после;
  - provider-specific overrides оставлять там, где они реально нужны.
- Definition of Done:
  - fallback/retry semantics определены в одном месте;
  - адаптеры и transformers не дублируют policy code;
  - regression tests подтверждают отсутствие поведения drift.

### RF-005. Провести вторую naming/governance wave

- Цель: завершить semantic tightening без repo-wide rename campaign.
- Конкретные правки:
  - сузить object-family ambiguity;
  - привести helper/factory vocabulary к более явным canonical правилам;
  - не допускать роста compatibility-driven naming drift.
- Основные темы:
  - `Creator` vs `Factory`
  - `Support` vs `Helper`
  - `RunResult` families
  - helper/facade names, не соответствующие текущей роли
- Риски:
  - churn без достаточной пользы;
  - разбалансировка docs/imports.
- Минимизация:
  - только evidence-backed slices;
  - только рядом с реальным code touch;
  - не трогать compatibility names без выгоды для public clarity.
- Definition of Done:
  - canonical vocabulary читается стабильнее;
  - remaining ambiguity ограничена осознанными compatibility seams;
  - evidence и docs обновлены синхронно.

## Рекомендуемый порядок выполнения

1. `RF-001` — сначала снять import fragility.
2. `RF-002` — параллельно или сразу после `RF-001`, чтобы не тянуть stale governance.
3. `RF-003` — после стабилизации CrossRef/import graph.
4. `RF-004` — после сужения assembly hubs.
5. `RF-005` — последней bounded wave.

## Verify Matrix

| Волна | Обязательная верификация | Цель проверки |
|---|---|---|
| `RF-001` | `pytest tests/architecture/test_interfaces_no_infrastructure.py -q` | Подтвердить снятие circular-import fragility и отсутствие новой layer leakage |
| `RF-001` | `pytest tests/unit/composition -q` | Проверить composition wiring и bootstrap contracts |
| `RF-001` | `python -m mypy --strict src/bioetl/composition src/bioetl/infrastructure/adapters/crossref` | Удержать типовую целостность import-sensitive seams |
| `RF-002` | `pytest tests/architecture/test_compatibility_*.py -q` | Подтвердить согласованность canonical vs compatibility policy |
| `RF-002` | `python scripts/qa/generate_compatibility_facade_snapshot.py --check` | Проверить SSOT/generated snapshot consistency |
| `RF-002` | `python scripts/check_doc_links.py --configs` | Убедиться, что doc/governance cleanup не сломал active references |
| `RF-003` | `pytest tests/unit/composition -q` | Зафиксировать поведение registry/factory/runner после декомпозиции |
| `RF-003` | `pytest tests/architecture -q` | Проверить, что разбиение hubs не создало новых boundary regressions |
| `RF-004` | `pytest tests/unit/infrastructure -q` | Проверить fallback/retry behavior на уровне адаптеров |
| `RF-004` | `pytest tests/unit/application -q` | Подтвердить отсутствие drift в transformer/service behavior |
| `RF-005` | `pytest tests/unit -q` | Убедиться, что naming cleanup не сломал runtime contracts |
| `RF-005` | `ruff check src tests && ruff format --check src tests` | Удержать style/import hygiene после rename slices |

Базовый full-closeout bundle после каждой завершённой волны:

- `./.venv/Scripts/python.exe -m pytest tests/architecture -q`
- `./.venv/Scripts/python.exe -m mypy --strict src/bioetl/`
- `./.venv/Scripts/ruff.exe check src tests`
- `./.venv/Scripts/ruff.exe format --check src tests`

## Метрики и тесты контроля регрессий

| Категория | Контрольная метрика/тест | Ожидаемое улучшение |
|---|---|---|
| Соблюдение слоёв | `tests/architecture/test_layer_dependencies.py`, `test_forbidden_imports.py`, dependency map | 7.0 → 8.5 |
| Hexagonal и DDD | audit по facade/port contracts, ADR alignment | 8.0 → 8.5 |
| Границы модулей | cycle/import checks, import-safe composition entrypoints | 7.0 → 8.0 |
| DI и composition | constructor-injection review, no service-locator grep, composition tests | 8.0 → 8.5 |
| Нейминг | naming evidence refresh, grep on canonical vocabulary, facade review | 6.0 → 7.5 |
| Конфигурация и governance | inventory sync checks, generated-doc drift checks, SSOT consumers | 5.0 → 8.0 |
| Тестовая архитектура | architecture tests, provider smoke tests, regression suite | 9.0 → 9.0 |
| Документация и ADR | docs sync, architecture-doc refresh checks | 8.5 → 8.8 |
| Технический долг | hotspot counts, duplication scans, file-size and decomposition progress | 6.0 → 7.5 |
| Расширяемость | touch-count per provider onboarding, assembly fan-out, seam count | 7.0 → 8.0 |

## Прогнозируемый эффект

Если реализовать `RF-001..RF-004` без regressions, ожидаемый интегральный балл
проекта поднимется примерно до **8.27 / 10**.

Это переведёт проект в зону:

- **`8.0–10.0` — хорошее состояние, точечные улучшения**

## Рекомендуемый порядок коммитов

1. `RF-001a` — characterization/import-hygiene для CrossRef seams без изменения public behavior.
2. `RF-001b` — фактическое сужение CrossRef bootstrap/import graph.
3. `RF-002a` — compatibility inventory и canonical-surface alignment.
4. `RF-002b` — derivative/generated docs relabeling и cleanup.
5. `RF-003a` — разбиение registry/factory hubs на внутренние seams без смены фасадов.
6. `RF-003b` — дополнительное сужение assembly responsibilities, если после первой волны всё ещё есть hotspot pressure.
7. `RF-004` — fallback/retry consolidation после стабилизации composition shape.
8. `RF-005` — naming/governance second wave последними bounded slices.

Правило: один архитектурный мотив на commit. Не смешивать `RF-001` import fixes с `RF-002` doc/governance cleanup в одном changeset, даже если файлы формально пересекаются минимально.

## Practical Notes

- Этот план нужно читать как архитектурный refactor map, а не как замену
  [consolidated-open-tasks-plan-2026-03-21.md](./consolidated-open-tasks-plan-2026-03-21.md).
- Если текущий implementation priority остаётся на `config topology / ownership`
  и `shared adapter hotspots`, то `RF-001` и `RF-004` лучше всего ложатся в уже
  существующую открытую очередь, а `RF-002`, `RF-003`, `RF-005` могут служить
  следующими bounded waves.
