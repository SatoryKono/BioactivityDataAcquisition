# Консолидированный план рефакторинга схем BioETL

**Дата:** 2026-02-18
**Автор:** Аудит 4 веток планов + верификация по кодовой базе main

**Источники:**

| Ветка | Документ | Кол-во backlog items | ADR кандидатов |
|-------|----------|---------------------|----------------|
| `codex/create-architectural-change-plan-for-bioetl` | `docs/plans/schema-audit-implementation-plan-2026-02-18.md` | 12 (SCH-001…012) | 5 |
| `codex/…-f7msdt` | `docs/plans/bioetl-schema-change-architecture-plan-2026-02-18.md` | 12 (BLG-001…012) | 5 |
| `codex/…-8x3vzl` | `docs/audits/schema-change-plan-from-audits-2026-02-18.md` | 11 (SC-001…011) | 5 |
| `codex/…-6v6zla` | `docs/05-operations/verification/schema-audit-change-plan-2026-02-18.md` | 12 (CB-01…12) | 7 |

---

## 0. Ключевые наблюдения

### 0.1 Код идентичен

Все 4 ветки содержат **идентичные изменения кода** (`src/`, `tests/`). Различаются только план-документы и их расположение в дереве `docs/`.

### 0.2 Верификация утверждений планов

При сверке с кодовой базой `main` обнаружены **фактические расхождения** с заявлениями во всех 4 планах:

| Утверждение планов | Реальность на main | Verdict |
|---|---|---|
| `gene_names` отсутствует в Silver schema UniProt | **Присутствует** (`silver.py:236`, `pa.list_(pa.string())`) | FALSE |
| `issue` отсутствует в Silver schema SemanticScholar | **Присутствует** (`silver.py:783`, `pa.string()`) | FALSE |
| Python↔YAML drift в `FIELD_TO_GROUP_MAPPING` | **Синхронизированы** (167 entries совпадают) | FALSE |
| CrossRef: отсутствуют трансформеры для `content_domain_*`, `issn_print/electronic`, `published_print/online` | **Все трансформеры реализованы** в `crossref/extractors.py` и `crossref/transformer.py` | FALSE |
| `pharmaceutical_use`, `publication_count` — dead fields | **Активны**: присутствуют в entity, имеют валидацию в schemas | UNVERIFIED — нужно проверить, заполняются ли реально трансформером |
| Ghost base_names (doi, pmid, year, etc.) рядом с canonical | **Подтверждено**: `field_groups/publication.yaml` содержит оба варианта | TRUE |
| `content_hash` в группе TRASH | **Подтверждено**: `publication.yaml:548`, группа `trash` | TRUE |
| Tissue PK mismatch: Gold `tissue_chembl_id` vs entity/Silver `tissue_id` | **Подтверждено**: Gold `chembl.py:645` vs Silver `silver.py:569` | TRUE |
| `action_type_action_type` в Activity | **Подтверждено**: rename mapping в `activity_transformer.py:185` | TRUE |
| `document_year`/`document_journal` legacy naming | **Подтверждено**: FieldSpec renames в `activity_transformer.py:119,125` | TRUE |
| Пустые `column_groups: []` в 15+ YAML schema файлах | **Подтверждено**: 15 файлов в `configs/schemas/` | TRUE |
| `subject_topics` inconsistency (string vs list) | **Подтверждено**: OpenAlex `pa.string()` vs другие `pa.list_` | TRUE |

### 0.3 Уникальные находки по веткам

| Ветка | Уникальные items | Ценность |
|-------|-----------------|----------|
| Branch 1 (base) | — (базовый publication-focused набор) | Baseline |
| Branch 2 (f7msdt) | Tissue PK (BLG-010), CrossRef transformer gaps (BLG-011), Empty column_groups governance (BLG-012) | BLG-010 подтверждён, BLG-011 ложный, BLG-012 подтверждён |
| Branch 3 (8x3vzl) | Single source of truth schema (SC-008), Contract versioning strategy (SC-009) | Оба архитектурно ценные |
| Branch 4 (6v6zla) | Taxonomy types Activity/CellLine (CB-01/02), action_type rename (CB-03), document naming (CB-04), PubChem fingerprint (CB-09) | CB-01/02 новая тема, CB-03/04 подтверждены, CB-09 minor |

---

## A) Консолидированный Change Backlog

Нумерация `RF-SCH-*` (Refactoring — Schema).

### Tier 1: Подтверждённые и критичные

| ID | Pipeline/Global | Изменение | Уровень | Источник веток | Подтверждено кодом |
|---|---|---|---|---|---|
| RF-SCH-001 | composite/publication | Удалить ghost base_names (`doi`, `pmid`, `pmc_id`, `year`, `document_chembl_id`) из `field_groups/publication.yaml`, оставить canonical `publication_*` | Refactor | ALL (SCH-001, BLG-001, SC-001, CB-*) | ✅ `publication.yaml` содержит обе формы |
| RF-SCH-002 | composite/publication | Консолидация MeSH/keywords/topics: оставить `subject_mesh`, `subject_keywords`, `subject_topics` как canonical | Refactor | ALL (SCH-002, BLG-002, SC-003) | ✅ Дублирование подтверждено |
| RF-SCH-003 | composite/publication | Разгрузить `id_and_status`: перенести `fields_of_study` → terms/topics, `publication_type` → publication_types | Refactor | ALL (SCH-003, BLG-003, SC-004) | ✅ Перегрузка группы подтверждена |
| RF-SCH-004 | composite/publication | Переклассифицировать `content_hash`: TRASH → system-metadata (`include_in_gold=false`) | Refactor | ALL (SCH-005, BLG-004, SC-005) | ✅ `content_hash` в TRASH группе |
| RF-SCH-005 | composite/publication | Journal naming cleanup: deprecate legacy `journal_full_title`, `journal_title`, `journal_abbrev` | Breaking | Branches 1,3 (SCH-004, SC-006) | ⚠️ Требует отдельного аудита journal полей |
| RF-SCH-006 | composite/publication | Решение по `language`, `license_url`, `is_oa`, `oa_status`, `open_access_url`: promote в Gold или оставить вне | Breaking | ALL (SCH-006, BLG-005, SC-007) | ✅ Сейчас в TRASH, решение необходимо |
| RF-SCH-007 | chembl/tissue | PK mismatch: Gold `tissue_chembl_id` → align с entity/Silver `tissue_id` | Breaking | Branch 2 (BLG-010) | ✅ Gold `chembl.py:645` vs Silver `silver.py:569` |
| RF-SCH-008 | chembl/activity | Унификация taxonomy type `target_taxonomy_id` (string→float/nullable int) в Silver/Gold | Breaking | Branch 4 (CB-01) | ⚠️ Требует отдельной верификации типов |
| RF-SCH-009 | chembl/cell_line | Выровнять Silver тип `cell_source_taxonomy_id` с Gold (`int`→`float`) | Breaking | Branch 4 (CB-02) | ⚠️ Требует отдельной верификации типов |
| RF-SCH-010 | chembl/activity | Формализовать rename `action_type_action_type` → `action_type` в schemas/configs (сейчас только в transformer) | Refactor | Branch 4 (CB-03) | ✅ Rename в `activity_transformer.py:185` |
| RF-SCH-011 | chembl/activity | Нормализовать `document_year`→`publication_year`, `document_journal`→`journal` в schemas/Gold contracts | Refactor | Branch 4 (CB-04) | ✅ FieldSpec renames в transformer |
| RF-SCH-012 | global/publication | Унифицировать list/JSON типы (`subject_topics` string vs list) между Silver schemas разных провайдеров | Refactor | ALL (SCH-011, BLG-*, SC-*, CB-08) | ✅ `subject_topics` как `pa.string()` в OpenAlex |

### Tier 2: Подтверждённые, но не критичные

| ID | Pipeline/Global | Изменение | Уровень | Источник веток | Подтверждено кодом |
|---|---|---|---|---|---|
| RF-SCH-013 | global/config | Решение по пустым `column_groups: []` в 15 YAML schema файлах: deprecate или populate | Refactor | Branch 2 (BLG-012) | ✅ 15 файлов с пустыми column_groups |
| RF-SCH-014 | global/publication | Единый source of truth: гармонизировать `publication.yaml` и `field_groups/publication.yaml` | Refactor | Branch 3 (SC-008) | ✅ Два параллельных определения |
| RF-SCH-015 | pubchem/compound | Документировать или удалить DTO-only поле `fingerprint` | Low | Branch 4 (CB-09) | ⚠️ Требует верификации |
| RF-SCH-016 | global/dq | Externalize DQ rules для schema drift detection и group policy enforcement | Refactor | ALL (SCH-012, BLG-*, SC-011, CB-12) | ✅ Архитектурно обоснованно |

### Tier 3: Требуют дополнительной верификации (ложные или спорные)

| ID | Pipeline/Global | Утверждение планов | Проблема | Действие |
|---|---|---|---|---|
| ~~RF-SCH-X1~~ | uniprot/protein | `gene_names` отсутствует в Silver schema | **Уже присутствует** на main (`silver.py:236`) | ОТКЛОНЕНО |
| ~~RF-SCH-X2~~ | semanticscholar/publication | `issue` отсутствует в Silver schema | **Уже присутствует** на main (`silver.py:783`) | ОТКЛОНЕНО |
| ~~RF-SCH-X3~~ | crossref/publication | MISSING_TRANSFORMER для 6 полей | **Все трансформеры реализованы** | ОТКЛОНЕНО |
| ~~RF-SCH-X4~~ | global/publication | Python↔YAML drift | **Синхронизированы** (167 entries) | ОТКЛОНЕНО |
| RF-SCH-017 | uniprot/protein | Dead fields `pharmaceutical_use`, `publication_count` | Поля есть в entity и schemas, но неизвестно, заполняются ли трансформером | НУЖНА ВЕРИФИКАЦИЯ: проверить `uniprot/protein_transformer.py` |

---

## B) Консолидированные ADR кандидаты

Из ~22 ADR кандидатов (суммарно по 4 веткам) выделено 7 уникальных тем:

### ADR-SCH-01: Canonical Publication Field Naming and Legacy Alias Sunset

**Покрывает:** ADR-CAND-01 (B1), ADR-C1 (B2), ADR-1 (B3), часть CB-04 (B4)

- **Context:** Ghost base_names (doi/publication_doi, year/publication_year и др.) в field groups создают двойственность и ghost columns.
- **Decision:** Canonical-only naming в field_groups и Gold contracts; legacy names — только compatibility alias на ограниченный период.
- **Migration:** Contract v2 → dual-read alias (2 релиза) → hard removal.
- **Observability:** `legacy_alias_hit_rate`, `unknown_field_in_query`.

### ADR-SCH-02: Field Group Taxonomy Governance (System/TRASH/Topics/OA)

**Покрывает:** ADR-CAND-02 (B1), ADR-C2 (B2), ADR-2 (B3), ADR-5 (B3)

- **Context:** `content_hash` в TRASH; `id_and_status` перегружен; нет system-metadata группы; спорный статус `language`/`license_url`.
- **Decision:** Формализовать группы: `system` (exclude from Gold by policy), `open_access`, `identifiers`, `topics`. Запрет mixed semantics.
- **Migration:** Перегруппировка YAML + policy enforcement + metadata spec v1.

### ADR-SCH-03: Gold Contract Versioning and Breaking Window Policy

**Покрывает:** ADR-CAND-03 (B1), ADR-C3 (B2), ADR-4 (B3), ADR-C03 (B4)

- **Context:** Множественные breaking changes (journal cleanup, PK rename tissue, taxonomy types, OA field promotion).
- **Decision:** Semver для Gold contracts: patch=docs, minor=additive, major=rename/remove. Обязательный dual-service для major.
- **Migration:** Dual-write/read → adoption threshold → cutover.

### ADR-SCH-04: Dead Field Policy (UniProt, PubChem)

**Покрывает:** ADR-CAND-04 (B1), часть BLG-007 (B2), ADR-C04 (B4)

- **Context:** Поля `pharmaceutical_use`, `publication_count` (UniProt) и `fingerprint` (PubChem DTO) — потенциально мёртвые.
- **Decision:** Explicit policy: поле в contract → MUST быть populated трансформером ИЛИ documented exception. Dead → remove с major bump.
- **Pre-requisite:** Верификация population rate через `uniprot/protein_transformer.py`.

### ADR-SCH-05: DQ Rules Externalization

**Покрывает:** ADR-CAND-05 (B1), часть BLG-* (B2), часть SC-011 (B3), ADR-C07 (B4)

- **Context:** Schema drift проявляется как ghost columns, inconsistent типы, missing validation.
- **Decision:** DQ rules в конфиг, исполняемый в CI и post-run. Поэтапный rollout: dry-run → warn → block.

### ADR-SCH-06: Silver Validation Completeness Policy

**Покрывает:** ADR-C4 (B2), часть CB-06/07 (B4)

- **Context:** Некоторые поля проходят в Silver/Gold без валидации.
- **Decision:** Каждая колонка Silver schema MUST иметь явную типизацию и constraint или documented exception.
- **Note:** Частично устарел — `gene_names` и `issue` уже в Silver schema. Актуален для будущих полей.

### ADR-SCH-07: Taxonomy Type Canonicalization (ChEMBL Activity/CellLine)

**Покрывает:** ADR-C01 (B4) — уникален для Branch 4

- **Context:** Type mismatch `target_taxonomy_id` (string vs float) и `cell_source_taxonomy_id` (int vs float) между Silver/Gold.
- **Decision:** Зафиксировать единый nullable-int pattern (`float` в Pandas) с explicit converter policy.
- **Pre-requisite:** Верификация текущих типов на main.

---

## C) Консолидированный Migration Runbook

### Phase 1: Подготовка и верификация

1. **Верифицировать оставшиеся спорные утверждения:**
   - Population rate `pharmaceutical_use`/`publication_count` в UniProt
   - Текущие типы `target_taxonomy_id`/`cell_source_taxonomy_id` в Silver/Gold
   - Полнота journal field audit для RF-SCH-005
2. **Создать schema registry baseline** для затронутых contracts.
3. **Определить version bump стратегию** по каждому breaking item.
4. **Зафиксировать rollback snapshots** Delta tables.

### Phase 2: Non-breaking refactoring (Tier 1 Refactor items)

**Порядок:** RF-SCH-003 → RF-SCH-004 → RF-SCH-010 → RF-SCH-011 → RF-SCH-012 → RF-SCH-014

1. Разгрузить `id_and_status` (RF-SCH-003) — перенос полей между группами, без изменения колонок.
2. Переклассифицировать `content_hash` (RF-SCH-004) — ввести system group.
3. Формализовать `action_type_action_type` rename в schemas/configs (RF-SCH-010).
4. Нормализовать `document_year`/`document_journal` в Gold contracts (RF-SCH-011).
5. Унифицировать `subject_topics` тип (RF-SCH-012).
6. Гармонизировать dual publication schema definitions (RF-SCH-014).

### Phase 3: Breaking changes (contract v2)

**Порядок:** RF-SCH-001 → RF-SCH-002 → RF-SCH-007 → RF-SCH-005 → RF-SCH-006

1. **Ghost base_names cleanup (RF-SCH-001):** contract v2, dual-read aliases на 2 релиза.
2. **MeSH/keywords consolidation (RF-SCH-002):** canonical `subject_*` only.
3. **Tissue PK alignment (RF-SCH-007):** Gold major bump, dual-write PK alias.
4. **Journal naming (RF-SCH-005):** после отдельного аудита — contract v2 с deprecation window.
5. **OA fields decision (RF-SCH-006):** ADR → promote или exclude.

### Phase 4: Taxonomy и DQ

1. **Taxonomy type fix (RF-SCH-008, RF-SCH-009):** после верификации — REBUILD Silver+Gold.
2. **Dead field resolution (RF-SCH-017):** после верификации — populate или remove.
3. **DQ externalization (RF-SCH-016):** dry-run → warn → block.

### Phase 5: Governance cleanup

1. **Empty column_groups (RF-SCH-013):** ADR decision — activate или deprecate.
2. **PubChem fingerprint (RF-SCH-015):** document или remove.

### Cutover + Rollback

**Cutover критерии:**
- 0 critical schema drift
- Contract compatibility checks green
- Legacy usage < 5%
- DQ hard-threshold violations = 0

**Rollback критерии:**
- Рост contract validation failures > SLO
- Критичные DQ hard-fail всплески
- Невозможность чтения Gold API у downstream consumers

**Rollback действия:**
- Pin consumers на предыдущую contract version
- Остановить публикацию новых partitions в vNext
- Восстановить Delta snapshots

---

## D) Standardization Pack (принят из всех 4 планов — консенсус)

### 1) Unified OutputMetadata (обязательный минимум)

- `run_id: str`
- `run_type: str`
- `provider: str`
- `entity: str`
- `schema_version: str`
- `ingestion_ts: timestamp`
- `content_hash: str | None` (system metadata, не business field)
- `dq_status: str`
- `dq_error_count: int`
- `record_count: int`

### 2) Unified Key Strategy

- Silver merge key: `[provider, entity, canonical_business_id]`
- Gold PK: provider-scoped canonical key
- Для rename PK — только через breaking versioned migration
- Запрет implicit coalesce нескольких IDs как surrogate key

### 3) Content Hash Standard

- Алгоритм: `sha256(provider + canonical_json(record))`
- Canonicalization: NaN/Inf→null, float→round(10), date→YYYY-MM-DD, string→strip(), deterministic key ordering
- Exclude: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`
- Null handling: None → explicit `null`

### 4) Naming Standards

- Canonical-first: `publication_doi`, не `doi`
- Provider-qualified: только когда поле source-specific
- Legacy names: только в compatibility alias maps, ограниченный срок

### 5) Partitioning Guidelines

- Bronze: append-only, без оптимизаций
- Silver: `year={YYYY}/month={MM}/`, low-cardinality dimensions
- Gold: аналитически оправданные срезы
- Запрет: high-cardinality partition keys без ADR

---

## E) Контроль качества

### CI gates (консенсус всех 4 планов)

1. **Schema diff tests** — Silver/Gold, additive vs breaking classification
2. **Golden tests** — snapshot Gold output для ключевых pipelines
3. **Contract compatibility checks** — backward-compat для minor, explicit breaking flag для major
4. **DQ checks** — alias collision, missing Silver validation, Python↔YAML parity, dead field detection

### Merge blockers

- Unapproved breaking schema diff без version bump
- Ghost columns (legacy+canonical пара активна одновременно)
- PK mismatch между config/transformer/Silver/Gold
- DQ hard-threshold violation (>20%)
- Отсутствие ADR + changelog + migration notes для breaking changes

---

## F) Рекомендации

### По выбору ветки-основы

**Ни одна из 4 веток не может быть принята as-is** из-за ложных утверждений. Рекомендуется:

1. Использовать **этот консолидированный документ** как единственный источник истины для планирования.
2. **Код из любой ветки** (идентичен) может быть cherry-picked, но требует отдельного review — изменения затрагивают Silver schemas (`silver.py`), domain config (`pipeline.py`, `storage.py`), factories, и Gold writer.
3. **Не мержить план-документы** из отдельных веток — они содержат фактические ошибки.

### По приоритизации

1. **Начать с Phase 2** (non-breaking refactoring) — низкий риск, высокая ценность.
2. **RF-SCH-007 (tissue PK)** — изолированный breaking change, можно сделать раньше.
3. **RF-SCH-001 (ghost base_names)** — ключевой cleanup, но требует coordination с downstream.
4. **ADR-SCH-03 (contract versioning)** — принять ДО начала breaking changes.
5. **Верификация UniProt dead fields** — до принятия решений по RF-SCH-017.

### По структуре документации

Все 4 ветки размещают план в разных директориях. Рекомендуемое расположение: `docs/plans/` (как в ветках 1 и 2) — это де-факто стандарт для планов в проекте.
