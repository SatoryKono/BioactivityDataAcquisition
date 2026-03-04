# Architecture Audit Report

Date: 2026-03-04
Scope: `src/bioetl`, `tests/architecture`, `configs/quality`, проектные правила в `docs/00-project/*`.

## Executive Summary

- Total findings: 6
- Critical (MUST): 0
- Moderate (SHOULD): 4
- Informational (MAY): 2
- Архитектурные guardrails сильные: `tests/architecture` проходят полностью (1439 passed, 21 skipped).
- Главный ограничитель развития — накопленный управляемый техдолг в метриках структуры (485 exemption entries в scorecard baseline).

## 10-category scorecard

| Категория                                             | Что оценивается                                                               |  Вес | Оценка (1–10) | Взвешенный балл |
| ----------------------------------------------------- | ----------------------------------------------------------------------------- | ---: | ------------: | --------------: |
| 1. Слоистая архитектура                               | Чистота зависимостей domain/application/infrastructure/interfaces/composition | 0.14 |           8.8 |            1.23 |
| 2. Hexagonal (Ports & Adapters) + DDD                 | Порты в domain, адаптеры в infrastructure, DI и инверсия зависимостей         | 0.12 |           8.3 |            1.00 |
| 3. Модульность и связность                            | Размер модулей, уровни связности, наличие god-object рисков                   | 0.11 |           6.4 |            0.70 |
| 4. Качество доменной модели                           | Чистота domain, выраженность value objects / contracts / invariants           | 0.10 |           7.4 |            0.74 |
| 5. Тестирование и архитектурные гейты                 | Полнота unit/integration/e2e/architecture, стабильность quality-gates         | 0.11 |           9.2 |            1.01 |
| 6. Обработка ошибок и устойчивость                    | Circuit breaker, retries, degradation patterns, fail-fast политика            | 0.08 |           7.8 |            0.62 |
| 7. Логирование и наблюдаемость                        | Структурированные логи, trace/metrics порты, run-context observability        | 0.08 |           8.4 |            0.67 |
| 8. Производительность и масштабируемость              | Асинхронность, батчинг, память/чекпоинты/производительность пайплайнов        | 0.08 |           7.2 |            0.58 |
| 9. Безопасность и секреты                             | Работа с credential/env vars, PII hashing, sanitization                       | 0.08 |           8.1 |            0.65 |
| 10. Документация, технический долг и сопровождаемость | Актуальность docs, явность правил, debt budgets/exemptions                    | 0.10 |           6.1 |            0.61 |

**Интегральный балл**: **7.81 / 10**

### Интерпретация

- **0–4.9**: критическое состояние
- **5.0–7.9**: рабочее, но ограниченное техдолгом
- **8.0–10**: зрелая архитектура

Текущее состояние: **верхняя граница “5.0–7.9”** — архитектура дисциплинированная и активно защищена тестами, но общий балл сдерживается размером и сложностью части модулей и большим количеством оформленных исключений из quality-метрик.

______________________________________________________________________

## Архитектурная оценка по запросу

### 1) Соблюдение слоистой структуры

- Позитив: в `tests/architecture/test_layer_dependencies.py` зафиксированы запреты на infra/imports в domain и на импорты concrete-adapters в application.
- Позитив: `tests/architecture` green (1439 passed).
- Вывод: критичных нарушений слоёв в текущем baseline не обнаружено.

### 2) Следование Ports & Adapters и DDD

- Позитив: фасад портов централизован в `src/bioetl/domain/ports/__init__.py`.
- Позитив: архитектурные тесты отдельно валидируют контракты портов/адаптеров (`test_port_contracts.py`, `test_adapter_contracts.py`).
- Риск: размер composition/application модулей усложняет безопасную эволюцию адаптеров и use-case orchestration.

### 3) Явность границ модулей и зависимостей

- Позитив: формализованная import discipline + CI-гейты.
- Риск: high fan-in/fan-out в крупных factory/transformer/config модулях (см. findings P2 ниже).

### 4) Единообразие naming и структуры пакетов

- Позитив: naming проверяется архитектурными тестами (`test_naming_conventions.py`), явная пакетная сегрегация слоёв.
- Риск: часть модулей содержит “технически валидную”, но перегруженную ответственность (configuration + orchestration + helper logic в одном файле).

______________________________________________________________________

## Findings

## [Moderate (P2)] F-001: Большой объём архитектурных exemption снижает реальную скорость улучшений

**Location**: `configs/quality/debt_scorecard.yaml`, `configs/quality/architecture_metric_exemptions.yaml`

**Rule**: SHOULD — управляемое сокращение техдолга по квартальным бюджетам.

**Evidence**:

- baseline фиксирует **485** total exemptions.
- распределение по registry: file_size_limits/function_complexity/function_length/class_size/god_object/domain_complexity.
- значительная доля с единым горизонтом истечения (2026-04-30), что формирует «долговой cliff».

**Impact**:

- затруднён приоритет реального рефакторинга;
- локальные изменения имеют повышенный риск hidden coupling;
- интегральный балл архитектуры искусственно ограничен.

**Recommendation**:

- Ввести wave-based debt burn-down (по 3–5 hotspot модулей/спринт);
- отделить обязательные от условных exemption с owner-level SLA;
- метрика успеха: -20% exemptions за 2 квартала.

**Verification command**: `uv run python - <<'PY' ... parse YAML ... PY`

## [Moderate (P2)] F-002: Крупные composition/application/domain модули создают локальные “god object” зоны

**Location**:

- `src/bioetl/composition/factories/pipeline_factory.py` (789 LOC)
- `src/bioetl/application/core/base_transformer.py` (622 LOC)
- `src/bioetl/domain/composite/config.py` (1152 LOC)
- `src/bioetl/composition/factories/storage_adapter.py` (734 LOC)

**Rule**: SHOULD — высокая связность и низкая когнитивная нагрузка модулей.

**Evidence**:

- `wc -l` подтверждает размеры выше типовых limits слоёв;
- архитектурный реестр exemption содержит отдельные записи для file_size/god_object/function_length.

**Impact**:

- рост стоимости изменения;
- сложность точечных unit-тестов;
- повышенный риск регрессий при расширении pipeline-сценариев.

**Recommendation**:

- выделить sub-factories/sub-services, перенести pure-функции в отдельные helper modules;
- ввести композицию через Protocol/ABC на уровне orchestration steps.

**Verification command**: `wc -l ... && grep -c ...`

## [Moderate (P2)] F-003: Тест quality-gate допускает высокий baseline long-functions

**Location**: `tests/architecture/test_code_metrics.py`

**Rule**: SHOULD — снижать допуски на длину функций по плану.

**Evidence**:

- `MAX_VIOLATIONS = 165` для функций >50 строк;
- комментарии в тесте отражают рост baseline и расширение допусков.

**Impact**:

- green build не гарантирует реального улучшения readability;
- long functions закрепляются как “новая норма”.

**Recommendation**:

- переводить budget в ratchet-модель (например, 165 -> 145 -> 120 по кварталам);
- добавить threshold на “new violations == 0” + “total decreases each quarter”.

**Verification command**: `sed -n '1,220p' tests/architecture/test_code_metrics.py`

## [Moderate (P2)] F-004: Частичное смешение orchestration и инфраструктурных деталей в крупных factory модулях

**Location**: `src/bioetl/composition/factories/pipeline_factory.py`

**Rule**: SHOULD — composition слой собирает зависимости, но не должен концентрировать чрезмерно много runtime-вариативности в одном модуле.

**Evidence**:

- модуль содержит большое число импортов из application/composition/domain/infrastructure;
- единая точка с множеством обязанностей: assembly, config extraction, runner wiring.

**Impact**:

- модуль становится изменяемым по многим причинам (SRP pressure);
- повышается риск конфликтов при параллельной разработке.

**Recommendation**:

- разрезать на bounded factory units (runner_assembly, dq_assembly, source_assembly, versioning_assembly);
- оставить в `pipeline_factory.py` только façade orchestration.

**Verification command**: `rg -n "^from |^import " src/bioetl/composition/factories/pipeline_factory.py`

## [Informational (P3)] F-005: Сильная архитектурная автоматизация — важный актив проекта

**Location**: `tests/architecture/*`

**Evidence**:

- 1460 архитектурных тестов, 1439 passed, 21 skipped;
- покрываются границы слоёв, naming, medallion invariants, observability ограничения, policy contracts.

**Impact**:

- снижает вероятность грубых архитектурных регрессов;
- упрощает безопасный инкрементальный рефакторинг.

## [Informational (P3)] F-006: Типобезопасность поддерживается на высоком уровне

**Location**: `src/bioetl/*`

**Evidence**:

- `uv run python -m mypy --strict src/bioetl/` -> Success (606 source files).

**Impact**:

- хороший фундамент для безопасного рефакторинга и выделения интерфейсов.

______________________________________________________________________

## Приоритизированный план рефакторинга

### P0 / Шаг 1 — Декомпозиция hotspot-модулей (первый wave)

**Цель**: снизить когнитивную сложность и размер критических файлов.

**Конкретные правки**:

- `pipeline_factory.py`: выделить `runner_assembler.py`, `dq_assembler.py`, `source_assembler.py`.
- `base_transformer.py`: вынести независимые этапы (column normalization, schema harmonization, quality hooks) в strategy-пакет.
- `domain/composite/config.py`: разделить на `seed_config.py`, `dependency_config.py`, `enricher_config.py`, `execution_policy.py` с re-export в фасаде.

**Риски**:

- поломка импортов и сериализации конфигов;
- поведение “тихо поменялось” из-за изменения порядка шагов.

**Снижение рисков**:

- contract tests на публичные dataclass/Protocol интерфейсы;
- golden snapshot тесты конфигураций;
- временный compatibility shim через `__init__.py` re-export.

**Критерии готово**:

- -15% LOC в каждом hotspot;
- 0 новых exemption;
- architecture + mypy green.

### P0 / Шаг 2 — Debt scorecard ratchet

**Цель**: перевести quality-gate из “держим baseline” в “обязательное снижение”.

**Конкретные правки**:

- `configs/quality/debt_scorecard.yaml`: целевые budgets на Q2/Q3 с минимум -8..10% по size_shape registries.
- `tests/architecture/test_code_metrics.py`: зафиксировать “new long-functions = 0”, уменьшить `MAX_VIOLATIONS` поэтапно.

**Риски**:

- рост красных CI в коротком горизонте.

**Снижение рисков**:

- staged rollout: warning->block только после 1 спринта стабилизации;
- исключения только с RF-id + expires_on.

**Критерии готово**:

- baseline exemptions \<= 440;
- автоматический отчёт debt trend в CI artifacts.

### P1 / Шаг 3 — Явные интерфейсы orchestration steps

**Цель**: снизить связность между orchestration компонентами и implementation деталями.

**Конкретные правки**:

- В application/composition ввести `Protocol` для шагов: preflight, extract, transform, load, postrun.
- Унифицировать фабрики шагов через typed factories (`*Factory`) без runtime ветвления в одном модуле.

**Риски**:

- дублирование интерфейсов или слишком “тонкие” абстракции.

**Снижение рисков**:

- ADR-lite (короткое решение) на границы каждого нового Protocol;
- ограничить стартовый scope 2-3 pipeline family.

**Критерии готово**:

- уменьшение import fan-out в `pipeline_factory.py` минимум на 30%;
- unit tests на каждый step port.

### P1 / Шаг 4 — Консолидация общей логики адаптеров

**Цель**: уменьшить дубли в fetch/search/health/request-sanitization.

**Конкретные правки**:

- Вынести общие request building blocks в `infrastructure/adapters/common` (already present, расширить использование).
- Для PubMed/OpenAlex/SemanticScholar унифицировать retry/backoff/circuit integration в mixin/service слой.

**Риски**:

- provider-specific edge cases могут “размыться”.

**Снижение рисков**:

- provider-contract tests + VCR кассеты per provider;
- feature flags на rollout общей логики.

**Критерии готово**:

- сокращение дублирующегося кода по target adapters (проверка через duplication scan);
- стабильный integration test baseline.

### P2 / Шаг 5 — Документация и architecture decision hygiene

**Цель**: удержать прозрачность эволюции архитектуры.

**Конкретные правки**:

- добавить “Refactoring Wave Board” в docs с RF-id, owners, deadlines;
- обновить runbook по рефакторингу крупных модулей и правилам внесения exemption.

**Риски**:

- документация устаревает быстрее кода.

**Снижение рисков**:

- CI check на синхронизацию версии правил и scorecard targets.

**Критерии готово**:

- все активные exemption имеют owner + expiry + removal_step;
- отчёт волны рефакторинга публикуется в каждом релизном цикле.

______________________________________________________________________

## Какие метрики и тесты добавить/обновить

1. **Architecture Fitness KPIs (обязательные)**

   - `exemptions_total` (цель: устойчивое снижение QoQ)
   - `hotspot_files_over_limit` (цель: снижение count)
   - `import_fanout_hotspots` (цель: снижение top-10)
   - `new_long_function_violations` (цель: всегда 0)

1. **Новые/обновлённые тесты**

   - test that **new exemptions forbidden** without RF-id и expiry;
   - ratchet test: квартальный budget must be \<= previous quarter;
   - fan-in/fan-out budget tests для composition hotspots;
   - mutation/snapshot tests для composite config decomposition.

1. **Связка с интегральным баллом (прогноз)**

   - После Шагов 1–2:
     - Категория 3 (модульность): 6.4 -> 7.6
     - Категория 10 (долг/сопровождаемость): 6.1 -> 7.2
     - Категория 8 (масштабируемость): 7.2 -> 7.8
   - Прогноз интегрального балла: **7.81 -> ~8.35**

______________________________________________________________________

## Verification Log (commands)

- `uv run python -m pytest tests/architecture/ -v`
- `uv run python -m mypy --strict src/bioetl/`
- `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -25`
- `uv run python - <<'PY' ... architecture_metric_exemptions stats ... PY`
- `wc -l src/bioetl/composition/factories/pipeline_factory.py src/bioetl/application/core/base_transformer.py src/bioetl/domain/composite/config.py src/bioetl/composition/factories/storage_adapter.py`
- `grep -c "^def \|^async def \|^class " ...`
- `rg -n "^from |^import " src/bioetl/composition/factories/pipeline_factory.py | head -40`
- `sed -n '1,220p' tests/architecture/test_code_metrics.py`
