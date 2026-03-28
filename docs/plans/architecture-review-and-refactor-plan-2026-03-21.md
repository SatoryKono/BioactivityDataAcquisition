# Architecture Review And Refactor Plan

Дата: 2026-03-23  
Статус: supporting assessment and refactor roadmap  
Язык: русский

> Этот документ — repo-only assessment surface. Он помогает
> интерпретировать текущее архитектурное состояние и выбирать bounded refactor
> waves, но не заменяет canonical project guidance в `docs/00-project/`,
> `docs/01-requirements/`, `docs/02-architecture/` и active guides under
> `docs/03-guides/`.

## Назначение

Этот документ фиксирует актуальную архитектурную оценку проекта и
приоритизированный план рефакторинга на основе:

- текущего состояния кода;
- active evidence packs;
- architecture tests и import guards;
- локальной проверки governance artifacts;
- актуального consolidated backlog.

Это **не** второй competing backlog вместо
[consolidated-open-tasks-plan-2026-03-21.md](./consolidated-open-tasks-plan-2026-03-21.md).
Его нужно использовать как supporting assessment snapshot:

- для оценки качества текущего состояния;
- для выбора следующей bounded refactor wave;
- для сравнения ожидаемого эффекта по интегральному баллу;
- для связывания backlog-задач с архитектурными целями.

## Источники

- [consolidated-open-tasks-plan-2026-03-21.md](./consolidated-open-tasks-plan-2026-03-21.md)
- [module-dependency-map.md](../02-architecture/generated/module-dependency-map.md)
- [07-compatibility-facade-inventory.md](../02-architecture/07-compatibility-facade-inventory.md)
- [RULES.md](../00-project/RULES.md)
- [project-import-governance/SUMMARY.md](../reports/evidence/project-import-governance/SUMMARY.md)
- [project-package-topology/SUMMARY.md](../reports/evidence/project-package-topology/SUMMARY.md)
- [project-file-structure/04-decisions/SUMMARY.md](../reports/evidence/project-file-structure/04-decisions/SUMMARY.md)
- [ADR-043-documentation-knowledge-management.md](../02-architecture/decisions/ADR-043-documentation-knowledge-management.md)

## Итоговая оценка

Интегральный балл проекта: **7.83 / 10.00**

Интерпретация:

- `0.0–4.9` — критическое состояние
- `5.0–7.9` — удовлетворительно, требуется системный рефакторинг
- `8.0–10.0` — хорошее состояние, точечные улучшения

Текущий вывод: проект находится в **верхней части диапазона
“удовлетворительно”** и близок к переходу в категорию “хорошее состояние”.
Архитектура сильная и реально enforced, а основной долг сейчас сидит не в
массовых нарушениях слоёв, а в нескольких плотных seams, freshness generated
artifacts и неполной behavioural coverage в части `composition`.

## Таблица оценки

| Категория | Описание | Вес | Оценка (1-10) | Взвешенный балл |
|---|---|---:|---:|---:|
| Layer Boundaries | Соблюдение import-matrix, запреты межслойных импортов, private-import policy | 0.14 | 9 | 1.26 |
| Hexagonal + DDD Fit | Соответствие Ports & Adapters, чистота `domain`, роль `application` как orchestration | 0.11 | 8 | 0.88 |
| Dependency Injection | DI через `composition`, отсутствие service locator и hard-coded wiring | 0.08 | 8 | 0.64 |
| Module Boundary Clarity | Ясность фасадов, ownership, читаемость границ модулей и seams | 0.10 | 7 | 0.70 |
| Topology / Hotspots | SCC, плотные family seams, god-object pressure, change coupling | 0.08 | 7 | 0.56 |
| Testing + Quality Governance | Architecture tests, CI-гейты, `mypy --strict`, `ruff`, coverage governance | 0.14 | 9 | 1.26 |
| Docs + Governance Freshness | Актуальность ADR, architecture docs, generated artifacts, compatibility/doc governance | 0.10 | 7 | 0.70 |
| Config Ownership Flow | Читаемость пути `configs -> infrastructure -> composition`, отсутствие смешения semantics/wiring | 0.09 | 7 | 0.63 |
| Naming + Package Consistency | Единообразие суффиксов, package structure, фасады, import discipline | 0.08 | 8 | 0.64 |
| Extensibility / Maintainability | Лёгкость расширения провайдерами и пайплайнами, локальность изменений | 0.08 | 7 | 0.56 |

## Интерпретация по ключевым критериям

### 1. Соблюдение слоёв

Слои `domain / application / infrastructure / composition / interfaces`
реальны, а не декларативны. Import-matrix поддерживается не только
документацией, но и architecture tests. Главный риск здесь не broad layer
violation, а drift в generated governance artifacts.

### 2. Соответствие Ports & Adapters и DDD

Проект хорошо соответствует Hexagonal/DDD модели. Публичный фасад портов,
тонкие CLI entrypoints и composition-root discipline читаются последовательно.
Смягчающий фактор: `domain` несёт часть runtime-oriented contract surface, что
является осознанным архитектурным компромиссом, а не дефектом.

### 3. Явность границ модулей и зависимостей

Границы package families в целом зрелые, но несколько плотных seams всё ещё
повышают стоимость reasoning о зависимостях. Особенно это касается
`infrastructure/config`, shared adapters и части `composition`.

### 4. Единообразие нейминга, структуры пакетов и файлов

Нейминг и фасады в целом стабильны. Основная неоднозначность осталась не в
базовой структуре, а в compatibility/watchlist seams и отдельных broad support
модулях.

## Ключевые проблемы

1. **Governance freshness residuals**
   Основной MUST-долг по generated artifacts уже снят через `RF-010` и
   `RF-011`, но freshness discipline остаётся чувствительной зоной: dependency
   map, compatibility snapshot и full verify baseline нужно удерживать как
   operational guardrails после следующих implementation волн.

2. **Config-topology pressure**
   Главный оставшийся structural track сосредоточен в
   `src/bioetl/infrastructure/config/pipeline_config_loader.py`,
   `src/bioetl/infrastructure/config/dq_config_loader.py`
   и
   `src/bioetl/composition/factories/pipeline/registry_manifest.py`.

3. **Shared adapter hotspots**
   Оставшийся maintenance pressure локализован в нескольких shared adapters:
   `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`,
   `src/bioetl/infrastructure/adapters/common/base_title_fallback.py`,
   `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py`,
   `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`.

4. **Smoke-only confidence in parts of composition**
   В части `composition` уверенность всё ещё держится на smoke/import coverage,
   а не на достаточном числе targeted behaviour tests.

5. **ProviderRegistry compatibility seam**
   Пара
   `src/bioetl/composition/providers/provider_registry.py`
   и
   `src/bioetl/composition/providers/_default_registry.py`
   остаётся осознанным watchlist seam. Это уже не кризисный SCC, но и не зона
   для бесконтрольного роста.

## RF-Style DAG

| RF | Приоритет | Зависит от | Риск |
|---|---:|---|---|
| RF-010 Dependency-Map Freshness | completed | - | low |
| RF-011 Full Verify + Coverage Snapshot | completed | RF-010 | medium |
| RF-012 Config Topology Closeout | P1 | RF-010 | high |
| RF-013 Registry Manifest Assembly-Only Guard | P1 | RF-012 | medium |
| RF-014 Shared Adapter Hotspot 1 (cached bronze) | P2 | RF-011 | medium |
| RF-015 Shared Adapter Hotspot 2 (title fallback) | P2 | RF-014 | medium |
| RF-016 Shared Circuit Breaker Contract Unify | P2 | RF-015 | medium-high |
| RF-017 Replace Smoke-Only Composition Coverage | P2.5 | RF-011 | medium |
| RF-018 ProviderRegistry Compat Seam No-Growth Ratchet | P3 | RF-011 | low |

## Протокол исполнения

1. Каждый RF исполняется **последовательно**, чтобы не создавать конфликтов по
   файлам и не смешивать несколько structural волн.
2. После каждого RF запускаются **параллельно** только два независимых блока:
   `targeted tests` и `docs/governance checks`.
3. Любые primary/double-check аудиты запускаются **последовательно**.

## Приоритизированный план рефакторинга

### RF-010. Dependency-Map Freshness

Статус: completed on `2026-03-23`.

- **Цель:** убрать MUST-дрейф и вернуть доверие к governance artifacts.
- **Конкретные правки:** обновить только generated файлы
  [module-dependency-map.md](../02-architecture/generated/module-dependency-map.md)
  и
  [module-dependency-map.json](../02-architecture/generated/module-dependency-map.json)
  через `scripts/qa/generate_architecture_dependency_map.py --update`.
- **Риски:** можно “подкрасить” картину без понимания фактического изменения
  графа.
- **Минимизация рисков:** фиксировать это как generated refresh и не смешивать с
  ручными doc edits.
- **Definition of Done:** `generate_architecture_dependency_map.py --check`
  зелёный, related drift guards зелёные.

Closeout:

- dependency-map artifacts обновлены и повторно подтверждены `--check`;
- generated docs больше не отстают от текущего import graph;
- freshness дальше удерживается уже как operational ratchet, а не как active
  refactor track.

### RF-011. Full Verify + Coverage Snapshot

Статус: completed on `2026-03-23`.

- **Цель:** получить текущий end-to-end confidence baseline после длинной серии
  refactor waves.
- **Конкретные правки:** прогнать `pytest tests -q`, собрать coverage snapshot
  при необходимости, повторно подтвердить `ruff`, `mypy`, compatibility snapshot
  и dependency-map checks.
- **Риски:** long-running suite может открыть flaky или ordering-sensitive
  tests.
- **Минимизация рисков:** сначала секторные прогоны (`tests/architecture`,
  `tests/unit`), затем full suite.
- **Definition of Done:** полный verify bundle зелёный.

Closeout:

- секторные verify-прогоны (`tests/architecture`, `tests/unit`) доведены до
  стабильного зелёного состояния;
- полный `pytest tests -q` повторно подтверждён после targeted stability fixes
  в compatibility/governance и scripts-inventory scan;
- `ruff`, `mypy`, dependency-map check и compatibility snapshot check
  повторно подтверждены;
- отдельный coverage artifact не понадобился для closeout, потому что целевой
  confidence baseline уже подтверждён полным verify bundle.

### RF-012. Config Topology Closeout

- **Цель:** сделать ownership читабельным как
  `configs -> infrastructure/config (read/normalize/validate/map) -> composition`.
- **Конкретные правки:** в
  `src/bioetl/infrastructure/config/pipeline_config_loader.py`
  и
  `src/bioetl/infrastructure/config/dq_config_loader.py`
  выделить внутренние стадии `reader`, `normalizer`, `validator`, `mapper`;
  в
  `src/bioetl/composition/factories/pipeline/registry_manifest.py`
  оставить только assembly/wiring.
- **Риски:** высокий blast radius, потому что loaders затрагивают почти весь
  runtime.
- **Минимизация рисков:** идти slice-by-slice, сохранить стабильный внешний API
  loader’ов, использовать golden fixtures и targeted pipeline smoke.
- **Definition of Done:** config-related tests зелёные, `composition` не владеет
  normalization logic, ownership story читается без дополнительных compat
  исключений.

### RF-013. Registry Manifest Assembly-Only Guard

- **Цель:** не дать
  `src/bioetl/composition/factories/pipeline/registry_manifest.py`
  стать вторым config-owner.
- **Конкретные правки:** добавить architecture guard, запрещающий
  `yaml`/config-normalization imports внутри manifest; добавить маленький
  unit-test на то, что manifest only assembles.
- **Риски:** guard может стать слишком жёстким.
- **Минимизация рисков:** запрещать только IO/normalization, но не typed
  contracts.
- **Definition of Done:** новый guard зелёный, targeted tests зелёные.

### RF-014. Shared Adapter Hotspot 1: Cached Bronze

- **Цель:** уменьшить coupling между cache policy, key-building и IO.
- **Конкретные правки:** в
  `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`
  вынести decision logic в маленький pure helper, отдельно выделить cache-key
  construction и policy seam.
- **Риски:** можно незаметно изменить кэш-поведение.
- **Минимизация рисков:** сначала unit-тесты на decision branches, затем
  рефакторинг; при необходимости один integration/VCR test.
- **Definition of Done:** behaviour не изменился, модуль стал уже по
  ответственности, новые unit-тесты зелёные.

### RF-015. Shared Adapter Hotspot 2: Title Fallback

- **Цель:** сделать fallback behaviour расширяемым и менее плотным.
- **Конкретные правки:** в
  `src/bioetl/infrastructure/adapters/common/base_title_fallback.py`
  выделить `TitleFallbackStrategy` как `Protocol` или маленький ABC, вынести
  1-2 конкретные стратегии и оставить в основном модуле только оркестрацию.
- **Риски:** переусложнение простого helper.
- **Минимизация рисков:** выносить только реально повторяющиеся правила и не
  дробить без выигрыша в читаемости.
- **Definition of Done:** код стал проще читать, стратегии покрыты unit-тестами.

### RF-016. Shared Circuit Breaker Contract Unify

- **Цель:** убрать скрытую дубликацию state/decision semantics.
- **Конкретные правки:** вынести общий typed seam для breaker-state и transition
  logic, который будет использоваться и в
  `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py`,
  и в
  `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`.
- **Риски:** регрессии в resiliency path.
- **Минимизация рисков:** сначала стабилизировать unit-тесты на state
  transitions, публичные API не менять.
- **Definition of Done:** shared typed contract существует, дублирование
  уменьшено, unit/integration tests зелёные.

### RF-017. Replace Smoke-Only Composition Coverage

- **Цель:** перенести часть confidence с import-only smoke на поведенческие
  unit-тесты.
- **Конкретные правки:** взять 3-5 часто меняемых модулей из
  `tests/smoke/test_smoke_composition.py`
  и добавить unit-тесты формата “build returns expected port/bundle shape”,
  “dependency injected”, “no import-time side effects”.
- **Риски:** brittle wiring-tests.
- **Минимизация рисков:** тестировать shape и contract, а не конкретные
  реализации и не весь DI-graph.
- **Definition of Done:** список модулей “без dedicated coverage” сокращён,
  новые unit-тесты зелёные.

### RF-018. ProviderRegistry Compat Seam No-Growth Ratchet

- **Цель:** удержать compat seam как watchlist, не открывая новую миграцию.
- **Конкретные правки:** добавить/сохранить guard против новых raw
  `ProviderRegistry.*` call sites в `src`, кроме уже санкционированных seams.
- **Риски:** почти отсутствуют, если guard baseline-aware.
- **Минимизация рисков:** не менять runtime semantics.
- **Definition of Done:** compat seam не растёт, tests фиксируют non-growth.

## Метрики и ожидаемый рост балла

| Категория | Контрольные метрики и тесты | Целевой балл после ключевых шагов |
|---|---|---:|
| Layer Boundaries | `tests/architecture/test_forbidden_imports.py`, `tests/architecture/test_private_module_imports.py` | 9.0 |
| Hexagonal + DDD Fit | `tests/architecture/test_domain_public_api.py`, отсутствие infra-imports в `domain/application` | 8.0 |
| Dependency Injection | targeted review/grep на hard-coded constructors вне `composition`, composition tests | 8.0 |
| Module Boundary Clarity | новые guards для `registry_manifest.py`, уменьшение responsibilities в config loaders | 8.0 |
| Topology / Hotspots | bounded refactors в shared adapters, сохранение reduced-SCC state | 8.0 |
| Testing + Quality Governance | `pytest tests -q`, новые unit-тесты вместо части smoke-only confidence | 9.5 |
| Docs + Governance Freshness | `generate_architecture_dependency_map.py --check`, `generate_compatibility_facade_snapshot.py --check` | 8.0 |
| Config Ownership Flow | focused tests на loaders, anti-leak guard для `composition` | 9.0 |
| Naming + Package Consistency | `ruff`, `mypy`, architecture/doc guards без нового drift | 8.5 |
| Extensibility / Maintainability | локализация shared adapter logic и более дешёвые изменения в `composition` | 8.0 |

Если реализовать `RF-010..RF-017`, реалистичный целевой интегральный балл:
**8.4-8.8 / 10.0**.
