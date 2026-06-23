______________________________________________________________________

Version: 6.1.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Pipeline Configuration Guide

Руководство по настройке конфигурации ETL-пайплайнов в BioETL.

**Версия:** 6.1.0
**Дата обновления:** 2026-04-29

______________________________________________________________________

## Обзор

BioETL использует **YAML-файлы** для конфигурации пайплайнов. Все конфигурации валидируются через **Pydantic** при загрузке, обеспечивая типобезопасность и раннее обнаружение ошибок.

### Ключевые особенности

- **Convention over Configuration (ADR-029):** Пути и ссылки вычисляются автоматически
- **Иерархическое наследование:** Общие defaults загружаются из `configs/base/pipeline.yaml`
- **Иерархические DQ/Filter правила (ADR-027/028):** 3-уровневая иерархия с merge
- **Pydantic валидация:** Схемы проверяются при загрузке
- **Immutable Domain Objects:** Конфиги преобразуются в frozen dataclasses
- **Fixture governance (dual model):** tracked fixture manifest + gap registry

______________________________________________________________________

## Структура директорий

```
configs/
├── base/                         # Глобальные defaults
│   ├── pipeline.yaml            # Общие pipeline/filter defaults
│   ├── quality.yaml             # Общие DQ defaults
│   ├── bronze_fixture_manifest.yaml # Positive fixture inventory (tracked CI samples)
│   └── bronze_fixture_gaps.yaml # Exception registry for missing fixture coverage
├── providers/                    # Provider-level source/quality/filters
│   ├── chembl.yaml
│   ├── crossref.yaml
│   ├── openalex.yaml
│   ├── pubchem.yaml
│   ├── pubmed.yaml
│   ├── semanticscholar.yaml
│   └── uniprot.yaml
├── entities/                     # Unified entity configs
│   ├── chembl/
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── assay_parameters.yaml
│   │   ├── cell_line.yaml
│   │   ├── compound_record.yaml
│   │   ├── molecule.yaml
│   │   ├── protein_class.yaml
│   │   ├── publication.yaml
│   │   ├── publication_similarity.yaml
│   │   ├── publication_term.yaml
│   │   ├── subcellular_fraction.yaml
│   │   ├── target.yaml
│   │   ├── target_component.yaml
│   │   └── tissue.yaml
│   ├── crossref/publication.yaml
│   ├── openalex/publication.yaml
│   ├── pubchem/compound.yaml
│   ├── pubmed/publication.yaml
│   ├── semanticscholar/publication.yaml
│   └── uniprot/{idmapping,protein}.yaml
├── composites/                   # Composite pipeline configs (ADR-026)
│   ├── activity.yaml
│   ├── assay.yaml
│   ├── molecule.yaml
│   ├── publication.yaml
│   ├── target.yaml
│   └── field_groups/publication.yaml
├── quality/                      # Quality policy, debt, source-test governance
│   ├── architecture_metric_exemptions.yaml
│   ├── debt_scorecard.yaml
│   ├── source_test_facade_inventory.yaml
│   ├── source_test_mapping_exceptions.yaml
│   ├── source_test_owner_inventory.yaml
│   └── test_matrix.yaml
├── enums/
│   ├── chembl.yaml
│   └── publication_type_classification.meta.yaml
└── naming_exceptions.yaml
```

### Категории конфигураций

Точный total по YAML-файлам в `configs/` быстро дрейфует по мере добавления
quality/governance assets и composite helpers, поэтому active guide фиксирует
категории, а не ручной глобальный count.

| Категория                     | Описание                                                                           |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| Entity configs (unified)      | Standard ETL pipelines (`configs/entities`)                                        |
| Composite pipeline configs    | Multi-provider pipelines (`configs/composites/*.yaml`)                             |
| Composite field-group configs | Shared field groups (`configs/composites/field_groups`)                            |
| Provider configs              | Source + provider quality/filters (`configs/providers`)                            |
| Base configs                  | Global defaults (`configs/base`)                                                   |
| Quality/governance configs    | Quality policy, debt, source-test, and composite quality files (`configs/quality`) |
| Enum configs                  | Enum and publication-classification assets (`configs/enums`)                       |
| Misc standalone configs       | Naming exceptions and similar top-level config assets                              |

### Section-Level Ownership For Large YAML Files

Unified entity configs and composite configs deliberately keep related runtime
policy in one SSOT file, but ownership is section-level. Do not treat a large
YAML file as a single undifferentiated owner surface.

| Config surface | Section / keys | Architectural owner | Extraction trigger | Regression gate |
| -------------- | -------------- | ------------------- | ------------------ | --------------- |
| `configs/entities/{provider}/{entity}.yaml` | `version`, `provider`, `entity`, `pipeline.*`, `pipeline.sink.*` | pipeline runtime / infrastructure config loading | section starts carrying provider-specific adapter behavior or non-YAML runtime branching | `uv run python -m scripts.schema validate-configs`; `tests/architecture/test_config_validation_surface.py` |
| `configs/entities/{provider}/{entity}.yaml` | `schema.*`, `schema.column_groups`, `schema.{silver,gold}` | schema/domain contract owners | field groups duplicate generated reference data or need cross-provider ownership | config validation plus schema/golden contract tests for the affected provider/entity |
| `configs/entities/{provider}/{entity}.yaml` | `quality.*` | DQ contract owners | inline DQ policy grows beyond entity-local checks or must be shared across providers | DQ config validation, contract tests, and docs drift checks for DQ references |
| `configs/entities/{provider}/{entity}.yaml` | `filters.*`, `input_filter`, `silver_filters`, `gold_filters` | filter-rule owners from ADR-028 | filter behavior needs reusable rule bundles or provider-level inheritance | config validation plus targeted filter-rule tests |
| `configs/entities/{provider}/{entity}.yaml` | migration, canonicalization, system-field policy | architecture/config governance owners | policy applies to more than one entity family or changes manifest/hash identity | config validation plus architecture/governance tests that cover hash and migration semantics |
| `configs/composites/{entity}.yaml` | `composite.seed`, `dependencies`, `enrichers`, join/filter conditions | composite runtime owners | runtime orchestration logic leaks into config comments or requires code branches per provider | composite config loader tests and composite runtime tests |
| `configs/composites/{entity}.yaml` | `merge`, `field_priorities`, `exclude_fields`, `schema.column_groups` | composite schema/merge owners | provider priority or field-order rules duplicate generated references or become shared across composites | composite config validation plus field-order/reference drift checks |
| `configs/composites/{entity}.yaml` | `dq_overrides`, `lineage`, provider lookup/source tracking | DQ/lineage owners | lineage semantics need cross-composite policy or DQ overrides become common rules | `uv run python -m scripts.schema validate-configs` plus lineage/DQ contract tests |

Current policy: keep sections in the YAML SSOT while they are entity-local or
composite-local. Extract to a shared config, generated reference artifact, or
domain-specific config file only when the section becomes cross-entity,
cross-provider, or independently versioned. When extraction happens, update
this matrix, the relevant schema validator, and any generated reference docs in
the same change.

### Fixture Governance: `manifest + gaps`

Для Bronze testability используется dual model:

- `configs/base/bronze_fixture_manifest.yaml` — позитивный реестр
  `tracked_ci_sample` fixtures (канонический CI baseline).
- `configs/base/bronze_fixture_gaps.yaml` — реестр дефицитов и исключений
  для pipeline keys, где tracked fixture пока отсутствует.

Практическое правило:

- pipeline считается покрытым, если есть `tracked_ci_sample` в manifest;
- если tracked fixture отсутствует, должен быть explicit entry в `gaps`;
- для ключей, покрытых `tracked_ci_sample`, gap-запись должна быть закрыта/удалена.
- `tracked_ci_sample` продвигается только из factual Bronze rows:
  local runtime snapshots или replay-backed VCR payload extraction, не synthetic hand-made records.
- bounded CI sample должен оставаться малым и deterministic:
  current floor — не меньше `20` JSONL records на fixture.
- для replay-critical family promotion нужен хотя бы один зафиксированный consumer path:
  integration, replay, или e2e test, который использует эту pipeline family в CI-visible surface.

### Non-ChEMBL Field Governance

Для новых non-ChEMBL полей недостаточно просто добавить колонку в YAML.
Минимальный expected closure path:

- нормализация должна жить в shipped profile-rule surface, а не в ad hoc transformer logic;
- observed inventory и generated normalization matrix должны получить evidence row;
- DQ и Gold/domain contracts должны остаться согласованными с identifier,
  vocabulary, или structured-payload semantics;
- semantic-sensitive JSON payloads должны использовать additive
  `*_raw_json` / `*_canonical_json` sidecars до любого future semantic rewrite.

Практический ориентир: перед merge сверь изменения с
`docs/04-reference/normalization/non-chembl-normalization-overview.md`,
`docs/reports/generated/pipeline_normalization_field_matrix/`, и
`tests/fixtures/normalization/non_chembl_observed_values.yaml`.

______________________________________________________________________

## Unified Entity Config YAML

### Минимальный конфиг

`configs/entities/{provider}/{entity}.yaml` хранит unified-конфиг с секциями.

```yaml
# configs/entities/chembl/activity.yaml
version: "1.0.0"
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  business_primary_keys: [activity_id]
```

### Полная структура конфига

| Секция      | Описание                                     | Обязательно |
| ----------- | -------------------------------------------- | ----------- |
| `version`   | Версия unified-конфига                       | Да          |
| `provider`  | Провайдер                                    | Да          |
| `entity`    | Сущность                                     | Да          |
| `pipeline`  | Runtime-параметры пайплайна                  | Да          |
| `schema`    | Column groups + layer include/exclude policy | Да          |
| `quality`   | DQ-правила для сущности                      | Да          |
| `filters`   | Extraction/silver/gold filters               | Да          |
| `contracts` | PK/merge/hash policy                         | Да          |

### Пример с переопределениями

```yaml
# configs/entities/chembl/activity.yaml
version: "1.0.0"
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  business_primary_keys: [activity_id]
  batch_size: 500
  dq_overrides:
    field-validations:
      - field: standard_value
        type: range
        min: 0
        nullable: true
```

______________________________________________________________________

## Composite Pipelines (ADR-026)

Composite pipelines объединяют данные из нескольких провайдеров в единый датасет.

### Структура Composite конфига

```yaml
# configs/composites/publication.yaml
composite:
  name: composite_publication
  version: "1.1.0"

  seed:
    pipeline: chembl_publication     # Базовый пайплайн (источник ID)

  enrichers:                          # Обогащение из других провайдеров
    - pipeline: crossref_publication
      join_keys: [doi, title]
      required: false
    - pipeline: openalex_publication
      join_keys: [doi, title]
      required: false
    - pipeline: pubmed_publication
      join_keys: [pmid, doi]
      required: false
    - pipeline: semanticscholar_publication
      join_keys: [doi, title]
      required: false

  merge:
    strategy: left_outer               # Сохраняем все seed записи
    conflict_resolution: seed_priority # При конфликте — seed выигрывает
    preserve_all_sources: true         # Храним provider-qualified поля
```

### Доступные Composite Pipelines

| Composite               | Seed                 | Enrichers                                                           | Описание                      |
| ----------------------- | -------------------- | ------------------------------------------------------------------- | ----------------------------- |
| `composite_activity`    | `chembl_activity`    | enrichers                                                           | Обогащённые данные активности |
| `composite_assay`       | `chembl_assay`       | enrichers                                                           | Обогащённые данные анализов   |
| `composite_molecule`    | `chembl_molecule`    | pubchem_compound, enrichers                                         | Обогащённые молекулы          |
| `composite_publication` | `chembl_publication` | crossref, openalex, pubmed, semanticscholar                         | Обогащённые публикации        |
| `composite_target`      | `chembl_target`      | target-component, protein-class, uniprot_idmapping, uniprot_protein | Обогащённые targets           |

### Отличия от Regular Pipelines

| Аспект        | Regular Pipeline                           | Composite Pipeline                                      |
| ------------- | ------------------------------------------ | ------------------------------------------------------- |
| Корневой ключ | `pipeline_name`, `provider`, `entity_type` | `composite:`                                            |
| Source        | Один провайдер + provider source config    | Несколько провайдеров через `enrichers`                 |
| Schema        | `configs/_schema/pipeline.json`            | Отдельная composite schema (ADR-026)                    |
| Пути          | Auto-computed                              | Часть путей задаётся в `merge.output`                   |
| Orchestration | `PipelineRunner` + `{Entity}Transformer`   | `CompositePipelineRunner` (без отдельных трансформеров) |
| Реализация    | `application/pipelines/{provider}/`        | `application/composite/`                                |

> **Архитектурная заметка:** Composite pipelines **не используют** классы трансформеров
> (`*Transformer`). Вместо этого оркестрация выполняется через `CompositePipelineRunner`,
> `EnrichmentCoordinator`, `MergeService` и другие сервисы в `application/composite/`.
> Seed и enricher pipelines запускаются как обычные single-source pipelines,
> а composite layer выполняет агрегацию на уровне Silver-данных.

______________________________________________________________________

## Convention-based Path Resolution (ADR-029)

Пути и file-reference defaults вычисляются автоматически из `provider` и
`entity_type`. Entity pipeline config задаёт `provider` и `entity_type`, после
чего loader:

1. подставляет convention defaults для `dq_config_file` и `filter_config_file`;
1. вычисляет медальонные пути и table names;
1. загружает provider source config из `configs/providers/{provider}.yaml`;
1. merge-ит provider source config с entity-level `source` overrides.

| Поле                 | Auto-computed значение                         | Примечание                                  |
| -------------------- | ---------------------------------------------- | ------------------------------------------- |
| `dq_config_file`     | `../../entities/{provider}/{entity_type}.yaml` | Convention default для entity-level DQ      |
| `filter_config_file` | `../../entities/{provider}/{entity_type}.yaml` | Convention default для entity-level filters |
| `sink.bronze.path`   | `data/output/bronze/{provider}/{entity_type}`  |                                             |
| `sink.silver.path`   | `data/output/silver/{provider}/{entity_type}`  |                                             |
| `sink.gold.path`     | `data/output/gold/{provider}/{entity_type}`    |                                             |
| `silver_table`       | `{provider}_{entity_type}`                     | Если явно не задан                          |
| `gold_table`         | `{provider}_{entity_type}`                     | Если явно не задан                          |

> **Важно:** pipeline config не использует `source-file`. Provider source section
> canonical-но грузится из `configs/providers/{provider}.yaml`, затем merge-ится
> с inline `source:` overrides в entity pipeline config.

### Config Compatibility Registry

Legacy/new-shape compatibility in config loading is bounded by
`configs/quality/config_compatibility_registry.yaml`. The registry lists the
remaining accepted timeout and rate-limit aliases, plus rejected retired forms
such as `source.api`, `source.client`, `source.batch`, and
`source.provider_config.batch_size`.

New compatibility normalization rules must be added to that registry before they
are accepted in `src/bioetl/infrastructure/config/*`. The canonical source
pagination contract remains `source.provider_config.pagination.*`; the only
pipeline-level pagination override is `page_size_override`.

### Normalization Governance For New Non-ChEMBL Fields

Если новый non-ChEMBL field попадает в active pipeline config, работа считается
незавершённой, пока не синхронизированы все связанные governance surfaces:

1. normalization profile coverage в `src/bioetl/domain/normalization/profiles/`
1. generated evidence в
   `docs/reports/generated/pipeline_normalization_field_matrix/`
1. representative fixtures в
   `tests/fixtures/normalization/non_chembl_identifier_cases.yaml` или
   `tests/fixtures/normalization/non_chembl_observed_values.yaml`
1. DQ and schema alignment в `configs/entities/{provider}/{entity}.yaml` и
   domain Silver schema
1. composite impact, если поле propagates into `configs/composites/*.yaml`

Published reference entrypoint for this workflow:

- [Non-ChEMBL Normalization Overview](../04-reference/normalization/non-chembl-normalization-overview.md)
- [Publication Normalization](../04-reference/normalization/publication-normalization.md)
- [PubChem Normalization](../04-reference/normalization/pubchem-normalization.md)
- [UniProt Normalization](../04-reference/normalization/uniprot-normalization.md)

### Авто-пропагация sort-by (ADR-014 compliance)

Параметры `sink.silver.sort_by` и `sink.gold.sort_by` **автоматически вычисляются**
из `technical_primary_key` и `business_primary_keys`:

```python
# pipeline_payload_normalization.py
raw_primary_keys = config.get("business_primary_keys", [])
primary_keys = [str(key) for key in raw_primary_keys if str(key).strip()]
technical_primary_key = str(config.get("technical_primary_key", "entity_id"))
sort_policy = [technical_primary_key] + [
    key for key in primary_keys if key != technical_primary_key
]

if layer_name in {"silver", "gold"}:
    layer.setdefault("sort_by", list(sort_policy))
```

Это означает, что entity configs обычно **не должны** явно указывать `sort_by` —
он выводится из primary key policy:

```yaml
# НЕ нужно указывать sort_by — он auto-computed
pipeline_name: chembl_activity
technical_primary_key: entity_id
business_primary_keys: ["activity_id"]  # → sort_by = ["entity_id", "activity_id"]
```

> **Преимущество:** Снижает дублирование на ~30%. Разработчик указывает только переопределения. Все 21 entity configs соответствуют ADR-014 через авто-пропагацию.

______________________________________________________________________

## Data Quality (DQ) конфигурация

### Иерархическая загрузка (ADR-027)

DQ правила загружаются в порядке приоритета (позже выигрывают):

1. `configs/base/quality.yaml` — глобальные defaults
1. `configs/providers/{provider}.yaml` — provider-specific
1. `configs/entities/{provider}/{entity}.yaml` — entity-specific
1. Inline `dq_overrides` в pipeline конфиге — финальные переопределения

> **Примечание:** Поле `dq_config_file` в pipeline YAML вычисляется конвенционно
> (ADR-029) и **не требует** явного указания. `DQConfigLoader` всегда загружает
> полную 3-уровневую иерархию по `provider`/`entity_type`. Если `dq_config_file`
> указан явно — он используется как override-path для entity-level файла.

### Специальная merge логика

- **Scalars:** Later wins
- **Validation lists:** **Concatenate** (не override)
- **Dicts:** Deep merge

### Структура DQ конфига

```yaml
# configs/base/quality.yaml
thresholds:
  soft_fail: 0.05      # >5% errors → Warning
  hard_fail: 0.25      # >25% errors → Fail Batch in the hierarchical quality default

strict_validation: false
invalid_record_policy: quarantine  # quarantine | skip | fail

report:
  enabled: true
  format: json
  include_sample_failures: true
  sample_size: 10

common_field_validations:
  - field: _content_hash
    type: required
    nullable: false
  - field: _ingestion_ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'

# Note: contract/runtime fallback defaults still normalize
# hard_fail_threshold at 0.20 when no explicit override is present.
```

### Entity-specific DQ правила

```yaml
# configs/entities/chembl/activity.yaml
entity_field_validations:
  - field: activity_id
    type: required
    nullable: false
  - field: standard_value
    type: range
    min: 0
    nullable: true
  - field: standard_type
    type: enum
    allowed: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, Kd, EC50, AC50, Potency]

entity_cross_field_validations:
  - name: value_requires_units
    fields: [standard_value, standard_units]
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units

entity_conditional_validations:
  - name: binding_requires_target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
        type: required
```

### Типы валидаций

| Тип        | Описание            | Параметры                |
| ---------- | ------------------- | ------------------------ |
| `required` | Обязательное поле   | `nullable`               |
| `range`    | Числовой диапазон   | `min`, `max`, `nullable` |
| `enum`     | Допустимые значения | `allowed`, `nullable`    |
| `pattern`  | Regex паттерн       | `pattern`, `nullable`    |
| `length`   | Длина строки        | `min`, `max`             |
| `unique`   | Уникальность        | —                        |

______________________________________________________________________

## Filter конфигурация

### Иерархическая загрузка (ADR-028)

Аналогично DQ, фильтры загружаются иерархически:

1. `configs/base/pipeline.yaml`
1. `configs/providers/{provider}.yaml`
1. `configs/entities/{provider}/{entity}.yaml`
1. Inline `filter_rules` в pipeline конфиге

### Input Filter

Фильтрация входных данных (CSV с ID):

```yaml
input_filter:
  enabled: true
  batch_size: 100
  source_path: "data/filter-ids.csv"
  column_name: "molecule_id"
  filter_field: "molecule_chembl_id"
```

### Gold Filters

Фильтрация данных на Gold слое:

```yaml
gold_filters:
  required_fields:
    - activity_id
    - standard_value

  columns:
    standard_type:
      operator: in
      values: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50]
    pchembl_value:
      operator: is_not_null

  ranges:
    pchembl_value:
      min: 5.0
      max: 15.0
      include-min: true
      include-max: true

  exclude_if_present:
    - deprecated-field
```

### Операторы фильтрации

| Оператор       | Описание                    |
| -------------- | --------------------------- |
| `in`           | Значение в списке           |
| `not_in`       | Значение не в списке        |
| `is_null`      | NULL                        |
| `is_not_null`  | NOT NULL                    |
| `is_empty`     | Пустая строка или список    |
| `is_not_empty` | Не пустая строка или список |

______________________________________________________________________

## Source конфигурация

### Структура

```yaml
# configs/providers/chembl.yaml
source:
  provider_config:
    provider: chembl
    base_url: https://www.ebi.ac.uk/chembl/api/data
    auth_type: public
    client:
      timeout_sec: 60.0
      max_retries: 3
    pagination:
      page_size: 1000
      id_batch_size: 20
      strategy: offset
      max_url_length: 1000
    # Transitional migration-only aliases may still appear in existing configs:
    # batch_size: 20
    # page_size: 1000
    # max_url_length: 2000

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300

  rate_limit:
    requests_per_second: 3
    burst: 10

  health_check:
    endpoint: /chembl/api/data/status.json
    timeout: 5

entities:
  - activity
  - assay
  - molecule
  - target
  # ... и 8 других entities для ChEMBL
```

Canonical current source pagination contract:

- `source.provider_config.pagination.*` is the single source of truth for provider pagination.
- Pipelines may override pagination only through `page_size_override`.

Retired source provider pagination aliases:

- `source.provider_config.batch_size`
- `source.provider_config.page_size`
- `source.provider_config.max_url_length`
- `source.provider_config.cursor_pagination`

Retired source root alias:

- `source.batch_size`

### Rate Limits по провайдерам (7 source configs)

| Provider        | Source Config                            | Rate Limit  | Burst | Batch Size |
| --------------- | ---------------------------------------- | ----------- | ----- | ---------- |
| ChEMBL          | `configs/providers/chembl.yaml`          | 3 req/sec   | 10    | 20         |
| PubChem         | `configs/providers/pubchem.yaml`         | 5 req/sec   | 10    | 50         |
| UniProt         | `configs/providers/uniprot.yaml`         | 10 req/sec  | 20    | 200        |
| CrossRef        | `configs/providers/crossref.yaml`        | 50 req/sec  | 100   | 50         |
| OpenAlex        | `configs/providers/openalex.yaml`        | 10 req/sec  | 20    | 50         |
| PubMed          | `configs/providers/pubmed.yaml`          | 3 req/sec   | 5     | 100        |
| SemanticScholar | `configs/providers/semanticscholar.yaml` | 0.1 req/sec | 1     | 50         |

______________________________________________________________________

## Sink конфигурация

### Структура слоёв

```yaml
sink:
  bronze:
    enabled: true
    format: jsonl
    path: data/output/bronze/chembl/activity

  silver:
    enabled: true
    format: delta
    path: data/output/silver/chembl/activity
    mode: merge                    # merge | append | delete
    primary_key: ["activity_id"]
    deterministic: true
    sort_by:
      columns: ["activity_id"]
      ascending: true
    on-schema-mismatch: evolve     # error | evolve | ignore

  gold:
    enabled: true
    format: delta                  # delta | parquet
    path: data/output/gold/chembl/activity
    mode: overwrite                # append | overwrite | scd2
    partition_by: ["standard_type"]
    flat-structure: true
    csv_export:
      enabled: true
      include-columns: ["activity_id", "standard_type", "standard_value"]
    metadata:
      owner: "data-team"
      description: "ChEMBL activity measurements"
      tags: ["bioactivity", "chembl"]
      retention-days: 365
```

### Write Modes

> **Canonical owner:** this guide documents YAML usage only. Normative
> write-mode semantics live in `docs/00-project/RULES.md` §2.1.1-§2.1.2 and
> the runtime enums in `src/bioetl/domain/medallion.py`.

| Mode        | Bronze        | Silver            | Gold              |
| ----------- | ------------- | ----------------- | ----------------- |
| `append`    | Только append | —                 | —                 |
| `merge`     | —             | Upsert по PK      | —                 |
| `delete`    | —             | Полная перезапись | —                 |
| `overwrite` | —             | —                 | Полная перезапись |
| `scd2`      | —             | —                 | Историзация Type 2 |

### Schema Mismatch Handling

| Режим    | Описание                                |
| -------- | --------------------------------------- |
| `error`  | Падение при несовпадении схемы          |
| `evolve` | Автоматическое добавление новых колонок |
| `ignore` | Игнорировать несовпадения               |

______________________________________________________________________

## Circuit Breaker конфигурация

```yaml
circuit-breaker:
  failure_threshold: 5      # Количество ошибок для открытия
  recovery_timeout: 300     # Время recovery в секундах
  half_open_requests: 1     # Пробные запросы в half-open состоянии
```

**Состояния:**

- **Closed:** Нормальная работа
- **Open:** Все запросы блокируются
- **Half-Open:** Пробные запросы для recovery

______________________________________________________________________

## Maintenance конфигурация

```yaml
maintenance:
  vacuum:
    enabled: true
    retention-days: 7           # Минимальный возраст файлов для удаления
    run-after-pipeline: false   # Автоматический VACUUM после пайплайна

  bronze-cleanup:
    enabled: true
    retention-days: 90          # Retention для Bronze файлов
```

______________________________________________________________________

## Валидация конфигурации

### CLI команды

```bash
# Показать конфигурацию
bioetl config show chembl_activity

# Валидация
bioetl config validate chembl_activity

# Показать глобальные настройки
bioetl config show-settings

# Список всех пайплайнов
bioetl config list-pipelines
```

### Pydantic валидация

При загрузке конфига выполняются проверки:

| Проверка                         | Описание                                            |
| -------------------------------- | --------------------------------------------------- |
| `validate_batch_size`            | `batch_size <= 5000`                                |
| `validate_provider`              | `provider` в lowercase                              |
| `validate_entity_type_canonical` | publication\* вместо legacy document\*              |
| `validate_medallion_formats`     | Bronze принудительно `jsonl`, Silver только `delta` |
| `validate_thresholds`            | `soft_fail < hard_fail`                             |

______________________________________________________________________

## Примеры конфигураций

### Минимальный конфиг

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
business_primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"
```

### С DQ переопределениями

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
business_primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

dq_overrides:
  thresholds:
    soft_fail: 0.10
    hard_fail: 0.30

  field_validations:
    - field: pchembl_value
      type: range
      min: 0
      max: 20
      nullable: true
```

### С кастомными sink путями

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
business_primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

sink:
  bronze:
    path: /custom/path/bronze/chembl/activity
  silver:
    path: /custom/path/silver/chembl/activity
    partition_by: ["standard_type"]
  gold:
    path: /custom/path/gold/chembl/activity
    csv_export:
      enabled: true
```

______________________________________________________________________

## Миграция с JSON на YAML

> **Историческая справка:** BioETL изначально использовал JSON для конфигураций.
> Переход на YAML выполнен для улучшения читаемости и поддержки комментариев.

**Было (JSON):**

```json
{
  "pipeline_name": "chembl_activity",
  "provider": "chembl",
  "entity-type": "activity",
  "batch-size": 100
}
```

**Стало (YAML):**

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
batch_size: 100

# Комментарии теперь поддерживаются!
```

______________________________________________________________________

## Troubleshooting

### Ошибка валидации конфига

```bash
bioetl config validate chembl_activity
```

**Распространённые ошибки:**

| Ошибка                   | Причина                     | Решение                |
| ------------------------ | --------------------------- | ---------------------- |
| `batch_size > 5000`      | Слишком большой batch       | Уменьшить до ≤5000     |
| `provider not lowercase` | Provider в верхнем регистре | Использовать lowercase |
| `soft_fail >= hard_fail` | Неверные пороги             | soft_fail < hard_fail  |
| `unknown field`          | Опечатка в имени поля       | Проверить spelling     |

### DQ правила не применяются

1. Проверить путь к DQ файлу:

   ```bash
   ls configs/entities/{provider}/{entity}.yaml
   ```

1. Проверить merge логику — validation lists **concatenate**, не override.

1. Использовать CLI для просмотра resolved конфига:

   ```bash
   bioetl config show chembl_activity --format json
   ```

______________________________________________________________________

## См. также

- [Running Pipelines](running-pipelines.md) — запуск пайплайнов
- [CLI Reference](../04-reference/cli.md) — команды CLI
- [DQ Configuration](dq-configuration.md) — детальная настройка DQ
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md) — sort-by requirement
- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md) — иерархия конфигов
- [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) — multi-provider pipelines
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) — иерархическая DQ загрузка
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md) — иерархическая Filter загрузка
- [ADR-029: Convention-based Path Resolution](../02-architecture/decisions/ADR-029-output-metadata-unification.md) — авто-вычисление путей
