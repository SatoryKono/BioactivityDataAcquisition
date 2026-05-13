______________________________________________________________________

Version: 0.1.0
Status: Draft
Class: working-document
Owner: BioETL Team
Last updated: '2026-05-13'

______________________________________________________________________

# План миграции: silver_filters → gold_filters (вариант D — гибрид)

## Краткое содержание

**Цель:** Сузить scope `silver_filters` до структурной целостности (`required_fields`,
`exclude_if_present`); все semantic-правила (`columns`, `ranges`, `list_lengths`,
`list_contains`) консолидировать в `gold_filters`.

**Связанные документы:**

- `docs/filters/ADR-048-silver-filters-structural-scope.md` — обоснование решения
- `scripts/data_quality/inventory_silver_filters_migration.py` — анализатор конфигов
- `docs/filters/inventory-baseline.md` — baseline отчёт
- `docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md` — текущая базовая ADR (amended)

## Ключевые открытия из анализа кода

1. **silver_filters и gold_filters часто дублируются в entity configs** (например, в
   `activity.yaml` `columns` совпадают, `ranges` пересекаются)
1. **21 entity** содержит секцию `silver_filters`
1. **`required_fields` в Silver vs Gold имеют разную семантику:** в Silver — структурные
   (25+ полей), в Gold — бизнес-критичные (4-6 полей)
1. **`exclude_if_present` присутствует только в Silver** (для `data_validity_comment` и др.)

## Целевая архитектура

```text
silver_filters: { required_fields, exclude_if_present }       <- structural integrity
gold_filters:   { required_fields, columns, ranges,           <- business filters
                  list_lengths, list_contains,
                  exclude_if_present }
```

**Принцип:** Silver — "запись должна быть структурно полной". Gold — "запись должна
удовлетворять бизнес-критериям".

## Найденные ошибки в первоначальной (наивной) реализации миграции

| Категория       | Описание                                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Mechanism       | `BaseTransformer.should_write_silver()` существует, но **не вызывается в runtime** — фактически работает `apply_silver_filter()` из `_base_transformer_structural_support.py`, бросающий `FilteredOutError`. |
| Optionality     | `silver_filters.required_fields` используется `ConfigSurfaceOptionalityResolver` для построения policy. Удаление сломает optionality. |
| Shadow metric   | `bioetl_structural_policy_shadow_comparisons_total` опирается на `silver_filters` для shadow comparison со structural policy. |
| Pre-silver path | Существует отдельный `_apply_pre_silver_filter` в `pre_silver_adapter_mixin.py`, который также применяет silver_filters. |
| Semantics       | silver_filters применяются на `SilverRecord` (с JSON-полями), gold_filters — на `GoldRecord` (после `transform_for_gold`, без JSON-полей и с применением `rename_map`). |
| Observability   | Существуют отдельный Grafana dashboard `bioetl-silver-reject-explorer.json`, Prometheus rules, CLI-команда `--silver-filter-only`, error_code `FILTERED_OUT_SILVER`, metric `silver_filter_rejects`. |
| Tests           | 35 тестовых файлов содержат проверки `silver_filter` поведения.                                                          |
| Composite       | `composite_config.py` явно отклоняет composite-local `gold_filters` — требует отдельной обработки.                       |

## Фазы

### Фаза 0: Подготовительные артефакты

#### 0.1. ADR-048 (draft)

`docs/filters/ADR-048-silver-filters-structural-scope.md` — обоснование сужения scope
`silver_filters`. Amends ADR-028.

#### 0.2. Inventory script

`scripts/data_quality/inventory_silver_filters_migration.py`:

- Для каждого entity вычислить per-rule план миграции:
  - **Keep in silver** — `required_fields`, `exclude_if_present`
  - **Move to gold** — `columns`, `ranges`, `list_lengths`, `list_contains`
  - **Detect duplicates** — правила, уже совпадающие с `gold_filters` (объединить, не дублировать)
  - **Detect conflicts** — semantic mismatch
- Output: `docs/filters/inventory-baseline.{csv,json,md}`

#### 0.3. Baseline measurements

Зафиксировать ДО изменений в `docs/filters/baseline-measurements.json`:

- E2E прогон представительной выборки (5 entities): rejection rates по слоям
- Counts records через каждый слой (Bronze → Silver → Gold)
- Top reject reasons для каждого entity
- Performance Silver writes (Delta version, write duration)

### Фаза 1: Runtime identity + domain compatibility

#### 1.1. SilverFilterConfig

`src/bioetl/domain/filtering/silver_config.py`:

Минимально инвазивный путь: оставить `SilverFilterConfig: BaseFilterConfig` без
domain-level warnings. Сужение Silver до structural происходит при конвертации
infrastructure schema → domain config. Это сохраняет чистоту domain слоя и не
тащит migration/runtime concerns в `bioetl.domain`.

#### 1.2. RuntimeConfig / execution identity

Добавить явное поле `silver_filter_compatibility_mode`:

- `structural_only_auto_promote` — canonical runtime mode; semantic Silver rules поднимаются в Gold

Поле должно попадать в effective config, run manifest, execution fingerprint и
checkpoint compatibility payload, иначе structural-only behavior не будет
детерминированно зафиксирован в replay/control-plane surfaces.

### Фаза 2: Infrastructure layer

#### 2.1. Pydantic schemas

`src/bioetl/infrastructure/schemas/filter_config.py`:

```python
class SilverFiltersFileConfig(BaseModel):
    required_fields: list[str] = Field(default_factory=list)
    exclude_if_present: list[str] = Field(default_factory=list)
    # Legacy semantic fields are accepted only for boundary compatibility.
    columns: dict[str, list] | None = Field(default=None, deprecated=True)
    ranges: dict[str, dict] | None = Field(default=None, deprecated=True)
    list_lengths: dict[str, dict] | None = Field(default=None, deprecated=True)
    list_contains: dict[str, dict] | None = Field(default=None, deprecated=True)
```

`to_domain()`: возвращает `SilverFilterConfig` только с structural полями.

#### 2.2. Filter config loader

`src/bioetl/infrastructure/config/filter_config_loader.py`:

- В `load()` и `load_as_dict()` после merge: auto-promotion semantic полей
  `silver_filters` → `gold_filters`
- При конфликте gold выигрывает: существующее gold-правило не перезаписывается.
- Cache key включает resolved compatibility mode, чтобы rollback env не
  использовал stale normalized config.

#### 2.3. Pipeline config schema

`src/bioetl/infrastructure/schemas/pipeline_config.py:193` — тип `silver_filters` изменить
с `GoldFiltersConfig` на новый `SilverFiltersConfig` (сужающий).

#### 2.4. CI invariants

`tests/architecture/test_silver_filter_boundary_inventory.py`:

- Committed `docs/filters/inventory-baseline.{csv,json,md}` MUST match
  `scripts/data_quality/inventory_silver_filters_migration.py`.
- Safe-first-wave candidates MUST remain explicitly justified when empty.
- После YAML rewrite window добавить отдельный hard-fail invariant:
  `silver_filters` MUST NOT contain `columns`/`ranges`/`list_lengths`/`list_contains`.

### Фаза 3: Application / checkpoint / control-plane identity

Нужны точечные изменения, потому что runtime mode влияет на reproducibility:

- `apply_silver_filter()` — оставить поведение, но считать default Silver
  structural-only после schema conversion.
- `_collect_silver_required_fields()` — без изменений.
- Shadow-comparison labels сменить с semantic на structural/silver-filter
  labels.
- Run manifest canonical execution identity должен включать
  `silver_filter_compatibility_mode`.
- Checkpoint metadata/fallback identity должен включать
  `silver_filter_compatibility_mode`, иначе strict resume не увидит drift между
  старым и новым execution identity payload.

### Фаза 4: Configs migration

#### 4.1. Авто-скрипт миграции

`scripts/migrations/migrate_silver_to_gold_filters.py`:

Алгоритм для каждого `configs/entities/*/*.yaml`:

1. Прочитать `filters.silver_filters` и `filters.gold_filters`
1. Для каждого semantic правила в silver_filters:
   - Если правило **полностью совпадает** с gold_filters → удалить из silver
   - Если правило **отсутствует** в gold_filters → переместить из silver в gold
   - Если правило **частично совпадает** → создать `conflicts/{provider}_{entity}.diff` для review
1. Сохранить обновлённый YAML с комментариями (`# migrated from silver_filters per ADR-048`)

Output: `docs/filters/migration-diff-{date}.md` с per-entity diff.

#### 4.2. Manual review для conflicts

Per-entity ревью с владельцем provider/entity.

#### 4.3. Base layer

`configs/base/pipeline.yaml`:

- `filter_defaults.silver_filters`: только `required_fields: []`, `exclude_if_present: []`
- `filter_defaults.gold_filters`: все остальные поля

#### 4.4. JSON schema

`configs/_schema/pipeline.json` — обновить scope `silver_filters`.

### Фаза 5: Observability

#### 5.1. Metric semantics

`silver_filter_rejects` остаётся, но **семантика сужается** — теперь structural rejects.

#### 5.2. Grafana

`grafana/dashboards/bioetl-silver-reject-explorer.json` — title и descriptions обновить
на "Silver Structural Reject Explorer".

#### 5.3. CLI rendering

- `src/bioetl/interfaces/cli/commands/domains/quarantine/rendering.py`
- `src/bioetl/interfaces/cli/commands/domains/diagnostics/rendering.py`

Обновить текст: "Silver Filter Rejects" → "Silver Structural Rejects".

### Фаза 6: Tests

| File | Изменение |
| ---- | --------- |
| `tests/architecture/test_silver_filter_boundary_inventory.py` | Add committed baseline drift check and later harden semantic Silver ban |
| `tests/unit/infrastructure/config/test_filter_config_loader.py` | Add auto-promotion tests |
| `tests/unit/infrastructure/schemas/test_filter_config.py` | Update SilverFiltersFileConfig scope |
| `tests/unit/infrastructure/test_config.py` | Verify inline pipeline config auto-promotion |
| `tests/unit/domain/normalization/test_fingerprints.py` | Verify silver mode changes execution fingerprint |
| `tests/unit/application/core/test_optionality.py` | No change (still uses silver_required_fields) |
| `tests/integration/test_grafana_silver_reject_config.py` | Update dashboard descriptions |
| `tests/integration/test_prometheus_rules_config.py` | Update annotations |
| `tests/integration/test_silver_to_gold_migration_parity.py` (planned) | Pre/post parity для каждого entity |

### Фаза 7: Documentation

| File | Изменение |
| ---- | --------- |
| `docs/02-architecture/decisions/ADR-048-...` | Создан в Фазе 0 (move from `docs/filters/` after acceptance) |
| `docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md` | Footer-ссылка на ADR-048, обновить таблицу Filter Types |
| `docs/04-reference/providers/{provider}/*.md` | Раздельные таблицы для silver structural и gold semantic |
| `docs/05-operations/runbooks/quarantine-management.md` | Обновить раздел Silver filter rejects |
| `docs/05-operations/01-monitoring-guide.md` | Обновить Silver Reject Explorer описание |
| `docs/plans/silver-filter-rejects-observability-plan.md` | Footer: "scope narrowed per ADR-048" |
| `docs/00-project/RULES.md` | §2.1.2 / §2.1.3 — уточнение responsibility scope |

### Фаза 8: Rollout

#### Phased rollout

1. **PR 1** — Runtime identity + Infrastructure compatibility changes
   (auto-promotion, structural-only Silver domain conversion)
1. **PR 2** — Inventory baseline enforcement + representative baseline measurement
1. **PRs 3-N** — Configs migration (per-provider, smaller PRs)
1. **PR N+1** — Tests + documentation
1. **PR N+2** — Observability rename/relabel
1. **Future release** — Remove deprecation warnings, harden CI invariant (warning → error)

#### Rollback triggers

- E2E parity test fails → rollback PR 1
- Performance Silver write degradation > 20% → investigate
- Quarantine analytics regression → adjust observability

## Риски

| Риск | Вероятность | Влияние | Митигация |
| ---- | ----------- | ------- | --------- |
| Semantic conflicts в configs | Средняя | Среднее | Manual review через 4.2 + per-entity diff |
| Тесты под новую структуру | Средняя | Низкое | Поэтапный rollout, auto-promotion period |
| Документация divergence | Средняя | Низкое | Documentation в том же PR что и code |
| Misinterpretation `silver_filter_rejects` метрики | Низкая | Низкое | Release notes + rename в Grafana |
| Production failure из-за auto-promotion bug | Низкая | Высокое | Feature flag + integration parity test |
| Architecture test поломки | Низкая | Низкое | Update boundary inventory в Фазе 6 |

## Оценка трудозатрат

| Фаза | Часы | Кто |
| ---- | ---- | --- |
| 0 — ADR + inventory script + baseline | 8-12 | Architect + Senior Engineer |
| 1 — Domain layer | 4-6 | Senior Engineer |
| 2 — Infrastructure layer | 12-16 | Senior Engineer |
| 3 — Application layer (validation) | 4-6 | Senior Engineer |
| 4 — Configs migration (auto + manual review) | 8-16 | Engineer + per-entity owners |
| 5 — Observability rename | 4-6 | Engineer |
| 6 — Tests | 16-24 | Engineer |
| 7 — Documentation | 8-12 | Engineer + Tech Writer |
| 8 — Rollout | 6-10 | Engineer + DevOps |
| **Итого** | **70-108 часов** | (~2-3 недели) |

## Acceptance criteria

- [ ] ADR-048 accepted и moved to `docs/02-architecture/decisions/`
- [ ] Inventory baseline зафиксирован
- [ ] Per-entity migration diff prepared and reviewed
- [ ] All 21 entity configs migrated
- [ ] Tests updated, integration parity test added
- [ ] Observability обновлена
- [ ] Documentation updated
- [ ] Feature flag tested
- [ ] No regression в E2E

## Changelog

| Date       | Author          | Change                                               |
| ---------- | --------------- | ---------------------------------------------------- |
| 2026-05-12 | BioETL Team     | Initial draft of variant D (hybrid) migration plan   |
