# Architecture Audit & Refactoring Plan (BioETL)

Date: 2026-03-04
Scope: `src/bioetl`, `tests/architecture`, quality governance config and baseline reports.

## Verification log (executed)

- `uv run python -m pytest tests/architecture/ -q` → PASS (with expected skips).
- `uv run python -m mypy --strict src/bioetl/` → PASS.

## Executive summary

Проект в целом находится в **хорошем рабочем состоянии** по архитектурным инвариантам (слои, порты, Medallion, strict typing), но с заметным накопленным архитектурным долгом в части размера модулей, сложности и `Any`-контрактов.

Ключевой вывод: **базовые архитектурные “guardrails” работают и защищают систему**, но для долгосрочной эволюции нужно системно снижать debt budget, декомпозировать крупные модули и ужесточать типобезопасность на границах.

______________________________________________________________________

## 1) Оценка по 10 категориям

| Категория                                        | Что оценивается                                                                                         |      Вес | Оценка (1–10) | Взвешенный балл |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | -------: | ------------: | --------------: |
| 1. Layered architecture compliance               | Соблюдение границ `domain/application/infrastructure/composition/interfaces` и направление зависимостей |     0.14 |           8.8 |            1.23 |
| 2. Hexagonal (Ports & Adapters) & DDD discipline | Явность портов, изоляция адаптеров, роль домена                                                         |     0.12 |           8.5 |            1.02 |
| 3. Modularity & coupling                         | Размер модулей, связность, наличие потенциальных god-модулей                                            |     0.11 |           6.3 |            0.69 |
| 4. Domain model quality                          | Чистота домена, инварианты, отсутствие I/O в domain                                                     |     0.10 |           8.3 |            0.83 |
| 5. Type safety & API contracts                   | `mypy --strict`, качество аннотаций, объём `Any`                                                        |     0.10 |           7.1 |            0.71 |
| 6. Testing & architectural guardrails            | Полнота архитектурных тестов и качество quality-gates                                                   |     0.11 |           9.0 |            0.99 |
| 7. Error handling & resilience                   | Стратегия обработки ошибок, circuit breaker / retry / деградации                                        |     0.08 |           7.6 |            0.61 |
| 8. Logging & observability                       | Структурированность логов, корреляция (`run_id`), метрики                                               |     0.08 |           8.0 |            0.64 |
| 9. Security & configuration hygiene              | Local-only policy, запреты на cloud/distributed зависимости, централизация конфигов                     |     0.08 |           8.2 |            0.66 |
| 10. Technical debt & maintainability             | Exemptions budget, hotspot-метрики, эволюционная стоимость изменений                                    |     0.08 |           5.9 |            0.47 |
| **Итого**                                        |                                                                                                         | **1.00** |               |   **7.85 / 10** |

### Интерпретация интегрального балла

- 0.0–4.9: архитектура нестабильна.
- 5.0–7.9: архитектура рабочая, но с заметным долгом.
- 8.0–10: зрелая и устойчиво эволюционируемая архитектура.

**Текущее состояние: 7.85** — верхняя граница «рабочая, но с долгом», почти «зрелая». Основной тормоз — размер/сложность отдельных модулей и накопленные quality exemptions.

______________________________________________________________________

## 2) Архитектурная оценка по requested аспектам

### 2.1 Соблюдение слоистой структуры

**Наблюдение:** соблюдение слоёв формализовано в архитектурных тестах и подтверждено прогоном тестового набора.

- Тесты фиксируют запрет на инфраструктурные импорты в домене и запрет зависимости domain→application/infrastructure (`test_layer_dependencies.py`).
- Отдельно проверяется чистота домена (I/O-паттерны запрещены) (`test_domain_purity.py`).

**Вывод:** текущее состояние ближе к strong compliance.

### 2.2 Ports & Adapters (Hexagonal) и DDD

**Наблюдение:** контракт портов централизован в фасаде `bioetl.domain.ports`, и это также закреплено архитектурным тестом (`test_forbidden_imports.py`, REQ-ARCH-027).

- Пример порта: `StoragePort` в домене.
- Пример адаптера: ChEMBL-клиент в `infrastructure/adapters/chembl/client.py`.
- Пример orchestration use-case: `MedallionLifecycleService` в application.

**Вывод:** Hexagonal-модель реализована последовательно.

### 2.3 Явность границ модулей и зависимостей

**Наблюдение:** границы явно защищены тестами, но в реализации есть крупные фабрики/конфигурационные модули (700+ / 1000+ LOC), что усложняет локализацию изменений.

- Это уже отражено в baseline debt report как hotspot-зона.

**Вывод:** формальные границы есть, но модульная декомпозиция неравномерна.

### 2.4 Единообразие именования и структуры пакетов

**Наблюдение:** в целом имена типизированы и осмысленны, но есть структурный артефакт `domain/config` и `domain/configs` с пересекающейся семантикой.

**Вывод:** единообразие хорошее, но есть точка для унификации пакетов конфигураций.

______________________________________________________________________

## 3) Основные проблемы (prioritized findings)

### [P1] Высокий накопленный технический долг по архитектурным метрикам

- В baseline зафиксировано **485 exemptions** и большие бюджеты по size/complexity registries.
- Есть выраженные hotspots по LOC/CC и значительный объём `Any`.

**Impact:** замедление feature delivery, повышение риска регрессий в cross-cutting изменениях.

### [P2] Крупные orchestration/factory-модули (риск “god modules”)

- Baseline показывает крупные файлы в `composition/factories/*` и `domain/composite/config.py`.

**Impact:** ухудшение читаемости, высокая цена входа в модуль, сложность точечного рефакторинга.

### [P2] Смешение и дублирование semantic namespace для конфигов

- Одновременно существуют `domain/config/` и `domain/configs/`.

**Impact:** когнитивная нагрузка, риск дублирования DTO/VO и «дрейфа» импортов.

### [P2] Broad exception catches в CLI-слое

- В интерфейсных командах есть `except Exception` как fallback.

**Impact:** в интерфейсном слое это допустимее, чем в core/domain, но снижает точность error taxonomy и затрудняет observability-анализ причин.

______________________________________________________________________

## 4) Детальный план рефакторинга (от критичных к желательным)

## Step 1 (Critical): Debt burn-down wave по hotspot-файлам

**Цель:** снизить архитектурный долг (LOC/CC/function-length/god-object exemptions).

**Конкретные правки:**

- Разбить `composition/factories/pipeline_factory.py`, `services_factory.py`, `storage_adapter.py` на sub-factories по bounded responsibilities.
- Из `domain/composite/config.py` вынести:
  - immutable value objects,
  - validation helpers,
  - parsing/conversion слой.
- Ввести тонкие orchestrator-модули (`*_orchestrator.py`) без бизнес-деталей.

**Риски:**

- Непреднамеренное изменение DI wiring.
- Рост числа циклических импортов на этапе декомпозиции.

**Минимизация рисков:**

- Golden-master тесты на публичные factory API.
- Временные compatibility re-exports.
- Архтесты + mypy после каждого микрошагa.

**Критерии готово:**

- Минус ≥20% exemptions в `file_size_limits` + `function_length`.
- Нет регрессий в `tests/architecture/` и `mypy --strict`.

## Step 2 (High): Type-hardening (уменьшение `Any`)

**Цель:** повысить надёжность контрактов между слоями.

**Конкретные правки:**

- Приоритизировать модули с наибольшим `Any` в портах/адаптерах.
- Заменять `Any` на:
  - `TypedDict` для JSON payload,
  - `Protocol`/`TypeVar` для портов,
  - конкретные alias в `domain.types`.
- Ввести budget-test на уменьшение `Any` по квартальным этапам.

**Риски:**

- Избыточная строгость на границе с внешними API.

**Минимизация рисков:**

- Progressive typing: сначала outbound/internal контракты, затем inbound raw payload.
- Локальные адаптеры-сериализаторы на boundary.

**Критерии готово:**

- Снижение `Any` annotations минимум на 25% от baseline.
- `mypy --strict` remains green.

## Step 3 (High): Unify config namespace (`domain/config` vs `domain/configs`)

**Цель:** унифицировать модель конфигурации и навигацию в домене.

**Конкретные правки:**

- Выбрать канонический пакет (рекомендовано `domain/config`).
- `domain/configs` оставить как временный shim + deprecation warnings в changelog/docs.
- Мигрировать импорты пакетно (codemod).

**Риски:**

- Ломающие изменения для внутренних import paths.

**Минимизация рисков:**

- Backward-compatible re-export минимум на 1–2 релиза.
- Архтест «no new imports from deprecated package».

**Критерии готово:**

- Новые изменения не добавляют импортов из deprecated namespace.
- Дублирующихся config DTO не остаётся.

## Step 4 (Medium): CLI error taxonomy tightening

**Цель:** повысить прозрачность отказов и качество операционной диагностики.

**Конкретные правки:**

- В `interfaces/cli/commands/*` заменить часть `except Exception` на доменно-ориентированные исключения + единый mapper.
- Централизовать mapping `Exception -> ExitCode -> reason_code` в одном модуле.

**Риски:**

- Пропуск редких edge-cases и ухудшение UX CLI.

**Минимизация рисков:**

- Contract tests для exit codes и reason codes.
- Fallback catch оставить, но с обязательной меткой `unexpected_error=true`.

**Критерии готово:**

- Снижение broad catches в interfaces минимум на 50%.
- 100% покрытие mapping-таблицы unit-тестами.

## Step 5 (Medium): Observability hardening at orchestration boundaries

**Цель:** сделать диагностику пайплайнов более причинно-связной.

**Конкретные правки:**

- Проверка обязательных полей лога (`run_id`, provider, entity, stage) в pipeline-контексте.
- Добавить arch-test на минимальный набор structured keys в critical lifecycle events.

**Риски:**

- Шум в логах и рост кардинальности метрик.

**Минимизация рисков:**

- Ограничить обязательные ключи и нормализовать значения.

**Критерии готово:**

- Новые тесты observability green.
- Корреляция run-level событий в логах подтверждается smoke test.

## Step 6 (Desirable): Documentation & ADR sync for refactoring map

**Цель:** удержать согласованность архитектуры и её описания.

**Конкретные правки:**

- Обновить ADR/архдоки по новой decomposition map.
- Вести RF-идентификаторы для каждого refactoring stream.

**Риски:**

- Документация устареет относительно темпа кода.

**Минимизация рисков:**

- CI gate на docs sync (уже есть) + mandatory checklist в PR template.

**Критерии готово:**

- Нет расхождений в tests документации.

______________________________________________________________________

## 5) Рекомендуемые дополнительные метрики и тесты (anti-regression)

1. **Layer purity trend**

   - Metric: число нарушений layer tests (target: 0 постоянно).
   - Связь с баллами: Категории 1, 2, 4.

1. **Debt velocity KPI**

   - Metric: `total_exemptions` по кварталам (target: как минимум в соответствии с scorecard траекторией).
   - Связь: Категории 3, 10.

1. **Any budget KPI**

   - Metric: `Any` annotations/token count (target: устойчивое снижение).
   - Связь: Категория 5.

1. **Hotspot complexity budget**

   - Metric: max CC для top-10 функций, max LOC для top-20 файлов.
   - Связь: Категории 3, 10.

1. **CLI failure taxonomy coverage**

   - Metric: % исключений, маппящихся в детерминированные reason_code/exit_code.
   - Связь: Категория 7.

1. **Observability schema compliance**

   - Metric: % pipeline logs c mandatory keys (`run_id`, `provider`, `entity`, `stage`).
   - Связь: Категория 8.

1. **Config namespace drift check**

   - Metric: imports from deprecated config namespace (target: 0 after migration).
   - Связь: Категории 3, 9, 10.

______________________________________________________________________

## 6) Прогноз изменения интегрального балла после ключевых шагов

Оценка сценария после Steps 1–4 (без полного завершения roadmap):

- Modularity & coupling: **6.3 → 7.6**
- Type safety & contracts: **7.1 → 8.0**
- Error handling & resilience: **7.6 → 8.3**
- Technical debt & maintainability: **5.9 → 7.4**

Ожидаемый общий интегральный балл: **7.85 → ~8.35**.

Это переведёт проект из верхней зоны «рабочий с долгом» в устойчивую «зрелую» категорию, при условии сохранения текущих guardrails.

______________________________________________________________________

## Evidence index

- Layer and purity architectural checks: `tests/architecture/test_layer_dependencies.py`, `tests/architecture/test_domain_purity.py`.
- Ports facade rule and local-only policy checks: `tests/architecture/test_forbidden_imports.py`.
- Delta-only Silver implementation: `src/bioetl/infrastructure/storage/silver_writer.py` and `src/bioetl/infrastructure/storage/silver_writer_delta_mixin.py`.
- Application lifecycle orchestration sample: `src/bioetl/application/services/medallion_lifecycle.py`.
- Ports contract sample: `src/bioetl/domain/ports/storage.py`.
- Adapter implementation sample: `src/bioetl/infrastructure/adapters/chembl/client.py`.
- CLI broad catch samples: `src/bioetl/interfaces/cli/commands/run.py`, `run_all.py`, `run_composite.py`.
- Debt baseline and scorecard: `docs/reports/architecture-debt-baseline-2026-03-04.md`, `configs/quality/debt_scorecard.yaml`.
- Config namespace split sample: `src/bioetl/domain/config/__init__.py`, `src/bioetl/domain/configs/__init__.py`.
