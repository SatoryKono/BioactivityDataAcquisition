# Architecture Audit Report

Date: 2026-03-04
Scope: `src/bioetl`, `tests/architecture`, `configs/quality`, project governance docs

## Executive Summary

- Total findings: 7
- Critical (P1 / MUST): 0
- Moderate (P2 / SHOULD): 5
- Informational (P3 / MAY): 2
- Integral architecture score: **7.51 / 10**

Проект демонстрирует высокий уровень дисциплины по базовым архитектурным ограничениям (границы слоёв, типизация, архитектурные quality-gates), но имеет выраженный структурный технический долг по размеру/сложности модулей и количеству исключений в метриках качества.

______________________________________________________________________

## Verification Log (commands)

1. `uv run python -m pytest tests/architecture/ -q`
1. `uv run python -m mypy --strict src/bioetl/`
1. `rg --files -g 'AGENTS.md'`
1. `rg --files src/bioetl | head -120`
1. `find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20`
1. `rg -n "\bprint\(" src/bioetl | head -50`
1. `rg -n "httpx|requests|structlog|open\(" src/bioetl/domain | head -80`
1. Просмотр ключевых файлов: `tests/architecture/*.py`, `src/bioetl/domain/ports/__init__.py`, `src/bioetl/composition/factories/pipeline_factory.py`, `src/bioetl/interfaces/observability.py`, `configs/quality/*.yaml`.

______________________________________________________________________

## 10 ключевых категорий оценки

| Категория                                     | Описание                                                                                                  |  Вес | Оценка (1–10) | Взвешенный балл |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---: | ------------: | --------------: |
| 1. Слоистая архитектура и границы             | Соблюдение границ domain/application/infrastructure/composition/interfaces и направленности зависимостей. | 0.15 |           8.8 |            1.32 |
| 2. Hexagonal (Ports & Adapters) и DDD-подход  | Наличие портов в domain, инверсия зависимостей, отделение бизнес-логики от адаптеров.                     | 0.13 |           8.4 |            1.09 |
| 3. Модульность, связность, декомпозиция       | Размеры файлов/классов, признаки god object, локализация ответственности.                                 | 0.12 |           6.1 |            0.73 |
| 4. Типобезопасность и контрактность           | Полнота аннотаций, strict mypy, контрактные тесты и API-фасады.                                           | 0.10 |           9.1 |            0.91 |
| 5. Тестовое покрытие архитектурных правил     | Наличие автоматизированных архитектурных тестов и гейтов.                                                 | 0.10 |           8.7 |            0.87 |
| 6. Обработка ошибок и устойчивость            | Единообразие ошибок, resilience-подсистема (CB/rate limit), предсказуемость поведения.                    | 0.09 |           7.4 |            0.67 |
| 7. Логирование и наблюдаемость                | Структурированное логирование, метрики/трейсинг, эксплуатационные контракты.                              | 0.08 |           7.8 |            0.62 |
| 8. Конфигурация и DI-дисциплина               | Централизация конфигурации, dependency injection, отсутствие service locator-подхода.                     | 0.08 |           7.6 |            0.61 |
| 9. Документация и архитектурная управляемость | Наличие правил, ADR/гайдов, соответствие кода документации.                                               | 0.07 |           8.3 |            0.58 |
| 10. Техдолг и сопровождаемость                | Объём исключений, «долговых» реестров, масштаб усилий на изменения.                                       | 0.08 |           5.1 |            0.41 |

**Итоговый интегральный балл:** **7.51 / 10** (сумма взвешенных баллов).

### Интерпретация балла

- **0–4.9**: архитектурный кризис, развитие рискованно.
- **5–7.9**: рабочее, но ограниченное состояние — развитие возможно, однако техдолг заметно влияет на скорость и риски.
- **8–10**: зрелая архитектура, устойчивое масштабирование.

Текущее состояние: **верхняя граница среднего диапазона (5–7.9)** — архитектура управляемая и дисциплинированная, но масштаб технического долга уже тормозит расширяемость.

______________________________________________________________________

## Оценка архитектуры по заявленным аспектам

### 1) Соблюдение слоистой структуры

- Архитектурные тесты по зависимостям и запретам импортов присутствуют и проходят. Это сильный индикатор того, что явные P1-нарушения границ в текущем срезе отсутствуют.
- При этом часть тестов помечена `skip`, включая legacy bootstrap-кейс — это снижает полноту контроля на «краевых» участках.

### 2) Ports & Adapters (Hexagonal) и DDD

- Порты централизованы в `domain.ports` фасаде, есть контрактные тесты и проверки публичного API.
- В слое composition реализована фабричная сборка и orchestration зависимостей; это соответствует DI и Hexagonal intent.
- Ослабляющий фактор: перегруженные composition-модули с большим объёмом условной логики затрудняют ясное разграничение assembly vs orchestration.

### 3) Явность границ модулей и зависимостей

- Границы формализованы тестами (layer dependencies, import boundaries, medallion invariants).
- В то же время масштаб исключений в quality-реестрах и большие файлы создают «скрытую связанность»: формально границы соблюдены, фактически изменяемость дорогая.

### 4) Единообразие naming/структуры пакетов

- В проекте есть специализированные архитектурные тесты на naming conventions.
- Базовая структура каталогов чётко выражает Hexagonal + Medallion.
- Накопленный «legacy surface» (exemptions + пропуски отдельных проверок) требует дальнейшей нормализации.

______________________________________________________________________

## Основные проблемы

### [P2] Большой объём архитектурных исключений (technical debt budget at ceiling)

**Location**: `configs/quality/debt_scorecard.yaml`, `configs/quality/architecture_metric_exemptions.yaml`
**Evidence**: baseline `total_exemptions: 485` и множество активных exemption-записей c expiry окнами.
**Impact**: рост стоимости изменений, риск латентных регрессий, «размытие» quality-gates.
**Recommendation**: запустить квартальную программу по сжиганию exemptions с KPI на каждую группу реестров.

### [P2] Перегруженные файлы в composition/infrastructure/domain

**Location**: результаты `wc -l` (например, `pipeline_factory.py`, `storage_adapter.py`, крупные adapter/config модули).
**Evidence**: многочисленные файлы существенно выше базовых лимитов, что компенсируется exemptions.
**Impact**: сложность локализации багов, высокая связность, усложнение ревью и переиспользования.
**Recommendation**: переразбивка по bounded-context/use-case factories и policy-компонентам.

### [P2] Частичная неполнота архитектурного контроля (skip-ветки)

**Location**: прогон `tests/architecture` (несколько `SKIPPED`, включая bootstrap/tracing/env-var checks).
**Impact**: слепые зоны в местах, где проект исторически менялся.
**Recommendation**: устранить причины skip или зафиксировать «временные» xfail с expiry и owner.

### [P2] Смешение orchestration + policy + config resolution в отдельных фабриках

**Location**: `src/bioetl/composition/factories/pipeline_factory.py`, `src/bioetl/composition/providers/registration.py`.
**Impact**: повышение когнитивной сложности и утечки инфраструктурных деталей в orchestration-код.
**Recommendation**: выделить отдельные policy-resolvers, provider assemblers, run-context builders.

### [P2] Интерфейсный слой частично реэкспортирует инфраструктуру

**Location**: `src/bioetl/interfaces/observability.py` (`start_metrics_server` из infra).
**Impact**: ослабление «чистоты» интерфейсного контракта и потенциальная зависимость внешних потребителей от infra API.
**Recommendation**: скрыть это за application/composition entrypoint, оставить интерфейсу стабильный абстрактный контракт.

### [P3] Сильная governance-база и архитектурные тесты

**Location**: `tests/architecture/*`, `docs/00-project/*`.
**Impact**: высокое качество архитектурной валидации и воспроизводимость решений.

### [P3] Высокая дисциплина типизации

**Location**: результат `mypy --strict` успешен для 606 файлов.
**Impact**: ниже риск runtime-ошибок и выше рефакторинг-безопасность.

______________________________________________________________________

## Приоритизированный план рефакторинга

### Шаг 1 (Критичный): Программа снижения exemption-долга (Q1→Q2)

- **Цель**: снизить общий объём исключений и вернуть силу quality-gates.
- **Конкретные правки**:
  - Вести backlog по registries: `file_size_limits`, `function_length`, `god_object`.
  - Разбить топ-20 файлов по LOC/complexity на подмодули.
  - Для каждого удалённого exemption — обновлять `architecture_metric_exemptions.yaml` и debt scorecard.
- **Риски**: функциональные регрессии при крупной декомпозиции.
- **Минимизация**: refactor-only PRs, golden tests, поэтапные feature-free изменения.
- **Definition of Done**:
  - `total_exemptions` снижено минимум на 8–12%.
  - Нет роста ни в одном registry budget.
  - `tests/architecture` зелёные.

### Шаг 2 (Критичный): Декомпозиция composition factory-монолитов

- **Цель**: уменьшить связанность, выделить явные assembly boundaries.
- **Конкретные правки**:
  - `pipeline_factory.py` → модули: `run_context_builder.py`, `dq_config_resolver.py`, `pipeline_assembler.py`, `transformer_assembler.py`.
  - `providers/registration.py` → provider-specific assemblers (`chembl_assembler`, `pubchem_assembler`, ...).
  - Вынести provider policy-map в декларативный конфиг/реестр.
- **Риски**: циклические импорты в composition.
- **Минимизация**: предварительно добавить тест на import DAG и запрет back-edge.
- **Definition of Done**:
  - LOC ключевых фабрик < 400 (или с плановым временным лимитом и expiry).
  - Снижение количества exemption-записей по соответствующим файлам.

### Шаг 3 (Высокий): Усиление boundary-контрактов интерфейсного слоя

- **Цель**: исключить «прямые» re-export зависимости интерфейсов от инфраструктуры.
- **Конкретные правки**:
  - `interfaces/observability.py` перевести на composition/application entrypoint.
  - Ввести тест-запрет `interfaces -> infrastructure` кроме whitelist c expiry.
- **Риски**: breaking changes для внешних импортов.
- **Минимизация**: backward-compatible shim + deprecation warning на 1 релиз.
- **Definition of Done**:
  - Нет прямых infra-импортов в interfaces, кроме задокументированных и временных.

### Шаг 4 (Высокий): Закрытие skip-зон в архитектурных тестах

- **Цель**: повысить полноту автоматического архитектурного контроля.
- **Конкретные правки**:
  - Устранить причины `skip` в bootstrap/tracing/env-var tests.
  - Где устранить сразу нельзя — заменить `skip` на `xfail(strict=False)` с owner+expiry.
- **Риски**: нестабильность CI при включении старых тестов.
- **Минимизация**: staged rollout (warn → fail), nightly gates до обязательного режима.
- **Definition of Done**:
  - Доля skipped архитектурных тестов < 0.5%.

### Шаг 5 (Средний): Нормализация ответственности доменных и прикладных сервисов

- **Цель**: убрать латентные god-object паттерны.
- **Конкретные правки**:
  - Разделить большие сервисы на policy/value/transformation компоненты.
  - Вынести cross-cutting helpers (normalization/hash/DQ thresholds) в переиспользуемые доменные сервисы.
- **Риски**: деградация производительности из-за избыточной гранулярности.
- **Минимизация**: бенчмарки hot path до/после, профилирование.
- **Definition of Done**:
  - Снижение нарушений в `god_object`, `function_length`, `class_size`.

### Шаг 6 (Желательный): Укрепление архитектурной observability

- **Цель**: связать техдолг с измеримыми KPI качества.
- **Конкретные правки**:
  - Добавить dashboard: exemptions by registry/owner/expiry, skip-rate, import-violations trend.
  - Пороговые алерты на рост debt > N за релиз.
- **Риски**: шум алертов.
- **Минимизация**: rolling baseline + процентные пороги.
- **Definition of Done**:
  - KPI доступны в CI artifacts, тренды видны поквартально.

______________________________________________________________________

## Рекомендации по метрикам и тестам против архитектурного регресса

1. **Architecture Compliance Index (ACI)**

   - Формула: `1 - (violations + weighted_skips) / total_checks`.
   - Источник: `tests/architecture` + статический анализ импортов.
   - Влияние на интегральный балл: категории 1, 2, 5, 8.

1. **Debt Pressure Index (DPI)**

   - Формула: `active_exemptions / quarter_budget` + штраф за просроченные expiry.
   - Источник: `configs/quality/debt_scorecard.yaml`, `architecture_metric_exemptions.yaml`.
   - Влияние: категории 3, 10.

1. **Boundary Purity Score**

   - Проверки на forbidden imports + interfaces→infra direct imports + domain I/O bans.
   - Влияние: категории 1, 2.

1. **Refactorability Signals**

   - P95 LOC/module, P95 function length, top-N complexity trend.
   - Влияние: категории 3, 10.

1. **Reliability Governance Metrics**

   - Ошибки по severity, retry/circuit-breaker события, % run_id в логах.
   - Влияние: категории 6, 7.

1. **Documentation Drift Metric**

   - Доля ADR/RULES ссылок, подтверждённых тестами/линтерами.
   - Влияние: категория 9.

### Прогноз изменения интегрального балла после ключевых шагов

- После шагов 1–2 (снижение debt + декомпозиция factory): **+0.6…+0.9**.
- После шагов 3–4 (boundary hardening + skip closure): **+0.2…+0.4**.
- После шагов 5–6 (service normalization + KPI observability): **+0.2…+0.3**.

**Ожидаемый целевой балл после 2 кварталов:** **8.4–8.8 / 10** (переход в «зрелый» диапазон).
