# BioETL Schema Change Plan (PROMPT-2)

**Дата:** 2026-02-18 01:50:09 Europe/Chisinau
**Response ID:** RID-BIOETL-SCHEMA-AUDIT-20260218-015009
**Основа:** выводы аудита схем по `configs/schemas/composite/**` (alias chaos, TRASH reclassification, drift между двумя publication-схемами, Python↔YAML inconsistencies, Gold propagation risks).

______________________________________________________________________

## A) Change Backlog

| ID     | Pipeline/Global          | Изменение                                                                                                                                                        | Уровень (Low/Refactor/Breaking) | Impact                                                                           | Risk   | Owner role                        | ADR? | Миграция (кратко)                                                                                                        | Done criteria                                                                                                |
| ------ | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------- | ------ | --------------------------------- | ---: | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| SC-001 | composite/publication    | Удалить ghost base_names после alias resolution: `doi`, `pmid`, `pmc_id`, `year`, `document_chembl_id` (оставить только canonical `publication_*`)               | Refactor                        | Убирает double-counting/ghost columns в field grouping и снижает неоднозначность | Medium | Data Platform Engineer            |   ✅ | Silver: не меняем Bronze, добавляем alias-backcompat view; Gold: контракт v1.1 (non-breaking cleanup), dual-read 1 релиз | В field_groups нет legacy-duplicates; contract tests подтверждают один canonical столбец на семантику        |
| SC-002 | composite/publication    | Добавить отсутствующий canonical `publication_year` в `date_and_places`                                                                                          | Low                             | Устраняет пропуск canonical поля в группировке                                   | Low    | Data Engineer                     |   ❌ | Delta additive (no rewrite), backfill из существующего `publication_year`                                                | Поле стабильно присутствует в Silver/Gold mapping, без новых drift-alert                                     |
| SC-003 | composite/publication    | Консолидация MeSH/keywords/topics: удалить legacy `mesh`, `mesh_terms`, `keywords`, `topics`; оставить `subject_mesh`, `subject_keywords`, `subject_topics`      | Refactor                        | Снижает семантическую дубликацию в аналитике Gold                                | Medium | Analytics Engineer                |   ✅ | Contract v1.2 (compat aliases), dual-serve 2 релиза через view aliases                                                   | Нет 3-way overlap в группах; все golden tests используют canonical subject\_\*                               |
| SC-004 | composite/publication    | Разгрузить `id_and_status`: перенести `fields_of_study` в terms/topics, `publication_type` в publication_types                                                   | Refactor                        | Убирает логическую перегрузку группы и путаницу в Gold API                       | Low    | Data Modeler                      |   ✅ | Non-breaking re-grouping (schema columns unchanged), обновление metadata group tags                                      | `id_and_status` содержит только id/status; group-level DQ rules применимы без исключений                     |
| SC-005 | composite/publication    | TRASH reclassification: `content_hash` вывести в system-metadata (exclude from Gold), добавить `author_details` в TRASH для консистентности с Python mapping     | Refactor                        | Убирает смешение системных и бизнес-полей, выравнивает Python↔YAML               | Medium | Platform Architect                |   ✅ | Contract v1.1 metadata patch; Silver keeps `_meta`; Gold strict exclude для system group                                 | `content_hash` больше не классифицируется как business trash; `author_details` синхронизирован в YAML/Python |
| SC-006 | composite/publication    | Journal naming cleanup: `journal_full_title`, `journal_title`, `journal_abbrev` → deprecated/alias к canonical (`journal`, `journal_name`, `journal_name_short`) | Breaking                        | Убирает 7-way journal fragmentation; меняет публичные legacy имена в Gold API    | High   | Product Analytics + Data Engineer |   ✅ | Contract v2.0, dual-serve 2 релиза (legacy view + warnings), rollback по feature flag `gold_publication_journal_v2`      | В v2 нет legacy journal columns; usage telemetry legacy\<5% перед cutover                                    |
| SC-007 | composite/publication    | Решение по `language` и `license_url`: либо остаются вне Gold, либо продвигаются в новую Open Access/Metadata группу                                             | Breaking (если в Gold)          | Потенциально добавляет аналитически значимые поля, меняет downstream contract    | High   | Data Product Owner                |   ✅ | Если promote: contract v2.1 additive, dual-write в Gold и в compatibility view, rollback через contract pinning v2.0     | Decision record принят; при promote поля документированы и проходят strict validation                        |
| SC-008 | global/composite-engine  | Свести к одному источнику истины publication schema: harmonize `publication.yaml` и `field_groups/publication.yaml` + синхронизировать `FIELD_TO_GROUP_MAPPING`  | Breaking                        | Закрывает semantic drift между двумя параллельными моделями                      | High   | Platform Architect                |   ✅ | Two-phase: (1) parity tests + generated mapping; (2) switch registry to single canonical spec                            | Drift test между YAML/Python = 0 differences; регрессии merge/order отсутствуют                              |
| SC-009 | global/gold-contracts    | Ввести строгую стратегию contract versioning + compatibility checks для breaking/non-breaking schema changes                                                     | Refactor                        | Предотвращает неуправляемый schema drift в Gold                                  | Medium | Tech Lead                         |   ✅ | Registry: semver contracts, compatibility gate в CI, migration manifests                                                 | Merge blocked без compatibility verdict; changelog содержит contract diff                                    |
| SC-010 | global/metadata-standard | Унификация OutputMetadata и ключей (PK/merge/provider scope/content hash standard)                                                                               | Refactor                        | Снижает cross-pipeline расхождения metadata и upsert conflicts                   | Medium | Data Architect                    |   ✅ | Ввести metadata spec v1, rollout по pipeline batches                                                                     | Все composite pipelines публикуют одинаковый обязательный metadata set                                       |
| SC-011 | global/dq                | Externalize DQ rules для schema drift и групповых правил (config-driven)                                                                                         | Refactor                        | Делает drift-control управляемым без code hotfix                                 | Medium | Data Quality Engineer             |   ✅ | DQ configs + alert routing + threshold policies                                                                          | Drift alerts и hard/soft thresholds мониторятся centrally                                                    |

______________________________________________________________________

## B) ADR Candidates

### ADR-1: Canonical Publication Fields Only (Legacy Alias Elimination)

- **Title:** Canonical-only base names for publication field groups
- **Context:** В audit обнаружены legacy+canonical дубликаты (`doi`/`publication_doi`, `pmid`/`publication_pmid`, `year`/`publication_year`), что создаёт ghost columns и риск double-counting.
- **Decision:** В field_groups оставляем только canonical `publication_*` и `subject_*`; legacy имена поддерживаются как compatibility aliases на уровне contract/view.
- **Consequences:** Меньше неоднозначности и меньше дефектов агрегаций; требуется контроль обратной совместимости для downstream SQL.
- **Migration plan:** v1.1 (cleanup) → dual-read aliases 1 релиз → removal в v2.0.
- **Compatibility notes:** Backward-compatible через alias views; direct column references на legacy колонки считаются deprecated.
- **Observability:** метрики `legacy_column_usage`, `gold_contract_validation_failures`, `schema_diff_legacy_vs_canonical`.

### ADR-2: TRASH vs System Metadata Reclassification

- **Title:** Separate system metadata from TRASH business exclusions
- **Context:** `content_hash` отмечен в TRASH, хотя это системное поле; также `author_details` отсутствует в YAML при наличии в Python mapping.
- **Decision:** Ввести `system_metadata` классификацию (always exclude from Gold by policy), TRASH оставить только для бизнес-нецелевых полей.
- **Consequences:** Более прозрачная семантика; меньше риска случайного попадания/исключения системных полей.
- **Migration plan:** Additive metadata spec v1; remap groups; regression tests на Gold exclusion.
- **Compatibility notes:** Non-breaking для Gold payload, если exclude-политика сохранена.
- **Observability:** `system_field_leak_to_gold`, `trash_group_delta_count`, `mapping_parity_failures`.

### ADR-3: Single Source of Truth for Publication Schema

- **Title:** Unify publication schema definitions across YAML and Python mapping
- **Context:** Зафиксирован semantic drift между `publication.yaml`, `field_groups/publication.yaml` и `FIELD_TO_GROUP_MAPPING`.
- **Decision:** Сделать один canonical schema spec и генерировать вторичные представления (или strict parity gate).
- **Consequences:** Меньше ручных расхождений; upfront cost на migration tooling.
- **Migration plan:** Phase 1 parity tests + manifest; Phase 2 switch registry/read path; Phase 3 retire duplicate spec.
- **Compatibility notes:** Breaking только если меняются публичные column names/group exports; тогда version bump обязателен.
- **Observability:** `schema_parity_score`, `generated_vs_runtime_mapping_mismatch`, `field_drop_events`.

### ADR-4: Gold Contract SemVer + Breaking Windows

- **Title:** Versioned Gold contracts with mandatory breaking windows and rollback criteria
- **Context:** Аудит показывает high-risk изменения (journal cleanup, optional promotion `language`/`license_url`) влияющие на downstream аналитические API.
- **Decision:** Принять semver для Gold contracts: patch=metadata/docs, minor=additive columns, major=rename/remove/resemantic.
- **Consequences:** Управляемые релизы и предсказуемые cutover/rollback.
- **Migration plan:** registry + compatibility checker + dual-service period for each major.
- **Compatibility notes:** Любой rename/remove требует major + dual-service минимум 2 релиза.
- **Observability:** `contract_version_adoption`, `dual_service_query_share`, `rollback_trigger_count`.

### ADR-5: Group Semantics Governance (`id_and_status` de-overload)

- **Title:** Strict semantic boundaries for publication field groups
- **Context:** `id_and_status` перегружен не-id полями (`fields_of_study`, `publication_type`), что искажает Gold semantics.
- **Decision:** Формализовать правила membership для групп и запретить mixed semantics.
- **Consequences:** Предсказуемые аналитические представления; меньше ad-hoc исключений в трансформациях.
- **Migration plan:** regroup non-breaking + update group-level DQ rules.
- **Compatibility notes:** Поскольку колонки не удаляются, изменение обычно non-breaking.
- **Observability:** `group_semantic_violations`, `dq_group_rule_failures`.

______________________________________________________________________

## C) Migration Runbook

### 1) Подготовка

1. Зарегистрировать текущие Gold contracts как baseline (`publication:v1.x`).
1. Зафиксировать матрицу изменений: additive/refactor/breaking для SC-001..SC-011.
1. Для breaking задач (SC-006, потенциально SC-007, SC-008):
   - поднять major/minor версию контракта,
   - создать dual-service views,
   - определить rollback criteria до запуска.
1. Включить schema-registry checks и compatibility gate в CI до rollout.

### 2) Silver migration (Delta)

1. **Add columns/backfill:**
   - добавить/валидировать canonical `publication_year` mapping;
   - backfill только из уже существующих canonical источников (без реконструкции из выдуманных полей).
1. **Type fixes:**
   - проверить типовую консистентность для canonical publication identifiers.
1. **Constraints:**
   - добавить soft constraints на mutually-exclusive legacy/canonical pairs (legacy не должен материализоваться после alias step).
1. **Repartition (по необходимости):**
   - без высококардинальных partition keys; сохранять текущую medallion-политику partitioning.
1. **Schema drift policy:**
   - `error` для breaking drift,
   - `evolve` только для явно additive и контрактно-разрешённых изменений.

### 3) Gold migration (контракты)

1. Выпустить версии:
   - `v1.1`: canonical cleanup + metadata harmonization (non-breaking),
   - `v2.0`: journal legacy removal,
   - `v2.1` (опционально): `language`/`license_url` promotion.
1. Включить strict validation against contract schema на write path.
1. Breaking window:
   - минимум 2 релиза параллельного обслуживания для `v1` и `v2`.
1. Deprecation notices:
   - в changelog/contract docs с датой окончательного удаления.

### 4) DQ externalization rollout

1. Перенести schema/group DQ правила в config-driven слой.
1. Добавить правила:
   - запрет legacy+canonical duplication,
   - контроль `default_group=TRASH` drop-rate,
   - контроль соответствия group semantics (`id_and_status`).
1. Мониторинг:
   - soft alert при >5% аномалий,
   - hard fail при >20% аномалий batch.

### 5) Cutover + rollback plan

1. **Cutover criteria:**
   - contract compatibility checks = PASS,
   - legacy usage ниже порога (например, \<5%),
   - 2 последовательных successful runs.
1. **Rollback triggers:**
   - рост contract validation failures,
   - критический рост missing columns в downstream,
   - DQ hard-fail.
1. **Rollback actions:**
   - pin consumers на предыдущую contract version,
   - отключить feature flags (`gold_publication_journal_v2`, `gold_publication_oa_fields`),
   - перезапустить Gold materialization из последней стабильной Silver snapshot.

______________________________________________________________________

## D) Standardization Pack

### 1) Unified OutputMetadata (обязательный набор)

Обязательные поля (единый policy для composite pipelines):

- `run_id: string`
- `provider: string`
- `entity: string`
- `ingestion_ts: timestamp`
- `pipeline_version: string`
- `contract_version: string`
- `content_hash: string` (system metadata; не business-поле Gold)
- `record_source: string` (source lineage)
- `dq_status: string`
- `dq_error_count: int`

### 2) Unified Key Strategy

- Silver merge key: `provider + entity + canonical_business_id` (без legacy alias полей).
- Gold PK: provider-scoped canonical key, чтобы исключить кросс-провайдерные коллизии.
- Для publication: приоритет canonical identifiers (`publication_doi`, `publication_pmid`, `publication_id`) по согласованному precedence.

### 3) Content hash standard

- Каноникализация перед hash:
  - NaN/Inf → `null`
  - float → round(10)
  - date → `YYYY-MM-DD`
  - string → trim
  - deterministic key ordering
- Exclude list: технические поля исполнения (`_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`) + прочие runtime-only metadata.
- `content_hash` хранится как system metadata и исключается из бизнес-модели Gold.

### 4) Naming standards

- Запрет на одновременное существование legacy+canonical base_name в контрактной модели.
- Provider-qualified policy:
  - **Нужно**: когда поле имеет provider-специфичную семантику и не имеет canonical эквивалента.
  - **Запрещено**: когда есть canonical unified field (например, publication identifiers и subject\_\*).
- Все публичные Gold поля — только canonical naming.

### 5) Partitioning guidelines

- Не использовать высокую кардинальность (doi/pmid/hash/run_id) как partition keys.
- Поддерживать medallion-совместимое partitioning по низкой/средней кардинальности (например, provider/entity/date buckets).
- Любое изменение partition scheme требует impact analysis на small-files и read amplification.

______________________________________________________________________

## E) Контроль качества (gate)

### Что должно быть в CI

1. **Schema diff tests:** legacy vs canonical, YAML vs Python mapping parity.
1. **Golden tests:** стабильные snapshot tests Gold contract payload.
1. **Contract compatibility checks:** semver-aware (patch/minor/major rules).
1. **DQ checks:**
   - duplicate semantic fields,
   - TRASH/system leakage,
   - drift severity thresholds.
1. **Migration tests:** dual-service read compatibility для v1/v2.

### Какие проверки блокируют merge

- Любой unapproved breaking contract diff.
- Drift между `publication.yaml` и `field_groups/publication.yaml` (до унификации) или между canonical spec и generated artifacts.
- Появление legacy+canonical дубликатов в одной релизной схеме.
- Нарушение strict Gold validation.
- DQ hard-threshold breach (>20% batch anomalies).

### Документирование breaking changes

- Обязательно:
  1. ADR с decision + migration + rollback criteria,
  1. Changelog entry с contract version bump,
  1. Deprecation notice с датой sunset,
  1. Migration guide для downstream SQL/BI потребителей.

______________________________________________________________________

## Contract Compatibility Strategy (explicit)

- **Non-breaking (patch/minor):** regrouping без удаления колонок, добавление metadata, добавление alias views.
- **Breaking (major):** rename/remove legacy journal fields, отказ от legacy base_names в публичном API, promotion новых Gold columns с semantic changes.
- Для каждого breaking change:
  1. новая версия контракта,
  1. миграционный манифест,
  1. dual-service период (минимум 2 релиза),
  1. измеримые rollback критерии (validation failures, consumer errors, DQ hard-fails).
