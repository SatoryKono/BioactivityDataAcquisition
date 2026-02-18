# BioETL Schema Audit → Implementation Architecture Plan

**Дата:** 2026-02-18
**Источник входных рисков:** `composite-schemas-audit-2026-02-17`, `schema-review-2026-02-17`
**Назначение:** перевод аудита схем в исполнимый backlog + ADR пакет + migration runbook.

______________________________________________________________________

## A) Change Backlog

| ID      | Pipeline/Global              | Изменение                                                                                                                                                | Уровень (Low/Refactor/Breaking) | Impact                                                      | Risk   | Owner role                     | ADR? | Миграция (кратко)                                         | Done criteria                                                                  |
| ------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------- | ------ | ------------------------------ | ---: | --------------------------------------------------------- | ------------------------------------------------------------------------------ |
| SCH-001 | publication/composite        | Удалить ghost base_names: `doi`, `pmid`, `pmc_id`, `year`, `document_chembl_id` из `field_groups/publication.yaml`, оставить canonical (`publication_*`) | Refactor                        | Устраняет двойную семантику и «призрачные» колонки          | Medium | Data Platform Engineer         |   ✅ | Обновить YAML + compatibility aliases в контракте Gold v2 | Schema diff: legacy поля не появляются как отдельные колонки; gold tests green |
| SCH-002 | publication/composite        | Консолидация тройных полей MeSH/keywords/topics: оставить `subject_mesh`, `subject_keywords`, `subject_topics`                                           | Breaking                        | Снимает риск двойного учёта терминов в аналитике            | High   | Domain Data Model Owner        |   ✅ | Gold contract v2, dual-read период для legacy имен        | Contract compatibility check + метрика legacy_field_usage < 1%                 |
| SCH-003 | publication/composite        | Переклассификация overloaded `id_and_status`: перенести `fields_of_study` и `publication_type` в корректные группы                                       | Refactor                        | Улучшает читаемость Gold API и mapping semantics            | Low    | Pipeline Maintainer            |   ✅ | Change in grouping + регенерация field catalogs           | Golden snapshot групп без регрессии строк                                      |
| SCH-004 | publication/composite        | Нормализовать journal naming: legacy `journal_full_title`, `journal_title`, `journal_abbrev` → deprecate/trash; canonical оставить                       | Breaking                        | Снижает 7→4 варианта наименований журнала                   | Medium | Analytics Contract Owner       |   ✅ | Gold v2 с alias map и deprecation window                  | Нет новых legacy полей в Gold; migration notes опубликованы                    |
| SCH-005 | publication/composite        | TRASH/system split: `content_hash` вывести в системный class (`include_in_gold=false`)                                                                   | Refactor                        | Убирает смешение системных и бизнес-полей                   | Medium | Platform Architect             |   ✅ | Добавить system-group policy + merge filter update        | `content_hash` доступен как system metadata, не бизнес-атрибут                 |
| SCH-006 | publication/composite        | Решение по `language`, `license_url`, `is_oa`, `oa_status`, `open_access_url`: если в Gold — только через version bump                                   | Breaking                        | Может изменить API-поверхность Gold для аналитики OA/языков | High   | Product Analytics Owner        |   ✅ | Контракт v2 + dual-write старого/нового представлений     | BI smoke tests + adoption report + rollback query path                         |
| SCH-007 | publication/composite        | Синхронизировать Python `FIELD_TO_GROUP_MAPPING` с YAML (добавить пропущенные canonical/legacy маппинги)                                                 | Low                             | Убирает Python↔YAML drift                                   | Medium | Backend Engineer               |   ❌ | Обновить mapping + unit tests                             | Unit tests по mapping и group loader pass                                      |
| SCH-008 | uniprot/protein              | Dead fields remediation: `pharmaceutical_use`, `publication_count` (либо заполнять, либо удалить из entity+silver)                                       | Breaking                        | Устраняет невалидные ожидания downstream по пустым полям    | High   | UniProt Pipeline Owner         |   ✅ | Contract v2 + backfill/cleanup + changelog                | Поля либо валидно populated, либо полностью удалены с migration note           |
| SCH-009 | uniprot/protein              | Добавить `gene_names` в Silver schema для строгой валидации                                                                                              | Refactor                        | Закрывает дыру в Silver validation                          | Medium | UniProt Pipeline Owner         |   ❌ | Delta schema evolve (add column + constraints soft)       | Silver validation coverage 100% по transformer fields                          |
| SCH-010 | semanticscholar/publication  | Добавить `issue` в Silver schema (сейчас проходит без валидации)                                                                                         | Refactor                        | Уменьшает риск schema drift в Silver                        | Medium | SemanticScholar Pipeline Owner |   ❌ | Delta add column + schema test                            | Поле валидируется в Silver и совпадает с Gold mapping                          |
| SCH-011 | global/publication providers | Унифицировать типы list/json полей (`subject_mesh`, `subject_keywords`, `institution_ids`, и др.) между Silver и Gold                                    | Breaking                        | Снижает runtime-cast ошибки и неоднозначность типов         | High   | Data Contracts Team            |   ✅ | Introduce contract v2 typing + converter/backfill         | Contract tests на типы strict pass на всех провайдерах                         |
| SCH-012 | global/dq                    | Externalize DQ schema checks: dead field detection, missing-in-silver detection, alias collision checks в конфиг                                         | Refactor                        | Системно предотвращает повторение drift                     | Medium | Data Quality Engineer          |   ✅ | DQ config rollout + alerting dashboards                   | DQ rules запускаются в CI и post-run с алертами                                |

______________________________________________________________________

## B) ADR Candidates

### ADR-CAND-01 — Canonical Publication Field Naming and Legacy Alias Sunset

- **Context (проблема из аудита):** Обнаружены legacy+canonical пары как отдельные base_names (`doi/publication_doi`, `pmid/publication_pmid`, `year/publication_year`) и ghost columns после alias resolution.
- **Decision:** В Gold/Silver контрактах canonical-only naming; legacy имена поддерживаются только как read-alias на ограниченный период.
- **Consequences:** Снижается schema drift и риск double-counting; требуется миграция потребителей с legacy селектов.
- **Migration plan:** Ввести `publication_contract:v2`; dual-read алиасы 2 релиза; затем hard removal legacy.
- **Compatibility notes:** `v1` остаётся доступным в течение deprecation window; changelog с таблицей old→new.
- **Observability:** Метрики `legacy_alias_hit_rate`, `unknown_field_in_query`, алерт при `legacy_alias_hit_rate > 5%` после первой недели.

### ADR-CAND-02 — Publication Field Group Governance (TRASH/System/Open-Access)

- **Context:** TRASH включает `content_hash` (системное поле) и спорные аналитические поля (`language`, `license_url`); `id_and_status` перегружен несвязанными атрибутами.
- **Decision:** Ввести строгие группы: `system`, `open_access`, `identifiers`, `topics`; запрет на mixed semantics в одной группе.
- **Consequences:** Прозрачнее include/exclude в Gold; изменится структура field catalogs.
- **Migration plan:** Перегруппировка YAML + field catalog regenerate + compatibility view для старых групп.
- **Compatibility notes:** Group-level change не должен менять значение поля; только API-представление и включённость в Gold по версии.
- **Observability:** `gold_group_distribution`, `dropped_by_trash_count`, алерт при аномальном росте dropped columns.

### ADR-CAND-03 — Silver→Gold Contract Versioning for Publication Enrichment Fields

- **Context:** Повышение `language`/`license_url`/OA-полей и унификация list/json типов — потенциальные breaking changes.
- **Decision:** Семантическое версионирование контрактов (`major.minor`), breaking только через major bump + dual-write.
- **Consequences:** Предсказуемые cutover окна, но временно растёт стоимость хранения/поддержки dual datasets.
- **Migration plan:** `gold/publication/v1` и `gold/publication/v2` параллельно 30 дней; автоматические parity-check отчёты.
- **Compatibility notes:** Потребители выбирают версию явно; дефолт остаётся v1 до финального cutover.
- **Observability:** `contract_version_read_share`, `v1_vs_v2_rowcount_delta`, `type_mismatch_rate`.

### ADR-CAND-04 — Dead Field Policy for UniProt

- **Context:** В UniProt выявлены dead fields (`pharmaceutical_use`, `publication_count`) и поле `gene_names` вне Silver валидации.
- **Decision:** Ввести policy: поле может существовать в Silver/Gold только если оно заполнено extractor/transformer либо вычисляется deterministic rule.
- **Consequences:** Уменьшение «пустых» API-контрактов; потребуется удалить/добавить логику в трансформер.
- **Migration plan:** Для каждого dead field выбрать branch: implement or deprecate; если deprecate — major bump и cleanup backfill.
- **Compatibility notes:** Для удаляемых полей — grace период + nullable compatibility view.
- **Observability:** `dead_field_nonnull_ratio`, `silver_validation_bypass_count`, алерт если nonnull_ratio < 0.1% 7 дней.

### ADR-CAND-05 — DQ Rule Externalization for Schema Drift Control

- **Context:** Drift проявляется как несоответствие Python↔YAML и поля, проходящие в Gold без Silver validation (`issue`, `gene_names`).
- **Decision:** Вынести schema-DQ правила в конфиг, исполняемый в CI и post-run.
- **Consequences:** Меньше ручных регрессий; требуется поддержка конфигураций правил по пайплайнам.
- **Migration plan:** Этапно подключить publication → uniprot → остальные провайдеры.
- **Compatibility notes:** На первом этапе правила в warning-mode, затем часть правил становится blocking.
- **Observability:** `schema_drift_events`, `dq_rule_failures_by_pipeline`, `new_unmapped_fields_count`.

______________________________________________________________________

## C) Migration Runbook

### 1. Подготовка

1. Создать/обновить schema registry записи для affected contracts (`publication`, `uniprot_protein`, `semanticscholar_publication`).
1. Для каждого breaking-change выполнить version bump:
   - Publication naming/type/group changes → `publication_gold:v2`.
   - UniProt dead field removal/semantic rework → `uniprot_protein_gold:v2`.
1. Подготовить dual-write/dual-read:
   - Silver: сохранить физический layout без удаления колонок до cutover.
   - Gold: публиковать `v1` и `v2` параллельно там, где breaking.
1. Freeze window: запрет на новые schema изменения во время миграции (кроме hotfix).

### 2. Silver migration (Delta)

1. **Add columns:** добавить недостающие validated поля (`gene_names`, `issue`) через Delta schema evolution.
1. **Type fix:** унифицировать list/json representation по решению ADR (например, canonical JSON string в Silver).
1. **Backfill:** пересчитать исторические партиции только для затронутых колонок (partition-pruned backfill).
1. **Constraints:** добавить soft-constraints/expectations на canonical поля (`publication_*`) и запрет неканоничных дублей.
1. **Repartition check:** подтвердить, что новые поля не меняют partition strategy (без high-cardinality partitions).

### 3. Gold migration (контракты)

1. Ввести `v2` контракты с strict validation и explicit aliases policy.
1. Breaking window:
   - T0: запуск dual-write (`gold/.../v1`, `gold/.../v2`).
   - T0+14d: блокировка новых consumer onboarding на v1.
   - T0+30d: cutover на v2 как default.
1. Для удаления/переименования полей подготовить mapping matrix old→new и SQL/view shims.
1. Контрактные проверки:
   - backward compatibility для non-breaking изменений;
   - explicit fail для breaking без major bump.

### 4. DQ externalization rollout

1. Добавить правила в DQ config:
   - duplicate canonical/legacy detection;
   - silver_vs_gold field presence checks;
   - python_mapping_vs_yaml parity.
1. Режимы rollout:
   - Week 1: warn-only;
   - Week 2+: blocking для critical drift (ghost columns, missing Silver validation).
1. Мониторинг:
   - dashboard по drift events;
   - alerting threshold: hard fail при >20% DQ schema errors, warning при >5%.

### 5. Cutover + rollback plan

1. **Cutover criteria:**
   - v2 read share ≥ 90%;
   - parity-check rowcount/hash в пределах согласованных допусков;
   - нет critical DQ alerts 7 дней.
1. **Rollback criteria (обязательные для breaking):**
   - рост pipeline failures после релиза > baseline + 30%;
   - contract validation failures > 5% батчей;
   - критичные BI-дашборды не проходят smoke tests.
1. **Rollback action:** вернуть default read path на v1, остановить v2 writes, сохранить artifacts для RCA.

______________________________________________________________________

## D) Standardization Pack (целевая унификация)

### 1) Unified OutputMetadata fields

Обязательный минимальный набор (все слои):

- `run_id: str`
- `layer: Literal[bronze,silver,gold]`
- `provider: str`
- `entity: str`
- `record_count: int`
- `schema_version: str`
- `write_started_at: datetime`
- `write_completed_at: datetime`
- `content_hash: str | None` (system-only semantics)
- `dq_summary: dict[str, int] | None`

Принцип: бизнес-поля не смешиваются с системными; `content_hash` не классифицируется как TRASH.

### 2) Unified Key Strategy

- Bronze: ключ не нормализуется (raw append-only).
- Silver: merge key = `provider + entity + natural_id` (или provider-qualified ID для publication).
- Gold: PK определяется контрактом, provider scoping обязателен, если идентификаторы не глобально уникальны (`publication_id` без provider запрещён).
- Для cross-provider consolidation использовать explicit surrogate key, а не implicit coalesce нескольких IDs.

### 3) Content hash standard

- Алгоритм: `sha256(provider + canonical_json(record))`.
- Canonicalization:
  - NaN/Inf → `null`
  - float → round(10)
  - date → `YYYY-MM-DD`
  - string → `strip()`
  - deterministic ordering keys
- Exclude list: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.
- Null handling: `None` сериализуется явно как `null`, не пропускается.

### 4) Naming стандарты

- Canonical public contract fields: `snake_case`, семантически явные (`publication_doi`, не `doi`).
- Provider-qualified policy:
  - **Нужно:** когда значение provider-specific или не имеет кросс-провайдерной эквивалентности.
  - **Запрещено:** дублировать canonical поле provider-префиксом без семантической причины.
- Legacy names допускаются только как alias в compatibility layer.

### 5) Partitioning guidelines

- Silver path остаётся `silver/{provider}/{entity}/year={YYYY}/month={MM}/`.
- Gold partitioning — по низкой/средней кардинальности аналитическим измерениям.
- Запрет: partition по высококардинальным полям (`doi`, `publication_id`, hash-поля, массивы) без отдельного ADR с обоснованием стоимости.
- Любое изменение partition key — только через ADR + perf baseline сравнение.

______________________________________________________________________

## E) Контроль качества (гейт)

### Что должно быть в CI

1. **Schema diff tests:** сравнение контрактов `vN` vs `vN+1` с классификацией breaking/non-breaking.
1. **Golden tests:** snapshot Gold output для ключевых pipeline seeds (publication, uniprot, semanticscholar).
1. **Contract compatibility checks:**
   - backward-compatible changes разрешены без major bump;
   - breaking change требует major + migration metadata.
1. **DQ checks:**
   - alias collision;
   - missing Silver validation fields;
   - Python↔YAML mapping parity;
   - dead-field non-null ratio.

### Какие проверки блокируют merge

- Любой breaking schema diff без major version bump.
- Обнаружение ghost columns (legacy+canonical пара активна одновременно).
- Новые поля в Gold без contract changelog и migration notes.
- DQ hard-threshold violation (>20% schema-related errors).

### Как документируем breaking changes

- Обязательные артефакты на PR:
  1. ADR (или ADR-candidate с decision log).
  1. `CHANGELOG` запись с old→new mapping.
  1. Migration note: dual-write период, cutover дата, rollback критерии.
  1. Compatibility matrix (какие клиенты/дашборды затронуты).
