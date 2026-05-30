# Drive BioETL technical debt to zero

**Status**: in_progress
**Priority**: P0
**Labels**: `architecture`, `tech-debt`, `governance`, `epic`
**GitHub Issue**: [#4811](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4811)
**Issue State**: open
**Task ID**: `tech-debt-zero-001`
**Last synced**: 2026-05-30

## Текущие статусы issue (GitHub)

| Issue | State | Ключевой сигнал |
| --- | --- | --- |
| [#4812](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4812) | open | runtime_builders duplicate clusters: `11` |
| [#4813](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4813) | open | application/core duplicates: `8` |
| [#4814](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4814) | open | bootstrap/runtime duplicates: `5` |
| [#4815](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4815) | open | control_plane duplicate clusters: `15` |
| [#4816](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4816) | open | ratchet families: `4` (`private` 1/0/1/3, `public` 7/12/11/2) |
| [#4817](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4817) | open | compatibility_test_file_max: `56` |
| [#4818](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4818) | open | configs/contracts drift: `31`/`448` |
| [#4819](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4819) | closed | closeout evidence: zero `alias_emitters` |
| [#4820](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4820) | open | dead-code triage: `19` entries (`uncertain` 0) |
| [#4821](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4821) | open | migration_supported alias windows: no entries in registry |

## TL;DR (до 10)

1. Базовая архитектурная инвариантность на уровне слоёв подтверждена (`Layer policy violations = 0`) в `docs/02-architecture/generated/module-dependency-map.md:11` и в `tests/architecture/test_domain_no_infrastructure_dependencies.py`.
2. Техдолг сейчас структурирован как управляемый: `14` sanctioned compatibility entrypoints, `15` twin-пар модулей и `39` дубликатных кластеров (`reports/quality/compatibility-importer-census.md:1`, `reports/quality/compatibility-importer-census.md:13`, `reports/quality/hotspot-duplication-baseline.md:7`).
3. Удалённые legacy-совместимые модули зафиксированы и подтверждены как несуществующие + без импортов (`source_importers=0`, `test_importers=0`) в `reports/quality/compatibility-importer-census.md`.
4. В конфигурационной/контрактной области зафиксирован высокий drift: `31` конфигов, `448` уникальных параметров с разночтениями (`docs/config-discrepancies-report.md:3-31`).
5. `config_compatibility_registry` и `compatibility_facade_inventory` действуют, но зафиксированы постоянные и временные compatibility debt с no-growth политиками (`configs/quality/config_compatibility_registry.yaml`, `configs/quality/compatibility_facade_inventory.yaml`, `configs/quality/compatibility_twin_module_ratchet.yaml`).
6. Compatibility-слой для наблюдаемости очищен по алиасу `checkpoint_saved_at_epoch_seconds`: `alias_emitters` и `compatibility_alias_candidates` теперь пусты в `reports/observability/runtime_cardinality_inventory.json`.
7. DQ/idempotency риски формально контролируются: проверка sink idempotency и контрактов в `tests/architecture/test_pipeline_config_idempotency_contract.py` и `configs/quality/determinism_identity_policy.yaml`.
8. Test-debt контролируется, но есть оставшийся целевой бюджет совместимости: `compatibility_test_file_max=56` (`configs/quality/test_governance_audit.yaml:60-67`).
9. Runtime/CLI split технически соблюдается тестами (`tests/architecture/test_bootstrap_layer_boundaries.py:23-77`), но это не убирает дублирование runtime/CLI фасадов и owner-контуров (`tests/architecture/test_bootstrap_layer_boundaries.py:172-210`).
10. Необходимо перейти от «managed debt» к «zero non-sanctioned debt»: исключить все несогласованные shim/legacy и сделать ratchet-параметры fail-fast.

## Карта техдолга по слоям

| Слой | Артефакты | Тип долга | Состояние | Доказательство |
| --- | --- | --- | --- | --- |
| Domain | `src/bioetl/domain` | Архитектурное соответствие | Без нарушений зависимости (`layer policy violations = 0`) | `docs/02-architecture/generated/module-dependency-map.md:11` |
| Domain | Конфигурационные compatibility-алиасы (`source.*`) | Config compatibility debt | Ограничение и burn-down есть, но сохраняются aliases | `configs/quality/config_compatibility_registry.yaml`, `tests/architecture/test_config_compatibility_registry.py:1-40` |
| Application | Дубликаты `application/core` | Duplication | `8` кластеров | `reports/quality/hotspot-duplication-baseline.md:7-20`, `reports/quality/hotspot-duplication-baseline.md:27-46` |
| Application | `application/services/control_plane` | Duplication + historical compatibility seams | `15` кластеров, продолжает использовать новые фабричные/owner разделения | `reports/quality/hotspot-duplication-baseline.md:39-55`, `reports/quality/hotspot-duplication-baseline.md:73-97` |
| Application | Проверка dead code / zero-import catalog | Dead code / uncertain retention | `43` кандидата, `19` triaged, `0` unresolved | `reports/quality/dead-code-inventory.md:3-18`, `reports/quality/dead-code-inventory.md:22-39` |
| Composition | `composition/bootstrap/runtime` дубликаты | Duplication | `5` кластеров | `reports/quality/hotspot-duplication-baseline.md:33-42`, `reports/quality/hotspot-duplication-baseline.md:60-90` |
| Composition | `composition/runtime_builders` | Duplication + compatibility-слой | `11` кластеров + `__getattr__` aliasing | `reports/quality/hotspot-duplication-baseline.md:74-85`, `src/bioetl/composition/runtime_builders/__init__.py:26-49` |
| Composition | `composition/entrypoints|health_api|maintenance_api` | Compatibility debt | Retained public facades с ростом first-party callers как blocking метрика | `configs/quality/compatibility_facade_inventory.yaml:8-33`, `configs/quality/compatibility_facade_inventory.yaml:245-323` |
| Interfaces | `interfaces/cli/commands/*` | Compatibility seams (legacy wrappers / public entrypoints) | `7` CLI entrypoint фасадов с growth policy | `configs/quality/compatibility_facade_inventory.yaml:13-33`, `tests/architecture/test_bootstrap_layer_boundaries.py:189-210` |
| Infrastructure | `infrastructure/config/__init__.py` | Compatibility facade + root-facade import governance | `tracked_public_entrypoint_burden` + `Config-API` root policy | `configs/quality/compatibility_facade_inventory.yaml:240-260`, `configs/quality/compatibility_twin_module_ratchet.yaml:1-200` |

## Карта зависимости долга

| Долговой артефакт | Текущие потребители | Почему это debt | Риск удаления |
| --- | --- | --- | --- |
| `src/bioetl/composition/bootstrap/cli/*` | `src/bioetl/composition/bootstrap/runtime/*` (ограниченно), `tests/architecture/test_bootstrap_layer_boundaries.py` | Legacy split for admin/admin-like entrypoints; sanctioned as CLI contract | Высокий: внешний CLI/API стабильность требует staged retirement |
| `src/bioetl/interfaces/cli/commands/run.py` и др. | Прямые src импортеры: `1..7` (по census), тестовые импортеры `0..5` | Санкционированный public command seam | Низкий технический риск, высокий процессный (breaking change window) |
| `src/bioetl/composition/entrypoints.py` | `tests/unit/composition/*` + ограниченные src точки | Закрывает приватные _pipeline_execution/_resource/_services | Риск: некорректное изменение `__all__/lazy exports` приведёт к регрессу CLI/обработки ресурсов |
| `src/bioetl/application/core/*` vs `src/bioetl/application/services/control_plane/*` twins | Twin-импортеры по `compatibility-importer-census` | Остаточные приватные пути в twin-семействах | Риск: раннее удаление может разорвать owner-модули без миграции |
| `src/bioetl/infrastructure/config/_legacy_normalizers` -> public API | `source_normalizers`, `pipeline_payload_normalization` | Совместимость normalized aliases vs канонические поля | Риск: изменение поведения исторических внешних конфигов |

## Compatibility debt анализ (критично)

### 1) Alias / shim / façade modules

- `src/bioetl/composition/runtime_builders/__init__.py` использует `__getattr__` lazy aliasing для `_input_snapshot_resolution` (`src/bioetl/composition/runtime_builders/__init__.py:1-42`).
- `src/bioetl/composition/__init__.py` держит `_LAZY_MODULE_EXPORTS` / `_LAZY_ATTR_EXPORTS` как управляемый пакетный proxy (`src/bioetl/composition/__init__.py:20-44`, `src/bioetl/composition/__init__.py:46-88`).
- `src/bioetl/composition/bootstrap/__init__.py` — lazy-кеширующая фасадная пересборка bootstrap API (`src/bioetl/composition/bootstrap/__init__.py:1-62`, `src/bioetl/composition/bootstrap/__init__.py:66-108`).
- `src/bioetl/composition/factories/datasource/data_source_factory.py` и `src/bioetl/composition/bootstrap/runtime/_composite_config_runtime_compat.py` остаются явными compatibility helpers для load/config контрактов.

Что делать:
- Keep: stable public API, где требуется внешний контракт (например `run`, `entrypoints`, `bootstrap_*`).
- Remove/inline: compatibility wrappers в тестовых/внутренних цепочках, если owner-API уже принят и покрыт тестами.
- Риск: регрессия контракта для CLI и bootstrap consumers.

### 2) Legacy shim / alias modules and removed seams

- Удалённые shim/legacy модули подтверждены как absent: `bioetl.application.services.checkpoint_compatibility_service_v2`, `bioetl.application.services.control_plane.workflow_execution_service`, `bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter`, и др. (`tests/architecture/test_compatibility_freeze_guards.py:1638-1653`, `tests/architecture/test_compatibility_importer_census_governance.py:57-95`).
- Контроль удалений дополняется списком в `compatibility_importer_census` (`reports/quality/compatibility-importer-census.md:73-103`) и frozen-governance проверками.

### 3) Runtime/CLI split duplicates

- Структурная граница зафиксирована: runtime не должен импортировать cli (`tests/architecture/test_bootstrap_layer_boundaries.py:23-50`) и имеет split на `assembly|cli|runtime` (`tests/architecture/test_bootstrap_layer_boundaries.py:52-77`).
- Дублирование фактов: и CLI, и runtime имеют свои фасады; это intentional seam до этапа consolidation owner modules.
- Риск: удаление без полной миграции вызовет нарушения CLI/administrative workflows.

## Приоритизированный backlog

| Priority | Тип долга | Артефакт | Действие | Риск | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Duplicate clusters | `src/bioetl/composition/runtime_builders` (`11`) | Свести к 0 по семейным hotspot с owner-адресацией и удалением повторных helper-копий | Регрессии сборки раннера/фильтров | L |
| P0 | Duplicate clusters | `src/bioetl/application/core` (`8`) | Убрать дубляжи в helper wiring и migration-логике | Риск изменения DQ/контуров контроля | M |
| P0 | Duplicate clusters | `src/bioetl/composition/bootstrap/runtime` (`5`) | Консолидировать паритетные runtime-support helpers | Риск в bootstrap-конфигурации observability | M |
| P0 | Duplicate clusters | `src/bioetl/application/services/control_plane` (`15`) | Продолжить разметку/консолидацию diagnostic/replay helpers после финализации ссылок | Поведение трассировки и диагностик | L |
| P1 | Compatibility debt | `configs/quality/compatibility_twin_module_ratchet.yaml` | Зафиксировать/снять private-import tails в 4 ratchet families (или подтвердить устойчивый owner-модуль) | Может раскрыть несвязанные пути импорта в проде | M |
| P1 | Test debt | `configs/quality/test_governance_audit.yaml` | Оценить и снизить `compatibility_test_file_max` от 56 к управляемому минимуму по миграциям | Рост регрессионных false-positive при очистке legacy тестов | M |
| P1 | Config drift | `docs/config-discrepancies-report.md` | Свести drift к нулю между config и контрактным слоем: унификация схем, `contract_ref`, alias maps | Высокий риск изменения поведения при массовой миграции сущностей | L-M |
| P2 | Observability compatibility alias | `reports/observability/runtime_cardinality_inventory.json` | Убрать alias emitter `checkpoint_saved_at_epoch_seconds` или мигрировать в non-runtime semantic channel | Потеря обратной совместимости dashboard/alert правил | M |
| P2 | Dead code | `reports/quality/dead-code-inventory.md` | Разделить `retain_*` с явным owner: либо удалить, либо закрыть как explicit-permanent with rationale | Возможная потеря неиспользуемых, но «тёплых» entrypoints | M |
| P2 | Config registry governance | `configs/quality/config_compatibility_registry.yaml` | Снизить migration-supported aliases и закрыть expired policy окна до нуля при наличии полного migration plan | Риск неочевидной обратной совместимости для старых конфигов | M |

## Дорожная карта

### Phase 1 — Visibility (1–2 недели)

1. Закрыть baseline: обновить и зафиксировать `reports/quality/hotspot-duplication-baseline.md`, `reports/quality/compatibility-importer-census.md`, `configs/quality/debt_scorecard.yaml`, `configs/quality/observability_metric_governance.yaml`, `reports/quality/test-governance`-артефакты.
2. Сформировать dependency map по каждому compatibility-узлу: «какой фасад кем используется» для 14 entrypoints и 4 ratchet twin family.
3. Разделить задачи по ownership: composition bootstrap/runtime, control-plane, application/core, infra-config.
4. [incomplete] Нужен дополнительный inventory for прямых зависимостей `pipeline <-> contract <-> config` на уровне импортов runtime-модулей (не только summary-отчёты).

### Phase 2 — Isolation (2–4 недели)

1. Ввести fail-fast для новых импортеров из compatibility entrypoints во всех non-root owners (`tracked_public_entrypoint_burden` enforce).
2. Расширить ratchet for `compatibility_twin_module_ratchet` в no-growth с обязательным подтверждением canonical owner в PR чек‑листах.
3. Зафиксировать правила для `lazy`/`__getattr__` фасадов: только объявленные и с тестом owner-path.

### Phase 3 — Removal (4–8 недель)

1. Удалить/консолидировать топ-7 duplicate cluster families по приоритету (runtime_builders, bootstrap/runtime, application/core, control_plane).
2. Перевести `config_compatibility_registry` migration aliases в explicit permanent alias или убрать при подтверждённых migration tests.
3. Разблокировать dead-code catalog: убрать кандидаты без owner-обоснования, закрыть `retain_*` решения в архитектурно-владельческих модулях.

### Phase 4 — Enforcement (до конца квартала)

1. Перевести ключевые метрики в fail-fast с нулевыми целями для несанкционированных классов:
  duplication per family (`configs/quality/debt_scorecard.yaml`), compatibility importer growth (`configs/quality/compatibility_twin_module_ratchet.yaml`, `configs/quality/compatibility_facade_inventory.yaml`), config-catalog drift evidence (`docs/config-discrepancies-report.md` + `scripts/schema check-invariants`)
2. Добавить explicit gate в CI на отсутствие [incomplete] pipeline/config/contracts edge drift.
3. Завести обязательную еженедельную проверку debt-map + approve ticket для любых изменений в compatibility/API фасадах.

## Риски и trade-offs

1) Удаление/свёртка compatibility может нарушить внешние интеграции, если не будет external break-plan. Это ограничивается только теми entrypoints, которые имеют `external_breaking_change_required=true` и уже классифицированы как stable API (`configs/quality/compatibility_facade_inventory.yaml:72-86`, `configs/quality/compatibility_facade_inventory.yaml:97-111`).
2) Aggressive consolidation дубликатов в control-plane и bootstrap может временно увеличить регрессионные пути и уплотнить blast-radius для DQ/observability.
3) Config drift cleanup несёт высокий semantic-риск: массовая нормализация `configs/*` и контрактов может изменить replay/ID-поведение без дополнительной фиксации в `determinism_identity_policy`.
4) Часть debt в observability (alias metric) имеет явное диагностическое значение для dashboards; чистка должна сопровождаться migration dashboard alerts и backfill.

## Enforcement (что должно быть в CI)

- Уже действуют: `scripts.engineering.qa report_observability_metric_inventory --check --json` и архитектурные guards в `test_bootstrap_layer_boundaries`, `test_compatibility_importer_census_governance`, `test_compatibility_freeze_guards`, `test_config_compatibility_registry`, `test_pipeline_config_idempotency_contract` (`.github/workflows/tests.yml:236-280`, `.github/workflows/tests.yml:342-375`, `tests/architecture/*`).
- Требуется добавить/усилить: gate на снижение/заморозку `compatibility_test_file_max` (phase-based owner review), CI-проверка `compatibility-importer-census.md` и `dead-code-inventory` как merge blocker при росте critical rows, отдельный gate по контролю dependency map для config↔contracts pipeline (см. [incomplete] в Phase 1)
