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

| Категория                       | Описание                                                                                         |  Вес | Оценка (1-10) | Взвешенный балл |
| ------------------------------- | ------------------------------------------------------------------------------------------------ | ---: | ------------: | --------------: |
| Layer Boundaries                | Соблюдение import-matrix, запреты межслойных импортов, private-import policy                     | 0.14 |             9 |            1.26 |
| Hexagonal + DDD Fit             | Соответствие Ports & Adapters, чистота `domain`, роль `application` как orchestration            | 0.11 |             8 |            0.88 |
| Dependency Injection            | DI через `composition`, отсутствие service locator и hard-coded wiring                           | 0.08 |             8 |            0.64 |
| Module Boundary Clarity         | Ясность фасадов, ownership, читаемость границ модулей и seams                                    | 0.10 |             7 |            0.70 |
| Topology / Hotspots             | SCC, плотные family seams, god-object pressure, change coupling                                  | 0.08 |             7 |            0.56 |
| Testing + Quality Governance    | Architecture tests, CI-гейты, `mypy --strict`, `ruff`, coverage governance                       | 0.14 |             9 |            1.26 |
| Docs + Governance Freshness     | Актуальность ADR, architecture docs, generated artifacts, compatibility/doc governance           | 0.10 |             7 |            0.70 |
| Config Ownership Flow           | Читаемость пути `configs -> infrastructure -> composition`, отсутствие смешения semantics/wiring | 0.09 |             7 |            0.63 |
| Naming + Package Consistency    | Единообразие суффиксов, package structure, фасады, import discipline                             | 0.08 |             8 |            0.64 |
| Extensibility / Maintainability | Лёгкость расширения провайдерами и пайплайнами, локальность изменений                            | 0.08 |             7 |            0.56 |

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

1. **Config-topology pressure**
   Главный оставшийся structural track сосредоточен в
   `src/bioetl/infrastructure/config/pipeline_config_loader.py`,
   `src/bioetl/infrastructure/config/dq_config_loader.py`
   и
   `src/bioetl/composition/factories/pipeline/registry_manifest.py`.

1. **Shared adapter hotspots**
   Оставшийся maintenance pressure локализован в нескольких shared adapters:
   `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`,
   `src/bioetl/infrastructure/adapters/common/base_title_fallback.py`,
   `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py`,
   `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`.

1. **Smoke-only confidence in parts of composition**
   В части `composition` уверенность всё ещё держится на smoke/import coverage,
   а не на достаточном числе targeted behaviour tests.

1. **ProviderRegistry compatibility seam**
   Пара
   `src/bioetl/composition/providers/provider_registry.py`
   и
   `src/bioetl/composition/providers/_default_registry.py`
   остаётся осознанным watchlist seam. Это уже не кризисный SCC, но и не зона
   для бесконтрольного роста.

## RF-Style DAG

1. Нормализовать lifecycle/stage model в RunLedger
   Цель: сделать execution timeline воспроизводимой и одинаковой для ordinary runner и composite runner.

Модули:

- src/bioetl/application/core/runner_flow.py
- src/bioetl/application/composite/runner_pkg/runner_control_plane_mixin.py
- src/bioetl/application/services/run_ledger_service.py
- src/bioetl/domain/control_plane/run_ledger.py

Шаги:

- Зафиксировать canonical stage taxonomy в domain-level contract.
- Свести ordinary/composite paths к одному набору stage names.
- Оставить minimal richer timeline: run_started, stage_started, stage_completed, run_finished, run_failed, run_shutdown.
- Не вводить новые event types без operational необходимости.

Риски:

- сломать inspection/reporting path;
- получить несовместимый event stream между old/new runs.

Снижение риска:

- сначала ввести contract и canonicalizers;
- потом переключать producers;
- не менять append-only semantics.

Проверка:

- tests/unit/application/services/test_run_ledger_service.py
- checkpoint/replay suite в tests/unit/application/composite/checkpoint
- architecture tests, связанные с execution context

DoD:

- оба runner path пишут одинаковую timeline model;
- replay и inspection не требуют special-case логики для composite runner.

2. Разгрузить family hotspot в application/core
   Цель: уменьшить orchestration density в главной pressure zone без top-level reorg.

Модули:

- family src/bioetl/application/core
- стартовые кандидаты: execution/lifecycle/runner-support subfamilies вокруг runner flow и checkpoint lifecycle

Шаги:

- Сделать family map: execution flow, lifecycle, checkpoint support, diagnostics support.
- Выделить pure decision logic из крупных orchestration helpers в небольшие application-local modules.
- Сокращать coordination-heavy файлы не “по строкам”, а по семантическим seams.

Риски:

- создать лишнюю фрагментацию;
- ухудшить discoverability.

Снижение риска:

- дробить только по bounded responsibilities;
- после каждого шага смотреть на file size, fan-in, imports.

Проверка:

- tests/architecture/test_code_metrics.py
- tests/architecture/test_regression_metrics.py
- smoke unit suites по runner/checkpoint flows

DoD:

- hotspot family становится легче читать;
- крупные orchestration модули превращаются в thin coordinators.

3. Уменьшить coordination gravity в application services
   Цель: не дать src/bioetl/application/services/run_ledger_service.py и src/bioetl/application/services/pipeline_runner_service.py стать god-service hubs.

Модули:

- src/bioetl/application/services/run_ledger_service.py
- src/bioetl/application/services/pipeline_runner_service.py
- связанные helper services рядом в application/services

Шаги:

- Вынести payload normalization и diagnostic anchor assembly в private helpers/modules.
- Оставить сервисам orchestration role и thin public API.
- Отделить logger correlation, metrics/result normalization и policy branching.

Риски:

- размазать ответственность между слишком многими helper-модулями;
- случайно сломать public API сервисов.

Снижение риска:

- public methods не менять без необходимости;
- helper extraction делать только для pure logic.

Проверка:

- unit tests на сервисы;
- mypy strict на application/services;
- architecture checks на logging/structlog contracts

DoD:

- сервисы заметно короче и линейнее;
- behaviour unchanged;
- новые cross-cutting concerns не липнут обратно в сервисы.

4. Довести provider/composition seams до узкого и устойчивого вида
   Цель: убрать остаточный abstraction pressure в provider registry / provider assembly.

Модули:

- src/bioetl/composition/providers/provider_registry.py
- src/bioetl/composition/providers/registration_bio.py
- src/bioetl/composition/providers/registration_biblio.py
- возможные shared helpers в composition/providers/\_\*.py

Шаги:

- Свести assembly modules к manifest-level declarations + узким helper seams.
- Не расширять compatibility obligations в provider_registry.py.
- Убрать оставшиеся implicit registry access patterns и дублирующий assembly plumbing.

Риски:

- regression в provider config tests;
- ломка старых registration expectations.

Снижение риска:

- держать migration через named seams;
- постоянно гонять provider registry contract tests.

Проверка:

- tests/architecture/test_registry_contracts.py
- tests/architecture/test_provider_registry_decomposition.py
- tests/unit/composition/providers/\*

DoD:

- provider assembly читается как декларативная wiring layer;
- raw registry callsites и assembly drift не возвращаются.

5. Перевести file-growth и fan-in pressure в family-scoped ratchets
   Цель: перестать только наблюдать рост сложности и начать ограничивать его тестами там, где evidence уже зрелое.

Модули:

- configs/quality/debt_scorecard.yaml
- regression/code metrics tests в tests/architecture
- quality configs для topology/hotspot tracking

Шаги:

- Выделить 2–3 hot families: application/core, composition/bootstrap/runtime, при необходимости application/services.
- Для каждой семьи ввести узкий budget на file size, fan-in или cross-layer edges.
- Избегать repo-wide tightening без family baseline.

Риски:

- noisy red CI;
- ложные блокировки на benign changes.

Снижение риска:

- ratchet only from current measured baseline;
- tightening маленькими шагами.

Проверка:

- tests/architecture/test_regression_metrics.py
- tests/architecture/test_code_metrics.py

DoD:

- ключевые hotspot families имеют собственные budgets;
- complexity drift ловится раньше, чем превращается в refactor wave.

6. Довести replay/fixture/contract governance до реально enforced состояния
   Цель: завершить test-governance слой так, чтобы replay/fixture/contract surfaces были не просто описаны, а operationally managed.

Модули:

- configs/quality/test_matrix.yaml
- configs/quality/fixture_governance_ledger.yaml
- configs/quality/ci_coverage_surface_matrix.yaml
- contract/replay-related architecture tests

Шаги:

- Перевести наиболее зрелые rollout items из planned/partial в partial/enforced.
- Для каждого rollout surface привязать owner, next step, promotion criteria.
- Довести contract_snapshots до первого реального adoption slice.

Риски:

- governance станет слишком тяжёлой;
- обновление snapshots будет болезненным.

Снижение риска:

- идти provider-family slices, а не broad rollout;
- использовать documented update path.

Проверка:

- tests/architecture/test_fixture_governance_ledger.py
- tests/architecture/test_ci_coverage_surface_matrix.py
- tests/architecture/test_test_matrix_lane_policy.py
- tests/architecture/test_fixture_governance_rollout.py

DoD:

- replay/fixture/contract governance не висит как “planned idea”;
- tracked ledgers и tests соответствуют реальному execution model.

7. Устранить drift между кодом, dependency artifacts и historical docs
   Цель: сделать docs-as-code и generated artifacts надёжными, а не хрупкими.

Модули:

- generated dependency map workflow
- tests/architecture/test_architecture_dependency_docs_drift.py
- historical evidence/docs в docs/reports/evidence/\*

Шаги:

- Зафиксировать canonical regeneration path для dependency artifacts.
- Обновить historical docs, где уже закрытые seams описаны как live backlog.
- Минимизировать ручной шаг между code change и generated artifact sync.

Риски:

- превратить документацию в шумный ritual;
- избыточные regen требования.

Снижение риска:

- синхронизировать только high-signal artifacts;
- не генерировать “всё подряд”.

Проверка:

- dependency docs drift test;
- docs/generator checks, уже используемые в repo

DoD:

- dependency artifact drift не всплывает как регулярная случайная поломка;
- исторические summary не противоречат текущей архитектуре.

8. Формализовать acceptance baseline как живой архитектурный контракт
   Цель: собрать один curated acceptance slice, который описывает фактическую архитектуру, а не старый план.

Модули:

- tests/architecture/\* curated subset
- tests/unit/application/services/test_run_ledger_service.py
- checkpoint suite
- logging correlation / manifest deprecation / no-structlog guards

Шаги:

- Сформировать узкий acceptance checklist.
- Привязать каждый acceptance пункт к конкретному test file.
- При необходимости добавить один aggregator doc или lightweight test manifest.

Риски:

- acceptance suite станет слишком широкой и дорогой;
- дублирование существующих guardrails.

Снижение риска:

- не писать новый большой test layer;
- собрать curated slice из уже существующих тестов.

Проверка:

- pytest tests/architecture/
- targeted unit suites
- mypy --strict

DoD:

- есть один воспроизводимый acceptance baseline;
- им можно завершать bounded refactor без споров о “настоящей” архитектуре.

Рекомендуемая последовательность

1. RunLedger timeline
1. application/core hotspot split
1. service gravity reduction
1. provider/composition seam narrowing
1. family-scoped ratchets
1. replay/fixture/contract governance
1. docs/artifact drift cleanup
1. acceptance baseline formalization

Что даст на практике

- После задач 1–4 снизится архитектурный риск и станет проще делать runtime-related изменения.
- После задач 5–6 проект начнёт не только замечать drift, но и системно ограничивать его.
- После задач 7–8 репозиторий получит более устойчивый operating model: меньше споров, меньше скрытого drift, быстрее bounded refactors.

Если хотите, следующим сообщением я превращу это в формат roadmap на 3 спринта с оценкой трудоёмкости и зависимостями.

› какие задачи можно параллерить

• Безопасно параллелить можно не всё. По текущему набору задач я бы разделил так.

Можно параллелить сразу

- Read-only анализ по задачам 5, 7, 8
  - сбор baseline-метрик для family budgets;
  - аудит historical docs и generated artifacts;
  - сбор acceptance checklist из уже существующих тестов.
- Тесты + документация после завершения одной кодовой задачи
  - например, после задачи 1 можно параллельно:
    - гонять targeted tests;
    - обновлять acceptance/docs/evidence.
- Задача 7 и задача 8
  - если 7 ограничить docs/artifact drift cleanup,
  - а 8 делать как curated acceptance mapping без правок в production-коде.
- Задача 5 и задача 7
  - если 5 делать только как проектирование новых ratchets/budgets,
  - а 7 как docs-only cleanup.
  - Если 5 уже меняет tests/architecture и quality configs, лучше не параллелить.

Лучше делать последовательно

- 1. RunLedger timeline normalization
- 2. application/core hotspot split
- 3. service gravity reduction

Причина:

- 1 и 3 оба трогают src/bioetl/application/services/run_ledger_service.py
- 1 и 2 оба лезут в orchestration/runtime family
- 2 и 3 пересекаются по application-слою и легко дают merge conflicts и повторную переукладку одного и того же кода

Отдельным независимым потоком можно

- 4. provider/composition seam narrowing

Она хорошо изолирована от 1–3, потому что живёт в composition/providers/\*. Если очень хочется ускориться, это лучший кандидат на отдельный worktree/исполнителя.

Условно можно параллелить, но только в отдельных worktree

- 1 и 4
- 3 и 4
- 6 и 7

Но только если заранее разделить ownership:

- кто-то трогает только application/\*
- кто-то только composition/providers/\*
- кто-то только docs/reports/\*

Не стоит параллелить

- 5 с 8, если обе задачи меняют tests/architecture/\*
- 6 с 8, если acceptance baseline будет включать те же governance tests/configs
- любые две задачи, которые одновременно меняют configs/quality/\*

Практически лучший план распараллеливания

1. Последовательно: 1 -> 2 -> 3
1. Параллельно с этим в отдельном потоке: 4
1. После стабилизации кода параллельно:
   - 5 metrics/ratchets
   - 7 docs/artifact drift cleanup
1. Потом последовательно:
   - 6 governance rollout
   - 8 final acceptance baseline
