# Architecture Audit Report — BioETL

Date: 2026-03-03
Scope: `src/bioetl`, `tests/architecture`, active docs/workflows

## Verification log (executed)

- `uv run python -m pytest tests/architecture/ -q`
- `uv run python -m mypy --strict src/bioetl/`
- `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20`
- `rg -n "^(from|import) (httpx|requests|aiohttp|structlog|logging)" src/bioetl/domain`
- `rg -n "\b(open|print)\(" src/bioetl/domain`
- `rg -n "^from bioetl\.infrastructure|^import bioetl\.infrastructure" src/bioetl/application`
- `rg -n "^from bioetl\.(application|infrastructure|composition|interfaces)|^import bioetl\.(application|infrastructure|composition|interfaces)" src/bioetl/domain`
- `rg -n "chembl-activity|chembl-assay|openalex-publication|semanticscholar-publication" docs/exports/full-documentation-no-plans-reports-skills.merged.md`

## Executive summary

- Архитектурный каркас в целом устойчив: есть формализованные архитектурные тесты, строгая типизация (`mypy --strict`), явные порты, DI и выраженная Medallion-политика.
- Основной архитектурный риск — **концентрация orchestration-логики в нескольких очень крупных модулях**, что снижает локальную изменяемость и увеличивает вероятность каскадных регрессий.
- Выявлено 1 фактическое регрессионное несоответствие в active docs: legacy kebab-case pipeline IDs в экспортированном документе `docs/exports/...` (падает архитектурный тест).

## 10-category scoring model

| Категория                                        | Что оценивается                                                                              |      Вес | Оценка (1–10) | Взвешенный балл |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------- | -------: | ------------: | --------------: |
| 1. Слоистая архитектура и границы зависимостей   | Соответствие domain/application/infrastructure/composition/interfaces и направлению импортов |     0.15 |           8.5 |           1.275 |
| 2. Hexagonal / Ports & Adapters                  | Полнота и консистентность портов, инверсия зависимостей, адаптеры                            |     0.12 |           8.5 |           1.020 |
| 3. Доменная модель и DDD-практики                | Чистота domain, value objects, агрегаты, отсутствие I/O в domain                             |     0.10 |           8.0 |           0.800 |
| 4. Модульность, связность, размер модулей        | Cohesion, отсутствие god objects, степень декомпозиции                                       |     0.12 |           6.0 |           0.720 |
| 5. Типобезопасность и контрактность              | Strict typing, ясность API, минимизация `Any`                                                |     0.10 |           8.0 |           0.800 |
| 6. Тестовая стратегия и архитектурные guardrails | Покрытие уровнями, архитектурные тесты, устойчивость CI-правил                               |     0.11 |           8.0 |           0.880 |
| 7. Обработка ошибок и resilience                 | Circuit breaker, retry policy, error contracts                                               |     0.08 |           8.0 |           0.640 |
| 8. Observability и логирование                   | Структурированное логирование, run_id traceability, метрики                                  |     0.07 |           8.0 |           0.560 |
| 9. Data architecture (Medallion/Delta/DQ)        | Bronze/Silver/Gold политика, Delta в Silver, DQ-пороги                                       |     0.10 |           8.5 |           0.850 |
| 10. Техдолг, документация и сопровождаемость     | Актуальность docs, управляемость изменений, dev ergonomics                                   |     0.05 |           6.5 |           0.325 |
| **Итого**                                        |                                                                                              | **1.00** |               |   **7.87 / 10** |

### Интерпретация интегрального балла

- **0–4.9**: критическое состояние, масштабный redesign.
- **5.0–7.9**: рабочая архитектура с заметным техдолгом и локальными рисками.
- **8.0–10**: зрелая архитектура, точечные улучшения.

**Текущий результат: 7.87** → верхняя граница «рабочая архитектура с заметным техдолгом».

## Оценка текущей архитектуры по requested axes

### 1) Соблюдение слоистой структуры

- Позитивно: архитектурные тесты явно проверяют запрет инфраструктурных и application-импортов в domain (`test_layer_dependencies.py`).
- Позитивно: прямые проверки импортов не обнаружили `application -> infrastructure` и `domain -> non-domain` импортов командами `rg`.
- Вывод: слойность **в основном соблюдается**.

### 2) Ports & Adapters (Hexagonal) и DDD

- Позитивно: `bioetl.domain.ports.__init__` является фасадом для портов и NoOp-реализаций, что поддерживает DI и контрактность.
- Позитивно: `SilverWriter` реализует Delta-подход и зависит от портов (`LoggerPort`, `MetricsPort`, `AuditPort` и др.), а не от application-сервисов.
- Вывод: Hexagonal-подход **реализован последовательно**, особенно в storage/observability контрактах.

### 3) Явность границ модулей и зависимостей

- Позитивно: есть большой набор архитектурных тестов (`tests/architecture`, 74 файла).
- Риск: отдельные ключевые модули остаются крупными (например, `application/composite/merger.py`, `application/composite/runner.py`, `composition/factories/pipeline_factory.py`, `infrastructure/storage/silver_writer.py`), что повышает когнитивную связанность.

### 4) Единообразие naming/package conventions

- Позитивно: имена портов и сервисов в целом следуют соглашениям (`*Port`, `*Service`, `*Factory`).
- Регрессия: тест документации фиксирует legacy kebab-case pipeline IDs в активном экспортном документе.

## Key findings

### [Critical/P1] Невоспроизводимость «зелёного» архитектурного гейта в текущем состоянии

**Location**: `tests/architecture/test_documentation_sync.py:242-288`, `docs/exports/full-documentation-no-plans-reports-skills.merged.md:45372,45480,46488,48017,62789`

**Evidence**:

- Падает `test_no_legacy_kebab_pipeline_ids_in_active_docs`.
- В active docs найдено: `chembl-activity`, `chembl-assay`, `openalex-publication`, `semanticscholar-publication`.

**Impact**:

- Нарушается архитектурный quality gate в CI; снижается доверие к документации как source-of-truth.

**Recommendation**:

1. Либо исключить `docs/exports/*.merged.md` из active-doc scan как generated artifact,
1. Либо нормализовать ID в генераторе экспортного документа,
1. Либо хранить экспорт в `docs/99-archive/` (уже исключается из проверки).

**Verification command**: `uv run python -m pytest tests/architecture/test_documentation_sync.py::test_no_legacy_kebab_pipeline_ids_in_active_docs -q`

______________________________________________________________________

### [Moderate/P2] Высокая концентрация orchestration-логики в крупных классах/модулях

**Location**: `src/bioetl/application/composite/merger.py` (~1850 LOC), `src/bioetl/application/composite/runner.py` (~1143 LOC), `src/bioetl/composition/factories/pipeline_factory.py` (~986 LOC), `src/bioetl/infrastructure/storage/silver_writer.py` (~1230 LOC)

**Evidence**:

- `merger.py`: 1 класс, ~43 методов.
- `runner.py`: 2 класса, ~24 методов.
- В `pipeline_factory.py` в одном модуле совмещены factory class + runner assembly + service wiring + data source construction.

**Impact**:

- Удорожание изменений, риск регрессий при расширении composite-pipeline сценариев, сложность targeted-тестирования.

**Recommendation**:

- Декомпозировать по сценариям ответственности (MergePlan, JoinExecutor, ConflictResolver, ColumnPolicy, RunnerStateMachine, RunnerLifecycleHooks, PipelineAssemblySteps).

**Verification command**:

- `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20`
- `rg -n '^\s+def |^\s+async def ' src/bioetl/application/composite/merger.py`

______________________________________________________________________

### [Moderate/P2] Стоимость поддержки strict typing повышена из-за высокой плотности `Any`

**Location**: преимущественно composition/infra и ports signatures (aggregate count)

**Evidence**:

- `rg -n "\bAny\b" src/bioetl | wc -l` => 1633 вхождения.
- При этом `mypy --strict` проходит, значит часть `Any` оправдана (например Pandera schema placeholders), но их объём уже риск для долгосрочной contract safety.

**Impact**:

- Снижение эффективности type-driven refactoring, рост вероятности рантайм-ошибок при изменениях API.

**Recommendation**:

- Ввести лимиты/бюджеты на `Any` по слоям и заменить на Protocol/TypeAlias/TypedDict для наиболее критичных путей.

**Verification command**: `uv run python -m mypy --strict src/bioetl/ && rg -n "\bAny\b" src/bioetl | wc -l`

## Refactoring plan (prioritized)

### RF-001 (P1): Stabilize architecture docs gate

- **Цель**: вернуть 100% pass архитектурного CI-гейта по документации.
- **Правки**:
  - Обновить `tests/architecture/test_documentation_sync.py` (исключение generated exports) **или** pipeline генерации `docs/exports/*` для underscore IDs.
  - Перегенерировать `docs/exports/full-documentation-no-plans-reports-skills.merged.md`.
- **Риски**: можно случайно ослабить guardrail.
- **Снижение риска**: добавить отдельный тест на корректность генератора экспортов.
- **DoD**:
  - `uv run python -m pytest tests/architecture/test_documentation_sync.py -q` зелёный.
  - В active docs нет legacy kebab-case IDs.

### RF-002 (P1): Decompose `MergeService` into composable strategy modules

- **Цель**: устранить god-object риск в composite merge.
- **Правки**:
  - Выделить из `application/composite/merger.py`:
    - `merge_plan_builder.py`
    - `join_executor.py`
    - `conflict_resolver.py`
    - `lineage_enricher.py`
    - `column_policy_service.py`
  - Оставить `MergeService` фасадом orchestration.
- **Риски**: изменение порядка merge-операций и subtle поведение в column precedence.
- **Снижение риска**:
  - Golden-master tests для merge output на наборе composite fixtures.
  - Контрактные тесты для каждого MergeStrategy.
- **DoD**:
  - `merger.py` < 500 LOC.
  - Не падают существующие `tests/unit/application/composite/*` и `tests/architecture/*`.

### RF-003 (P1): Split `CompositePipelineRunner` lifecycle orchestration

- **Цель**: повысить тестируемость и прозрачность FSM/lifecycle.
- **Правки**:
  - Вынести этапы run lifecycle в отдельные application-сервисы:
    - `seed_stage_service.py`
    - `dependency_stage_service.py`
    - `enrichment_stage_service.py`
    - `merge_stage_service.py`
    - `finalization_stage_service.py`
  - Runner оставить coordinator-level классом.
- **Риски**: race conditions/lock lifecycle regressions.
- **Снижение риска**:
  - Добавить stage-level integration tests с checkpoint resume.
  - Проверка lock heartbeat/release на happy-path и error-path.
- **DoD**:
  - Цикл `run()` читается как linear pipeline из stage-вызовов.
  - У stage сервисов отдельные unit-тесты и фикстуры.

### RF-004 (P2): Modularize composition factory assembly

- **Цель**: снизить связанность composition root и упростить DI-вариативность.
- **Правки**:
  - Разделить `pipeline_factory.py` на:
    - `pipeline_factory_core.py`
    - `pipeline_services_builder.py`
    - `runner_assembler.py`
    - `cached_bronze_source_factory.py`
  - Ввести явные dataclass-конфиги для assembly options.
- **Риски**: circular imports в composition.
- **Снижение риска**: архитектурный тест на import graph в composition subtree.
- **DoD**:
  - Нет cyclic dependencies в composition.
  - Сохранён публичный API через re-export backward shim.

### RF-005 (P2): Introduce type-hardening campaign (`Any` budget)

- **Цель**: уменьшить surface area нестрогой типизации.
- **Правки**:
  - Добавить `TypeAlias`/`Protocol` для schema-like абстракций.
  - `Any` в public signatures заменять на bounded generic/Protocol.
  - Ввести архитектурный тест: «новые `Any` запрещены без комментария-обоснования».
- **Риски**: рост времени разработки на начальном этапе.
- **Снижение риска**: делать по 2–3 критичных модуля за итерацию.
- **DoD**:
  - Снижение общего числа `Any` минимум на 25%.
  - `mypy --strict` остаётся зелёным.

### RF-006 (P2): Strengthen config-vs-business logic separation

- **Цель**: исключить смешение policy/config трансформаций с runtime orchestration.
- **Правки**:
  - Вынести policy-derivation logic в domain/application policy services.
  - Оставить composition только за wiring.
- **Риски**: дублирование fallback-логики при миграции.
- **Снижение риска**: временный compatibility adapter + deprecation plan.
- **DoD**:
  - В composition нет бизнес-ветвлений по run semantics (кроме wiring decisions).

### RF-007 (P3): Documentation governance hardening

- **Цель**: синхронизировать generated docs и архитектурные tests.
- **Правки**:
  - Явно маркировать generated docs; хранить их в «неактивной» зоне или обновить policy-скан.
  - Добавить pre-commit check по pipeline ID convention.
- **Риски**: конфликт требований разных doc pipelines.
- **Снижение риска**: единый source-of-truth mapping legacy→underscore.
- **DoD**:
  - Документационный CI стабилен, нет ложноположительных падений.

## Suggested metrics & tests to prevent regressions

### New/updated metrics

1. **Layer Boundary Compliance Rate** = pass% tests `test_layer_dependencies`, `test_forbidden_imports`, `test_domain_purity`.
1. **Module Size Risk Index** = доля файлов > 700 LOC и > 20 методов на класс.
1. **Type Strictness Index** = (total public signatures - signatures with `Any`) / total public signatures.
1. **Architecture Test Stability** = pass rate `tests/architecture` по 14-дневному окну.
1. **Composite Maintainability Index** = cyclomatic + LOC по `application/composite/*`.
1. **Docs Consistency Index** = доля active-doc тестов без sync violations.
1. **DQ Policy Compliance** = присутствие soft/hard thresholds и их использование в runtime.
1. **Resilience Policy Compliance** = circuit breaker settings adherence (5 failures / 300s open / half-open probe).

### Mapping metrics to 10-category integral score

- После RF-001/007 ожидается рост категорий 6 и 10: +0.3…+0.5 суммарно.
- После RF-002/003/004 ожидается рост категории 4 и частично 1/2: +0.6…+0.9.
- После RF-005 ожидается рост категории 5: +0.4…+0.7.

**Projected integral score after key steps (RF-001..RF-005): ~8.4–8.8 / 10**
(переход в зрелую зону «8–10»).
