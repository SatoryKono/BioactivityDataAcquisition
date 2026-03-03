# Architecture Audit Report

Date: 2026-03-03
Scope: `src/bioetl`, `tests/architecture`, active docs (`docs/`, `.github/workflows`, `README.md`)

## Executive Summary

- Total findings: **6**
- Critical (P1 / MUST): **1**
- Moderate (P2 / SHOULD): **3**
- Informational (P3 / MAY): **2**
- Интегральный взвешенный балл: **7.15 / 10**

Проект демонстрирует зрелую архитектурную дисциплину (строгие архитектурные тесты, типизация `mypy --strict`, выраженная портовая модель), но имеет критичный разрыв в консистентности активной документации и заметный структурный риск в виде нескольких сверхкрупных модулей composition/application.

______________________________________________________________________

## Методика и верификация

### Выполненные команды

1. `uv run python -m pytest tests/architecture/ -q`
   - Результат: 1 failure (documentation sync), остальное pass/skip.
1. `uv run python -m mypy --strict src/bioetl/`
   - Результат: success (550 source files).
1. `uv run python -m pytest tests/architecture/test_antipatterns.py -q`
   - Результат: pass.
1. `uv run python -m pytest tests/architecture/test_performance.py -q`
   - Результат: pass.
1. Статический аудит границ/антипаттернов:
   - `rg -n "^from bioetl\.infrastructure|^import bioetl\.infrastructure" src/bioetl/application`
   - `rg -n "^from bioetl\.(infrastructure|application|composition|interfaces)|^import bioetl\.(infrastructure|application|composition|interfaces)" src/bioetl/domain`
   - `rg -n "\bprint\(" src/bioetl tests`
   - `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20`

______________________________________________________________________

## Оценка по 10 категориям

| Категория                                         | Описание                                                                |  Вес | Оценка (1–10) | Взвешенный балл |
| ------------------------------------------------- | ----------------------------------------------------------------------- | ---: | ------------: | --------------: |
| 1. Слоистая архитектура и границы зависимостей    | Насколько соблюдается import matrix и изоляция слоёв                    | 0.16 |           8.5 |            1.36 |
| 2. Hexagonal (Ports & Adapters) и DI              | Использование портов, инверсия зависимостей, композиция через factories | 0.14 |           8.0 |            1.12 |
| 3. DDD и качество доменной модели                 | Инварианты, aggregate roots, value objects, чистота домена              | 0.12 |           8.0 |            0.96 |
| 4. Модульность, связность, размер модулей         | Cohesion/complexity, отсутствие god modules                             | 0.10 |           5.5 |            0.55 |
| 5. Тестирование и архитектурные гейты             | Полнота архитектурных/unit/integration checks, сигнал регрессий         | 0.12 |           8.0 |            0.96 |
| 6. Типизация и контрактность                      | Строгость type system, стабильность публичных API                       | 0.10 |           9.0 |            0.90 |
| 7. Ошибки, отказоустойчивость и observability     | Ошибки домена, circuit breaker/rate limit, structured logging           | 0.08 |           7.5 |            0.60 |
| 8. Medallion/данные и storage-практики            | Соответствие Bronze/Silver/Gold policy, Delta в Silver                  | 0.08 |           8.5 |            0.68 |
| 9. Конфигурация, документация и единообразие имен | Консистентность идентификаторов/доков/конфигов                          | 0.06 |           4.5 |            0.27 |
| 10. Техдолг и сопровождаемость                    | Стоимость изменений, локальность правок, читабельность                  | 0.04 |           6.5 |            0.26 |

**Итоговый интегральный балл = 7.15 / 10**

### Интерпретация общего балла

- **0–4.9**: нестабильная архитектура
- **5–7.9**: рабочая, но с заметным техдолгом и рисками
- **8–10**: зрелая и масштабируемая архитектура

**Вывод:** текущее состояние — **верхняя граница среднего диапазона** (рабочая и дисциплинированная архитектура), но до «зрелой» недотягивает из-за документарных рассинхронизаций и крупных многозадачных модулей.

______________________________________________________________________

## Оценка архитектуры (Hexagonal + DDD + границы)

### 1) Соблюдение слоистой структуры

- Позитив: тесты явно проверяют изоляцию orchestration фреймворков в application, запуск метрик только в composition, импорт портов через фасад.
- Риск: один из архитектурных тестов на документацию падает, что указывает на несогласованность «активных» артефактов и текущих naming conventions.

### 2) Следование Ports & Adapters и DDD

- Позитив: `domain.ports` реализован как единый фасад с широким реэкспортом контрактов; видна доменная модель с aggregate roots и инвариантами.
- Риск: отдельные application/composition модули очень крупные и совмещают несколько видов orchestration/assembly-ответственности.

### 3) Явность границ модулей и зависимостей

- Позитив: архитектурные тесты детально формализуют forbidden imports и adapter isolation.
- Риск: крупные «центральные» файлы повышают риск скрытых transitive-зависимостей и усложняют безопасный рефакторинг.

### 4) Единообразие соглашений именования/структуры

- Позитив: проект активно контролирует naming через архитектурные тесты.
- Риск: merged-документация содержит legacy kebab-case pipeline IDs в активном дереве docs, что ломает policy.

______________________________________________________________________

## Findings

## [Critical (P1)] Active docs содержат legacy kebab-case pipeline IDs

**Location**: `tests/architecture/test_documentation_sync.py:242-288`, `docs/exports/full-documentation-no-plans-reports-skills.merged.md:45372,45480,46488,48017`
**Rule**: Naming consistency in active docs/workflows (MUST, архитектурный тест)

**Evidence**:

```python
# tests/architecture/test_documentation_sync.py
assert (
    not violations
), "Legacy kebab-case pipeline IDs found in active docs/workflows:\n" + "\n".join(
    f"  - {item}" for item in sorted(violations)
)
```

```text
# docs/exports/full-documentation-no-plans-reports-skills.merged.md
# Source: `04-reference/pipelines/chembl-activity.md`
# Source: `04-reference/pipelines/chembl-assay.md`
# Source: `04-reference/pipelines/openalex-publication.md`
# Source: `04-reference/pipelines/semanticscholar-publication.md`
```

**Impact**: архитектурный gate падает; повышается риск путаницы между legacy/new pipeline IDs в процессах сопровождения и CI.

**Recommendation**:

- Либо исключить экспортный merged-файл из active-scan (если это build artifact),
- либо нормализовать legacy source labels в merged output,
- либо переместить экспорт в `docs/99-archive` (если это архив).

**Verification command**: `uv run python -m pytest tests/architecture/test_documentation_sync.py::test_no_legacy_kebab_pipeline_ids_in_active_docs -q`

______________________________________________________________________

## [Moderate (P2)] Сверхкрупный модуль `MergeService` повышает риск god object

**Location**: `src/bioetl/application/composite/merger.py` (1850 LOC, 42 methods)
**Rule**: Maintainability / module cohesion (SHOULD)

**Evidence**:

- В `MergeService` сосредоточены чтение таблиц, дедупликация, агрегация, переименование, ordering, cross-validation orchestration.

**Impact**: изменения в одном аспекте с высокой вероятностью затрагивают другие; возрастает вероятность регрессий при доработках composite flow.

**Recommendation**:

- Выделить orchestrator + 4–6 специализированных сервисов (reader/join planner/conflict resolver/lineage mapper/schema enforcer).

**Verification command**: `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20`

______________________________________________________________________

## [Moderate (P2)] `pipeline_factory.py` смешивает слишком много обязанностей composition-слоя

**Location**: `src/bioetl/composition/factories/pipeline_factory.py:85-950`
**Rule**: Single responsibility in composition modules (SHOULD)

**Evidence**:

- В одном файле: `GenericPipelineFactory`, `build_pipeline_services`, `create_pipeline_with_services`, `assemble_runner`, DQ extraction helpers.

**Impact**: сложная навигация, высокий cognitive load, сложнее ревью/тестировать изменяемые зоны отдельно.

**Recommendation**:

- Разбить на пакеты: `pipeline_factory/` с `factory.py`, `services_assembly.py`, `runner_assembly.py`, `dq_context.py`.

**Verification command**: `rg -n "^def |^class " src/bioetl/composition/factories/pipeline_factory.py`

______________________________________________________________________

## [Moderate (P2)] Документарный экспорт смешивает текущую и legacy терминологию

**Location**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md`
**Rule**: Documentation consistency (SHOULD)

**Evidence**:

- В одном активном файле присутствуют current pipeline names (`chembl_activity`) и legacy source labels (`openalex-publication`, `semanticscholar-publication`).

**Impact**: «ложные» архитектурные нарушения и рост стоимости поддержки тестов синхронизации документации.

**Recommendation**:

- Ввести explicit metadata marker для legacy fragments (например, YAML front matter `legacy: true`) и учитывать его в тестах.

**Verification command**: `rg -n "openalex-publication|semanticscholar-publication|chembl-activity|chembl-assay" docs/exports/full-documentation-no-plans-reports-skills.merged.md`

______________________________________________________________________

## [Informational (P3)] Портовая фасадная модель реализована корректно

**Location**: `src/bioetl/domain/ports/__init__.py:1-120`, `tests/architecture/test_forbidden_imports.py:180-216`
**Rule**: REQ-ARCH-027

**Evidence**:

- Явный фасад `bioetl.domain.ports` + архитектурный тест, запрещающий импорт внутренних порт-модулей.

**Impact**: снижает coupling между слоями и стабилизирует публичный API портов.

**Recommendation**: сохранить policy и добавить smoke-check на backward compatibility `__all__`.

**Verification command**: `uv run python -m pytest tests/architecture/test_forbidden_imports.py::TestPortImportFacade::test_ports_imported_only_from_facade -q`

______________________________________________________________________

## [Informational (P3)] Типизация и storage policy находятся в хорошем состоянии

**Location**: `src/bioetl/infrastructure/storage/silver_writer.py:1-39`, `tests/architecture/test_performance.py`, `mypy strict run`
**Rule**: Silver=Delta (MUST), strict typing (MUST)

**Evidence**:

- Silver writer основан на Delta Lake (`deltalake`, `write_deltalake`).
- `mypy --strict` проходит на всём `src/bioetl`.

**Impact**: высокая предсказуемость контрактов и ниже риск runtime-дефектов на слое данных.

**Recommendation**: поддерживать строгий CI gate для mypy и architecture tests.

**Verification command**: `uv run python -m mypy --strict src/bioetl/`

______________________________________________________________________

## Приоритизированный план рефакторинга

### Шаг 1 (Critical): Нормализация активной документации и test policy

- **Цель**: восстановить зелёный архитектурный gate по doc naming.
- **Конкретные правки**:
  - Либо переместить `docs/exports/*.merged.md` в archive scope,
  - либо обновить генератор merged docs для underscore source IDs,
  - либо скорректировать `test_documentation_sync` (исключать экспортные агрегаты с `legacy: true`).
- **Риски**: потеря трассируемости legacy source names.
- **Минимизация риска**: хранить legacy ID в отдельном metadata-поле/appendix, не в «активном» контенте.
- **Критерии готово**:
  - `tests/architecture/test_documentation_sync.py::test_no_legacy_kebab_pipeline_ids_in_active_docs` = PASS,
  - наличие явной policy в docs generator/README.

### Шаг 2 (High): Декомпозиция `MergeService`

- **Цель**: снизить связность и упростить сопровождение composite merge.
- **Конкретные правки**:
  - Выделить интерфейсы/ABC: `SeedReaderPort`, `EnricherJoinPlannerPort`, `ConflictResolverPort`, `LineageComposerPort`, `CompositeSchemaEnforcerPort`.
  - Перенести реализацию в отдельные модули `application/composite/services/*`.
  - Оставить `MergeService` как thin orchestrator.
- **Риски**: subtle regression в merge semantics и lineage.
- **Минимизация риска**: snapshot regression tests на выходные таблицы + property-based tests для join key normalization.
- **Критерии готово**:
  - `merger.py` < 700 LOC,
  - покрытие ключевых merge-веток не ниже baseline,
  - zero diff на golden dataset.

### Шаг 3 (High): Разбиение `pipeline_factory.py` на подмодули assembly

- **Цель**: сделать composition root более читаемым и безопасным для расширения провайдеров.
- **Конкретные правки**:
  - `composition/factories/pipeline_factory/`:
    - `factory.py` (GenericPipelineFactory),
    - `services_assembly.py` (build_pipeline_services),
    - `runner_assembly.py` (assemble_runner),
    - `dq_context.py` (DQ extraction helpers).
- **Риски**: циклические импорты между сборочными helper-модулями.
- **Минимизация риска**: explicit interfaces + import-linter rule + incremental move.
- **Критерии готово**:
  - каждый модуль < 350 LOC,
  - публичный API backward-compatible (`__init__.py` re-export),
  - архитектурные тесты зелёные.

### Шаг 4 (Medium): Явная политика по legacy документам

- **Цель**: исключить повторные ложные срабатывания в документационных тестах.
- **Конкретные правки**:
  - Добавить taxonomy: `active docs` vs `generated export` vs `archive`.
  - Обновить тестовые фильтры и генератор документации.
- **Риски**: расхождение между tooling и policy.
- **Минимизация риска**: contract test на набор файлов-кандидатов (`test_documentation_sync` fixture).
- **Критерии готово**:
  - стабильный список сканируемых артефактов,
  - нулевые flaky failures по documentation sync.

### Шаг 5 (Medium): Улучшение тестируемости и локализация сложной логики

- **Цель**: повысить скорость безопасных изменений.
- **Конкретные правки**:
  - для выделенных сервисов внедрить unit tests с DI-моками,
  - добавить «контрактные» тесты для портов merge/services,
  - зафиксировать стандарт fixture naming для composite pipelines.
- **Риски**: рост времени CI.
- **Минимизация риска**: параллелизация и split-fast/slow test suites.
- **Критерии готово**:
  - ключевые refactor-зоны имеют targeted tests,
  - mean time to debug (по PR feedback) снижается.

______________________________________________________________________

## Рекомендованные метрики и контроль регресса

### Новые/обновлённые архитектурные метрики

1. **Layer Boundary Violations** (count)
   Источник: `tests/architecture/*import*`, forbidden imports.
1. **Largest Module LOC (P95 / max)**
   Источник: `wc -l` по `src/bioetl/**/*.py`.
1. **Complexity Hotspots** (functions with CC > threshold)
   Источник: `radon cc` (добавить в CI).
1. **Architecture Test Pass Rate**
   Источник: `pytest tests/architecture`.
1. **Doc Naming Consistency Violations**
   Источник: `test_documentation_sync`.
1. **Mypy Strict Error Count**
   Источник: `mypy --strict`.
1. **Composite Merge Golden-Diff Ratio**
   Источник: snapshot tests для composite output.
1. **PR Change Locality Index** (сколько слоёв затронуто одним RF)
   Источник: git diff analyzer.

### Привязка метрик к интегральному баллу

- После **Шага 1** ожидаемый прирост: `+0.3 .. +0.5` (категория 9, частично 5).
- После **Шага 2–3** ожидаемый прирост: `+0.7 .. +1.1` (категории 4 и 10, частично 2).
- После **Шага 4–5** ожидаемый прирост: `+0.2 .. +0.4` (категории 5 и 9).

**Прогноз**: при выполнении ключевых шагов планово достижим общий балл **8.4–8.9 / 10**.

______________________________________________________________________

## Verification Log (срез)

- `uv run python -m pytest tests/architecture/ -q` → **FAILED (1 test)**: legacy kebab IDs in active docs.
- `uv run python -m mypy --strict src/bioetl/` → **PASSED**.
- `uv run python -m pytest tests/architecture/test_antipatterns.py -q` → **PASSED**.
- `uv run python -m pytest tests/architecture/test_performance.py -q` → **PASSED**.
