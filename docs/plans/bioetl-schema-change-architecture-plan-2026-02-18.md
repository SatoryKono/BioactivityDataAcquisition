# BioETL Schema Change Architecture Plan (Prompt-2)

**Date:** 2026-02-18
**Input audits:**

- `docs/audits/composite-schemas-audit-2026-02-17.md`
- `docs/05-operations/verification/schema-review-2026-02-17.md`
- `docs/05-operations/verification/sync-report-2026-02-17.md`

**Scope policy:** план построен только на зафиксированных в аудитах проблемах/рисках, без добавления новых фактов.

______________________________________________________________________

## A) Change Backlog

| ID      | Pipeline/Global              | Изменение                                                                                                                                   | Уровень (Low/Refactor/Breaking) | Impact                                                            | Risk   | Owner role                         | ADR? | Миграция (кратко)                                                                                     | Done criteria                                                                             |
| ------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------- | ------ | ---------------------------------- | ---: | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| BLG-001 | global/publication composite | Удалить ghost base_name после alias resolution: `doi`, `pmid`, `pmc_id`, `year`, `document_chembl_id`; оставить canonical (`publication_*`) | Refactor                        | Устранение двойной трактовки полей и ghost columns в field groups | Medium | Data Platform Engineer             |   ✅ | V2 field-groups, backfill не нужен (логическая чистка), dual-read на legacy aliases в Gold контрактах | Нет legacy base_name в `field_groups/publication.yaml`; тесты field-group loader проходят |
| BLG-002 | global/publication composite | Консолидировать тройки `mesh/mesh_terms/subject_mesh`, `keywords/subject_keywords`, `topics/subject_topics` в canonical поля                | Refactor                        | Снижение schema drift, единая семантика topical fields            | Medium | Domain Model Engineer              |   ✅ | Ввести alias compatibility map на migration window; затем hard deprecate legacy names                 | Все 3 группы сведены к canonical; нет дубликатов в Gold экспорте                          |
| BLG-003 | global/publication composite | Починить перегрузку `id_and_status`: перенести `fields_of_study` в terms/topics и `publication_type` в publication_types                    | Refactor                        | Устранение семантической путаницы в группах Gold include          | Low    | Data Architect                     |   ✅ | Contract minor bump, без удаления колонок; проверка порядка/групп                                     | Поля в целевых группах; Gold включает поля из корректных доменных групп                   |
| BLG-004 | global/publication composite | Переклассифицировать `content_hash` как system (не business trash) и формализовать include_in_gold=false для system group                   | Refactor                        | Разделение системной и бизнес-метадаты                            | Medium | Platform Architect                 |   ✅ | Ввести system group и запретить попадание в Gold по policy; rollback через feature flag group policy  | `content_hash` не в TRASH и не попадает в Gold                                            |
| BLG-005 | global/publication composite | Решение по `language` и `license_url` (сейчас TRASH): если добавляются в Gold — сделать controlled breaking rollout                         | Breaking                        | Возможное расширение аналитического API Gold                      | High   | Product Analytics + Data Architect |   ✅ | Contract vNext, dual-write в Gold vN/vN+1, deprecation window 2 релиза, explicit rollback criteria    | Решение ADR принято; либо поля остаются вне Gold, либо выполнен полный breaking rollout   |
| BLG-006 | global/publication mappings  | Синхронизировать Python `FIELD_TO_GROUP_MAPPING` и YAML (включая `author_details`)                                                          | Refactor                        | Снятие Python↔YAML inconsistency                                  | Medium | Backend Engineer                   |   ❌ | Обновление mapping + regression tests                                                                 | Несоответствий mapping между Python/YAML нет                                              |
| BLG-007 | uniprot/protein              | Удалить или начать заполнять dead fields: `pharmaceutical_use`, `publication_count`                                                         | Breaking                        | Устранение неиспользуемых контрактных полей                       | High   | UniProt Pipeline Owner             |   ✅ | Выбор: populate (non-breaking) или remove (breaking, contract v+1, dual-read); backfill при populate  | Поля либо consistently populated, либо удалены с versioned migration                      |
| BLG-008 | uniprot/protein              | Добавить `gene_names` в Silver schema (сейчас проходит без валидации)                                                                       | Refactor                        | Повышение валидации Silver                                        | Medium | UniProt Pipeline Owner             |   ❌ | Delta add column/validation rule, backfill из уже существующих значений                               | `gene_names` валидируется Silver schema                                                   |
| BLG-009 | semanticscholar/publication  | Добавить `issue` в Silver schema (сейчас unvalidated passthrough)                                                                           | Refactor                        | Закрытие validation gap                                           | Medium | Publication Pipeline Owner         |   ❌ | Delta schema add column + contract check                                                              | `issue` покрыт Silver schema и contract tests                                             |
| BLG-010 | chembl/tissue                | Исправить PK mismatch в Gold: `tissue_chembl_id` → `tissue_id`                                                                              | Breaking                        | Выравнивание PK с config/transformer                              | High   | ChEMBL Pipeline Owner              |   ✅ | Gold contract major bump, dual-write PK alias period, downstream remap guide                          | Gold PK совпадает с pipeline config/transformer                                           |
| BLG-011 | crossref/publication         | Закрыть MISSING_TRANSFORMER поля (`content_domain_*`, `issn_print/electronic`, `published_print/online`)                                    | Refactor                        | Полнота трансформации под existing entity schema                  | High   | Publication Pipeline Owner         |   ❌ | Transformer enrichment + DQ checks                                                                    | Все поля entity schema имеют transformer population или documented exception              |
| BLG-012 | global/config governance     | Принять решение по `configs/schemas/*` с пустыми `column_groups: []`: депрекейт или заполнение                                              | Refactor                        | Устранение пустого cfg_schema слоя в 22 пайплайнах                | Medium | Architecture Guild                 |   ✅ | ADR decision + migration path for config readers                                                      | Нет пустого governance-контура без статуса (deprecated/active)                            |

______________________________________________________________________

## B) ADR Candidates

### ADR-C1: Canonical Publication Field Names and Alias Retirement

- **Context:** аудит выявил coexistence legacy/canonical base_name и ghost columns после alias resolution (`doi`/`publication_doi`, `year`/`publication_year`, и т.д.).
- **Decision:** в composite field-groups оставить только canonical base_name; legacy names переводятся в compatibility alias map на ограниченный период.
- **Consequences:** меньше schema drift и двусмысленности; требуется migration window для downstream SQL/BI.
- **Migration plan:**
  1. Ввести `contract_version = v2` для publication Gold.
  1. Dual-read aliases (не dual-write физколонок) на 2 релиза.
  1. Удалить legacy aliases после burn-in.
- **Compatibility notes:** backward compatibility через alias map и changelog breaking section.
- **Observability:** метрики `legacy_field_usage_count`, `gold_contract_validation_failures`, алерт при non-zero usage legacy полей после дедлайна.

### ADR-C2: Field Group Taxonomy Hardening (ID vs Topics vs Types vs System)

- **Context:** `id_and_status` перегружен не-идентификаторными полями; `content_hash` попал в TRASH вместо system; Python↔YAML mapping расходится.
- **Decision:** формализовать taxonomies групп и запретить смешение system/business семантики.
- **Consequences:** прозрачная модель Gold include/exclude; потребуется рефактор field group configs и mapping code.
- **Migration plan:**
  1. Ввести system group policy (`include_in_gold=false`).
  1. Перенести `fields_of_study`, `publication_type` в доменные группы.
  1. Синхронизировать Python mapping с YAML.
- **Compatibility notes:** non-breaking при сохранении имен колонок; change в порядке колонок — документировать.
- **Observability:** `field_group_unmapped_fields`, `default_to_trash_count`, `group_policy_violations`.

### ADR-C3: Gold Contract Versioning and Breaking Window Policy

- **Context:** аудит фиксирует потенциальные breaking кейсы (`language/license_url` promotion, PK rename tissue, dead field removal).
- **Decision:** единая policy: любое breaking изменение Gold → major version bump + migration + rollback criteria.
- **Consequences:** предсказуемость для потребителей, дополнительная нагрузка на dual-support.
- **Migration plan:**
  1. Версионировать контракты (`vN`, `vN+1`).
  1. Dual-write/dual-read где необходимо (PK/field renames).
  1. Формальный cutover checkpoint + freeze window.
- **Compatibility notes:** обязательный deprecation период (минимум 2 релиза для API-полей).
- **Observability:** `consumer_version_adoption`, `contract_breaking_errors`, `rollback_trigger_events`.

### ADR-C4: Silver Validation Completeness Policy

- **Context:** `gene_names` и `issue` проходят без Silver validation; часть полей entity объявлена, но transformer не заполняет.
- **Decision:** каждая колонка, проходящая в Silver/Gold, должна быть в Silver schema или иметь explicit exception.
- **Consequences:** меньше silent drift; больше upfront работы в схемах.
- **Migration plan:** phased rollout по пайплайнам (uniprot, semanticscholar, crossref) с soft→hard validation.
- **Compatibility notes:** non-breaking при additive schema updates; breaking only если удаляются dead fields.
- **Observability:** `silver_unvalidated_field_count`, `transformer_missing_field_count`, DQ fail rates.

### ADR-C5: Config Schema Governance (Empty column_groups policy)

- **Context:** во всех `configs/schemas/{provider}/{entity}.yaml` выявлен пустой `column_groups: []`.
- **Decision:** выбрать одно: (A) активировать и заполнять, (B) официально депрекейтнуть слой с удалением readers.
- **Consequences:** убирается архитектурная двусмысленность.
- **Migration plan:** inventory consumers → выбрать стратегию → выполнить remove/populate.
- **Compatibility notes:** если remove, сохранить compatibility shim на 1 релиз.
- **Observability:** `cfg_schema_consumers_count`, `empty_schema_config_detected`.

______________________________________________________________________

## C) Migration Runbook

### 1) Подготовка

1. Создать/обновить schema registry entries для Silver и Gold по затронутым пайплайнам.
1. Выполнить version bump контрактов:
   - minor для refactor/non-breaking;
   - major для breaking (`chembl/tissue` PK rename, возможный promotion `language/license_url`, удаление dead fields).
1. Для breaking кейсов включить dual-support:
   - dual-read aliases (legacy→canonical) для publication fields;
   - dual-write только где требуется реальная смена физической колонки/PK.
1. Зафиксировать rollback checkpoints (snapshot Delta + текущие contract artifacts).

### 2) Silver migration (Delta)

1. **Add columns / schema fixes:**
   - добавить в Silver schema: `gene_names` (uniprot/protein), `issue` (semanticscholar/publication).
1. **Type/validation fixes:**
   - синхронизировать validated поля с entity/transformer coverage.
1. **Backfill:**
   - для additive колонок — заполнить из существующих raw/transformed источников.
1. **Constraints & checks:**
   - PK consistency checks (особенно `chembl/tissue` путь к Gold).
   - DQ thresholds: soft/hard гейты по текущей политике.
1. **Repartition:** только при подтвержденной необходимости; не вводить высокую кардинальность партиций.

### 3) Gold migration (contracts)

1. Ввести `vN+1` Gold contracts для breaking pipeline(ов).
1. Применить strict validation на новые контракты в pre-prod.
1. Окно breaking migration:
   - период параллельного обслуживания: минимум 2 релиза для полей/алиасов;
   - явная дата окончания поддержки legacy alias.
1. Cutover: переключить default consumers на `vN+1` после выполнения SLO adoption.

### 4) DQ externalization rollout

1. Вынести правила в конфиги для полей alias/dead/unvalidated.
1. Добавить мониторинг:
   - drift (новые/невалидированные поля),
   - legacy usage,
   - coverage transformer→silver→gold.
1. Постепенно перевести правила из warning в blocking, когда false-positive rate стабилен.

### 5) Cutover + rollback plan

1. **Go/No-Go criteria:**
   - 0 critical contract validation errors;
   - legacy usage ниже согласованного порога;
   - DQ hard-threshold violations = 0.
1. **Rollback criteria (обязательные для каждого breaking):**
   - рост contract errors выше SLO;
   - массовые падения consumer jobs;
   - невозможность чтения legacy contract в deprecation window.
1. **Rollback actions:**
   - вернуть consumer routing на `vN`;
   - отключить new schema flags;
   - восстановить предыдущие Delta snapshots/contract artifacts.

______________________________________________________________________

## D) Standardization Pack

### 1) Unified OutputMetadata fields (обязательный набор)

Минимальный обязательный набор для Silver/Gold метадаты:

- `provider: string`
- `entity_type: string`
- `run_id: string`
- `run_type: string | null`
- `_ingestion_ts: timestamp`
- `content_hash: string`
- `_dq_warn: bool | null` (где применимо)

Правило: системные поля не классифицируются как бизнес-TRASH; управляются отдельной system-policy.

### 2) Unified Key Strategy

- PK/merge key определяется contract-first и должен совпадать между config, transformer, Silver schema, Gold schema.
- Provider scoping обязателен там, где ключ не глобально уникален.
- Для rename PK (пример `tissue_chembl_id` → `tissue_id`) — только через breaking versioned migration.

### 3) Content hash standard

- Каноникализация: использовать единую canonical serialization до hashing.
- Exclude list: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.
- Null handling: null-эквиваленты нормализуются до `null`.
- Ordering: детерминированная сортировка ключей при сериализации.

### 4) Naming стандарты

- Canonical-first: в контрактах и field groups используются только canonical имена (`publication_*`, `subject_*`).
- Provider-qualified policy:
  - нужен, если поле source-specific и не имеет устойчивого канонического эквивалента;
  - запрещен, если есть утвержденный canonical alias.
- Legacy names допускаются только в compatibility maps в ограниченное окно миграции.

### 5) Partitioning guidelines

- Bronze: append-only, без аналитических оптимизаций, сохраняем сырой след.
- Silver: партиционирование по стабильным temporal/provider dimensions; запрещено вводить high-cardinality partition keys без доказанного эффекта.
- Gold: партиционирование только по аналитически оправданным срезам и в рамках контрактной стабильности.

______________________________________________________________________

## E) Контроль качества (гейт)

### Что должно быть в CI

1. **Schema diff tests** (Silver и Gold): обнаружение add/remove/rename/type-change.
1. **Golden tests**: фиксированные contract snapshots для ключевых пайплайнов.
1. **Contract compatibility checks**:
   - backward compatibility для minor;
   - explicit breaking flag + migration notes для major.
1. **DQ checks**:
   - coverage transformer→silver→gold,
   - unvalidated fields,
   - dead field detection,
   - alias usage counters.

### Что блокирует merge

- Любой unapproved breaking change без version bump + migration + rollback criteria.
- PK mismatch между pipeline config / transformer / Silver / Gold.
- Новые unvalidated passthrough поля в Silver.
- Пустые/несогласованные contract artifacts для затронутых пайплайнов.

### Как документируем breaking changes

- Обязательные артефакты:
  1. ADR (Decision + Consequences + Migration + Compatibility),
  1. Changelog entry с датой cutover и сроком поддержки legacy,
  1. Runbook update с rollback trigger conditions.
- Без этих 3 артефактов релиз breaking-схемы запрещен.
