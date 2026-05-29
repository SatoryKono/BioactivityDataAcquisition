# Drive BioETL technical debt to zero

**Status**: proposed
**Priority**: P0
**Labels**: `architecture`, `tech-debt`, `governance`, `epic`
**GitHub Issue**: `TBD`
**Issue State**: draft
**Last synced**: 2026-05-29

## TL;DR

1. Layering is mostly clean (`0` policy violations), but compatibility debt and duplicate hotspots are still bounded and non-zero.
2. `14` sanctioned public compatibility entrypoints remain; first-party burden through them is still tracked as `retained_public_entrypoint_burden`.
3. `15` public/private twin-module pairs remain and `4` are ratcheted twins requiring ongoing no-growth enforcement.
4. Duplication hotspots still sit at: `application/services/control_plane=15`, `composition/runtime_builders=11`, `composition/bootstrap/runtime=5`, `application/core=8`.
5. Zero-import debt inventory is a review surface: `43` candidates, `19` triaged dispositions.
6. Compatibility test debt budget remains explicit (`compatibility_test_file_max=56`).
7. Observability still reports compatibility alias emitter `checkpoint_saved_at_epoch_seconds`.
8. VCR metadata drift is currently failing drift check for 15 `openalex` health cassettes.
9. Config/contract parameter drift remains substantial (`31` configs, `448` unique parameters) and is mostly covered but requires governance and cleanup discipline.
10. Target-state is clear: collapse/retire compatibility seams, remove duplicate helper clusters, and turn visibility baselines into fail-fast enforcement.

## Карта техдолга по слоям

### Domain

- **State:** no domain layering violations (imports are internally consistent) from generated map.
  - Evidence: `docs/02-architecture/generated/module-dependency-map.md:11`, `docs/02-architecture/generated/module-dependency-map.md:122-125`.
- **Debt classification:** compatibility shape debt exists only as explicit, bounded aliases with review metadata.
  - Evidence: `configs/quality/config_compatibility_registry.yaml:7-29`, `configs/quality/config_compatibility_registry.yaml:36-53`.
- **Open debt workitems:** none that are currently architectural violations; this layer mostly acts as boundary owner for compat contracts and needs ongoing alias drift control.

### Application

- **Compatibility debt:**
  - `14` retained sanctioned public entrypoints; current `retained_public_entrypoint_burden=14`.
    - Evidence: `configs/quality/compatibility_facade_inventory.yaml:12-22`, `:108-110`, `:139-159`.
  - **Compatibility test debt:** `compatibility_test_file_max=56` remains active.
    - Evidence: `configs/quality/test_governance_audit.yaml:60-65`.
- **Duplication debt:**
  - `application/services/control_plane` = `15` duplicate clusters, `application/core` = `8`.
    - Evidence: `reports/quality/hotspot-duplication-baseline.md:15-20`, `:67-75`, `:129-133`.
- **Dead code inventory debt:** `43` zero-import candidates, all currently reviewed with mixed dispositions (`retain_active` + retired).
  - Evidence: `reports/quality/dead-code-inventory.md:3-12`, `:17-38`.

### Infrastructure

- **Config/control-plane compatibility surface debt:** `4` sanctioned public export facades still carry compatibility boundary contracts.
  - Evidence: `reports/quality/compatibility-importer-census.md:13-15`, `:44-45`.
- **Layering checks:** bootstrap split and adapter boundaries are explicitly tested; no reported violations in last run.
  - Evidence: `tests/architecture/test_bootstrap_layer_boundaries.py:23-50`, `:52-74` and related pass in previous architecture sweep.
- **Compat shape/deprecation debt:** compatibility alias policies in `config_compatibility_registry` must remain bounded (`accepted_shape_max=2`, `migration_supported_shape_max=0`).
  - Evidence: `configs/quality/config_compatibility_registry.yaml:15-17`, `:29-30`.

### Composition

- **Duplication debt:**
  - `composition/bootstrap/runtime=5`, `composition/runtime_builders=11` duplicate clusters.
    - Evidence: `reports/quality/hotspot-duplication-baseline.md:16-20`, `:44-60`, `:96-120`.
- **Compatibility entrypoint debt:** composition public seams remain sanctioned entrypoints with bounded exports + lazy table.
  - Evidence: `configs/quality/compatibility_facade_inventory.yaml:160-214`.
- **Observed compatibility test debt:** not currently failing, but needs ratchet to zero budgets.
  - Evidence: same as Application compatibility test surface (`...test_governance_audit.yaml:60-65`).

### Interfaces

- **Compatibility / CLI debt:** `7` CLI public compatibility command entrypoints retained as public seams.
  - Evidence: `configs/quality/compatibility_facade_inventory.yaml:13-33`.
- **Risk debt:** dual-layer CLI/runtime bootstrap compatibility requires ongoing first-party caller narrowing.
  - Evidence: `tests/architecture/test_bootstrap_layer_boundaries.py:23-50`, `:206-227`.

## Compatibility debt анализ

### 1) Alias / facade / shim debt

- **Retained public entrypoints (`14`, all sanctioned):**
  - `src/bioetl/interfaces/cli/commands/{run,run_all,run_composite,health,diagnostics,quarantine,maintenance}.py`
  - `src/bioetl/composition/{entrypoints.py,health_api.py,maintenance_api.py}`
  - `src/bioetl/infrastructure/config/__init__.py`
  - `src/bioetl/domain/composite/config.py`
  - `src/bioetl/domain/value_objects/activity_values.py`
  - `src/bioetl/application/composite/merger.py`
  - Evidence: `configs/quality/compatibility_facade_inventory.yaml:13-33`, `:160-214`, `:240-322`, `:335-322`.
- **Why kept:** these are intentional seams, not transition debt (`transition_compat_count=0`).
  - Evidence: `configs/quality/debt_scorecard.yaml:97-107`.

### 2) Twin modules / private compatibility mirrors

- `15` twin pairs are present today, and `4` no-growth families are ratcheted:
  - `application.core.span_helpers`
  - `composition.runtime_builders.run_manifest_support`
  - `domain.normalization.profiles.chembl_policy_registry`
  - `domain.normalization.profiles.chembl_policy_registry_data`
  - Evidence: `reports/quality/compatibility-importer-census.md:73-102`, `configs/quality/compatibility_twin_module_ratchet.yaml:6-50`.
- **Compatibility risk:** remaining twin imports can re-introduce duplicate public/private behavior and ownership drift.

### 3) Removed compatibility surfaces

- `22` legacy removed surfaces confirmed absent.
- `0` removed surfaces with src/test re-importers.
  - Evidence: `reports/quality/compatibility-importer-census.md:5-8`, `:46-70`.
- **Interpretation:** migration succeeded, but remaining sanctioned seams must be narrowed further.

### 4) Lazy exports / alias tables

- Public export facades are tracked and currently clean (no duplicate exports), but lazy aliases still require governance.
  - Evidence: `reports/quality/compatibility-importer-census.md:37-44`.

### 5) Observability compatibility alias

- One compatibility alias emitter still present:
  - `checkpoint_saved_at_epoch_seconds` from `src/bioetl/application/core/lifecycle/checkpoint_manager.py`
  - Evidence: `reports/observability/runtime_cardinality_inventory.json:53-60`, `:192`.

## Приоритизированный backlog

1) **P0 — Закрыть compatibility-заметки в Observability/метриках**
- **Артефакт:** `reports/observability/runtime_cardinality_inventory.json`, `configs/quality/observability_metric_governance.yaml`
- **Действие:** удалить `checkpoint_saved_at_epoch_seconds` из emission path или перевести в non-runtime semantic channel без метрик-алиасов.
- **Риск:** потенциальное временное падение диагностического дашборда `checkpoint_saved_at_epoch_seconds`.
- **Effort:** M

2) **P0 — Устранить 4 ratcheted twin-семейства до нулевых private-imports, где возможно**
- **Артефакт:** `configs/quality/compatibility_twin_module_ratchet.yaml`, `reports/quality/compatibility-importer-census.md`
- **Действие:** закрепить единственный публичный owner-путь для каждой пары, убрать private direct imports за пределами owner modules, перейти в reviewed-baseline/zero для тех, где бизнес-потенциал исчерпан.
- **Риск:** затраты на адаптацию тестов/вызовов.
- **Effort:** L

3) **P0 — Привести duplicate-hotspots к нулю по плану семейства**
- **Артефакт:** `configs/quality/debt_scorecard.yaml`, `reports/quality/hotspot-duplication-baseline.md`
- **Действие:** поочередно убрать 15, 11, 5, 8 кластеров в control_plane/runtime_builders/bootstrap/runtime/core.
- **Риск:** регрессии determinism/replay без полной тест-поддержки.
- **Effort:** L

4) **P1 — Пересмотреть zero-import debt**
- **Артефакт:** `reports/quality/dead-code-inventory.md`
- **Действие:** конвертировать triage-позиции `retain_*` в `removed` или `explicit permanent` с owner-обоснованием или подтвердить неизменность как bounded API-узлов.
- **Риск:** неочевидный runtime usage через динамическую загрузку/тест-плагины.
- **Effort:** M

5) **P1 — Снизить compat test debt budget**
- **Артефакт:** `configs/quality/test_governance_audit.yaml`
- **Действие:** убрать legacy compatibility test surface до `compatibility_test_file_max=0` через миграцию вызовов в новый фасад и очистку метаданных покрытия.
- **Риск:** повышение объема тест-рефакторинга в нескольких пакетах.
- **Effort:** M

6) **P1 — Закрыть дрейф VCR-фактуры**
- **Артефакт:** `tests/fixtures/vcr/openalex`, `tests/architecture/test_vcr_metadata_inventory.py`, `scripts/engineering/qa/vcr`
- **Действие:** обновить/пересоздать 15 `openalex` `_meta.yaml` cassette fingerprints или зафиксировать намеренную деградацию.
- **Риск:** изменения ответов провайдеров меняют стабильность контрактов.
- **Effort:** M

7) **P2 — Довести контрактный drift к управляемому состоянию**
- **Артефакт:** `docs/config-discrepancies-report.md`, `configs/base/bronze_fixture_gaps.yaml`
- **Действие:** зафиксировать обязательные инварианты для семейства (entity/contract/pipeline/filters/composite) и снизить необъяснимые расхождения через ADR/issue-driven consolidation.
- **Риск:** большая матрица потребует поэтапного управления, а не «большой залп».
- **Effort:** M/L

## Дорожная карта (Phases)

### Phase 1 — Visibility (1–2 недели)

- Утвердить baseline и зафризить артефакты:
  - `configs/quality/dead-code-inventory.md`
  - `reports/quality/compatibility-importer-census.md`
  - `reports/quality/hotspot-duplication-baseline.md`
  - `reports/quality/hotspot-duplication-baseline.json`
  - `reports/observability/runtime_cardinality_inventory.json`
- Проставить owner/контракт/условие удаления для каждого retained debt item.
- Обновить acceptance map в `configs/quality/debt_scorecard.yaml` и `configs/quality/compatibility_facade_inventory.yaml`.

### Phase 2 — Isolation (2–4 недели)

- Ввести/усилить архитектурные запреты на появление новых private twin importers вне sanctioned owner-модулей.
- Ограничить first-party imports через sanctioned public seams.
- Отключить рост compatibility-тестовых debt-файлов и alias-таблиц без review.
- Добавить контроль новых VCR метаданных (`checksum/shadow`) в CI pre-check.

### Phase 3 — Removal (4–8 недель)

- Удалить/консолидировать совместимые shim-пути по очереди:
  - `checkpoint_saved_at_epoch_seconds` (runtime event-label alias)
  - private twin import tails (где owner path стабилен)
  - duplicate clusters families (control_plane/runtime_builders/bootstrap_runtime/core)
- Выравнять ownership для `application/services/control_plane` и `composition/runtime_builders`.

### Phase 4 — Enforcement (до конца квартала)

- Перевести выбранные visibility-budgets в fail-fast gates:
  - `configs/quality/debt_scorecard.yaml` (duplication families)
  - `configs/quality/dead-code-inventory.md` (newly non-removable retained modules)
  - `configs/quality/compatibility_twin_module_ratchet.yaml` (no-growth)
  - `configs/quality/test_governance_audit.yaml` (compatibility debt budget)
- Синхронизировать тестовую карту и архитектурные checks в CI.

## Риски и trade-offs

1) **Стабильность внешних потребителей.** Часть retained entrypoints может быть использована извне; удаление требует внешнего аудита и поэтапного deprecation window.
2) **Регрессионый риск при удалении duplicate-кластера.** Без полного перекрытия тестами по контрольной плоскости и replay можно скрыть semantic drift.
3) **Непредсказуемость VCR provider drift.** Обновление cassette metadata для OpenAlex может приводить к «источниковой» изменчивости и маскировать реальные изменения парсера.
4) **Административная стоимость:** перевод compatibility debt в fail-fast может временно повысить число артефактов для ручного решения и замедлить CI на старте.

## Acceptance

- [ ] `configs/quality/debt_scorecard.yaml`: `retained_public_entrypoint_burden` remains governed and no transition compatibility debt.
- [ ] `reports/quality/compatibility-importer-census.md`: `tracked_twin_family_count` reduced to only sanctioned residuals; private-import growth blocked per ratchet.
- [ ] `reports/quality/hotspot-duplication-baseline.json`: duplicate-cluster counts reduced toward 0 for 4 active families.
- [ ] `configs/quality/test_governance_audit.yaml`: `compatibility_test_file_max` reduced to 0.
- [ ] `reports/observability/runtime_cardinality_inventory.json`: no compatibility alias emitters.
- [ ] `tests/architecture/test_bootstrap_layer_boundaries.py`: pass (runtime/cli split and boundaries).
- [ ] `scripts/engineering/qa/vcr check-metadata-age --max-age-days 90`: pass or explicit waiver issue with owner + review date.

## Evidence (anchor set)

- `docs/02-architecture/generated/module-dependency-map.md`
- `configs/quality/debt_scorecard.yaml`
- `configs/quality/compatibility_facade_inventory.yaml`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/config_compatibility_registry.yaml`
- `configs/quality/test_governance_audit.yaml`
- `docs/config-discrepancies-report.md`
- `reports/quality/compatibility-importer-census.md`
- `reports/quality/dead-code-inventory.md`
- `reports/quality/hotspot-duplication-baseline.md`
- `reports/observability/runtime_cardinality_inventory.json`
