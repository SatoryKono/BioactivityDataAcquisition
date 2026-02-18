# BioETL Schema Audit → Architecture Change Plan

*Дата: 2026-02-18*
*Основание: консолидированные результаты трёх аудитов схем (ветки gFEGo/sRnnM/7Zhjk и последующая верификация schema-review 2026-02-17).*
*Контекст запроса: RID-BIOETL-SCHEMA-AUDIT-20260218-015009 (PROMPT-2).*

______________________________________________________________________

## A) Change Backlog

| ID    | Pipeline/Global                                                        | Изменение                                                                                                         | Уровень (Low/Refactor/Breaking) | Impact                                                   | Risk                                                      | Owner role                       | ADR? | Миграция (кратко)                                                             | Done criteria                                                              |
| ----- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------- | --------------------------------------------------------- | -------------------------------- | ---: | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| CB-01 | chembl/activity                                                        | `target_taxonomy_id`: унификация типа (string → float/nullable int pattern) в Silver/Gold + transformer converter | Breaking                        | Стабильные joins/валидаторы taxonomy в Silver/Gold       | Ошибка coercion/невалидные historical batches             | Data Platform Engineer           |   ✅ | Version bump контракта, REBUILD Activity Silver+Gold, strict schema check     | Новая схема проходит contract+golden; drift=0 по типу                      |
| CB-02 | chembl/cell_line                                                       | `cell_source_taxonomy_id`: выровнять Silver тип с Gold (`int` → `float`)                                          | Breaking                        | Удаление type-mismatch между слоями                      | Несовместимость чтения legacy partition                   | Data Platform Engineer           |   ✅ | Version bump, REBUILD CellLine Silver, пересчёт quality snapshots             | Silver/Gold тип идентичен, DQ type rule зелёный                            |
| CB-03 | chembl/activity + composite/activity                                   | Rename `action_type_action_type` → `action_type` в transformer/schemas/configs                                    | Breaking                        | Снижение redundant naming, упрощение контрактов Gold     | Downstream consumers используют legacy-имя                | Analytics Contract Owner         |   ✅ | Контракт vNext, dual-read alias (ограниченное окно), REBUILD Activity         | Нет legacy-колонки в новых партициях; consumers мигрированы                |
| CB-04 | chembl/activity + publication model                                    | Нормализовать publication context naming: `document_year`/`document_journal` → `publication_year`/`journal`       | Breaking                        | Согласованность Activity с Publication unified naming    | Ломает joins/дашборды на `document_*`                     | Analytics Contract Owner         |   ✅ | Контракт vNext, compatibility view с alias, cutover после window              | Все composite joins используют canonical publication поля                  |
| CB-05 | uniprot/protein                                                        | Устранить dead fields: `pharmaceutical_use`, `publication_count` (либо populate, либо удалить из entity+Silver)   | Refactor                        | Убирает ложные поля и schema noise                       | Неправильный выбор (удалить vs заполнить) повлияет на API | UniProt Pipeline Maintainer      |   ✅ | ADR-решение populate/remove, при remove — minor/major bump по контракту       | Поля либо валидно заполняются, либо отсутствуют во всех слоях              |
| CB-06 | uniprot/protein                                                        | Добавить `gene_names` в Silver schema (сейчас bypass validation)                                                  | Refactor                        | Закрывает «слепую зону» в Silver validation              | Возможны ошибки парсинга list/string                      | UniProt Pipeline Maintainer      |      | Additive column, backfill NULL-safe, DQ rule на формат                        | Поле валидируется Silver schema без bypass                                 |
| CB-07 | semanticscholar/publication                                            | Добавить `issue` в Silver schema (сейчас есть в entity/transformer/Gold, нет в Silver)                            | Refactor                        | Сквозная валидация поля в медальонном потоке             | Низкий: additive                                          | Publication Pipelines Maintainer |      | Additive column, backfill, schema registry update                             | `issue` проходит Silver→Gold без unvalidated pass-through                  |
| CB-08 | openalex/publication + pubmed/publication (global publications typing) | Свести публикационные list-поля к единой contract policy (JSON-string в Silver vs object/list в Gold)             | Refactor                        | Снижает межпровайдерный drift типов                      | Изменение сериализации может затронуть downstream readers | Data Contract Architect          |   ✅ | ADR по list-полям, staged migration Silver serializer + Gold strict validator | Типовые правила одинаковы для всех publication providers                   |
| CB-09 | pubchem/compound                                                       | Удалить/документировать dead DTO-only `fingerprint`                                                               | Low                             | Чище модель, меньше ложных ожиданий                      | Минимальный                                               | PubChem Pipeline Maintainer      |      | Если не используется — cleanup DTO + docs                                     | Нет «мертвых» полей в DTO inventory                                        |
| CB-10 | Global (all source pipelines)                                          | Стандартизовать ключи provider/canonical (`provider_*_id`, `*_id`) и merge keys policy                            | Refactor                        | Единый контракт key strategy для Silver/Gold и composite | Риск collisions при неверном scoping                      | Data Platform Architect          |   ✅ | ADR + phased config migration в composite pipelines                           | Все новые/изменённые пайплайны соответствуют unified key strategy          |
| CB-11 | Global (metadata)                                                      | Унифицировать OutputMetadata обязательный минимум и типы по пайплайнам                                            | Refactor                        | Сопоставимые observability и lineage                     | Риск несовместимости metadata parsers                     | Platform Observability Owner     |   ✅ | Additive first, затем strict contract enforcement                             | Metadata schema одинакова в Bronze/Silver/Gold adapters                    |
| CB-12 | Global (DQ)                                                            | Externalize DQ rules/config rollout (entity/pipeline overrides + мониторинг)                                      | Refactor                        | Предсказуемый DQ governance и drift control              | Ошибки в конфиге могут блокировать ingestion              | Data Quality Owner               |   ✅ | Поэтапный rollout: dry-run → warn → block                                     | DQ правила не хардкодятся в transformers, coverage по критичным полям 100% |

______________________________________________________________________

## B) ADR Candidates

### ADR-C01 — Taxonomy Type Canonicalization for Silver/Gold

- **Title:** Canonical taxonomy type policy (`float` as nullable-int pattern in tabular layers)
- **Context (проблема из аудита):** Type mismatch и неоднозначность taxonomy-полей в ChEMBL Activity/CellLine; критичный drift при смене типа.
- **Decision:** Зафиксировать единый контрактный тип в Silver/Gold и единый converter policy в transformers.
- **Consequences:** Требуется REBUILD затронутых таблиц; повышается стабильность joins и DQ.
- **Migration plan:** Версия контракта ++; dual-write не требуется (типовая миграция с rebuild); backfill historical partitions; strict validation до cutover.
- **Compatibility notes:** Breaking; на время миграции допускается read-compat на legacy snapshots, write только в новую схему.
- **Observability:** Метрики `schema_type_mismatch_count`, `taxonomy_parse_error_rate`, алерт при drift Critical.

### ADR-C02 — Activity Naming Alignment with Publication Unified Model

- **Title:** Replace legacy `document_*` fields in Activity with publication semantic names
- **Context:** В аудите зафиксирован разрыв между Activity (`document_year`, `document_journal`) и publication unified naming (`publication_year`, `journal`).
- **Decision:** Канонизировать Activity на publication naming; legacy имена только во временном compatibility layer.
- **Consequences:** Breaking для downstream, но устраняет дубли семантики и упрощает composite joins.
- **Migration plan:** Contract v2; dual-read/compat view на период migration window; затем удаление legacy aliases.
- **Compatibility notes:** Обязательный период параллельного обслуживания (N релизов/оговорённое окно) для downstream consumers.
- **Observability:** `legacy_field_read_ratio`, `contract_validation_failures`, алерт если legacy usage не снижается.

### ADR-C03 — Action Type Field De-duplication

- **Title:** Remove redundant flatten prefix in `action_type_action_type`
- **Context:** Аудит выявил redundant naming из flatten-политики.
- **Decision:** Canonical поле `action_type`; legacy `action_type_action_type` только как временный alias.
- **Consequences:** Breaking контракт для Activity Gold/API consumers.
- **Migration plan:** Version bump + dual-read alias + rebuild Activity partitions.
- **Compatibility notes:** Обязательный rollback-триггер: рост contract failures после cutover.
- **Observability:** `activity_action_type_null_rate`, `legacy_alias_hits`, `downstream_schema_error_count`.

### ADR-C04 — Dead Field Governance (UniProt/PubChem)

- **Title:** Policy for dead fields: populate-or-remove with explicit ownership
- **Context:** Аудит зафиксировал dead поля (`pharmaceutical_use`, `publication_count`, DTO `fingerprint`).
- **Decision:** Для каждого dead поля принимается явное решение: вычислять/извлекать или удалять из контрактов.
- **Consequences:** Снижение ложных контрактных ожиданий; требуется review downstream usage.
- **Migration plan:** Для remove — major/minor bump по совместимости; для populate — additive rollout + backfill.
- **Compatibility notes:** При remove обязателен changelog + deprecation window (если поле публичное).
- **Observability:** `dead_field_population_rate`, `null_ratio_by_field`, `consumer_access_to_deprecated_fields`.

### ADR-C05 — Unified List/Object Typing for Publication Providers

- **Title:** Cross-provider serialization contract for list-like publication fields
- **Context:** В аудите выявлены типовые расхождения Silver (`Series[str]` JSON) vs Gold (`Series[object]`) в publication pipelines.
- **Decision:** Определить единый serialization policy и strict schema rules для Silver и Gold.
- **Consequences:** Возможны изменения сериализации и контрактов потребителей.
- **Migration plan:** Staged: introduce canonical representation → dual-validation → strict enforcement.
- **Compatibility notes:** При изменении wire-format — breaking, требуется versioned contract.
- **Observability:** `list_field_parse_failures`, `silver_gold_type_divergence_count`, `schema_compatibility_check_status`.

### ADR-C06 — Unified OutputMetadata Contract

- **Title:** OutputMetadata v1: mandatory fields and types across medallion layers
- **Context:** Аудиты/планы фиксируют необходимость унификации metadata и контроля drift.
- **Decision:** Ввести обязательный metadata core contract (см. раздел D).
- **Consequences:** Улучшается lineage/observability; требуется обновление writers/adapters.
- **Migration plan:** Additive fields first, then strict non-null for mandatory set.
- **Compatibility notes:** Additive этап backward-compatible; strict этап может быть breaking для старых writers.
- **Observability:** `metadata_missing_mandatory_count`, `run_id_coverage`, `content_hash_presence_rate`.

### ADR-C07 — DQ Rules Externalization as Default Governance

- **Title:** Externalized DQ config as single source of truth
- **Context:** Аудит выявил/подтвердил потребность консистентного DQ rollout и устранения hardcoded проверок.
- **Decision:** DQ rules/thresholds хранятся в конфиге; pipelines только исполняют.
- **Consequences:** Прозрачное управление качеством, но выше требования к качеству конфигов.
- **Migration plan:** Dry-run mode → warning mode → blocking mode, с owner sign-off на каждый этап.
- **Compatibility notes:** Изменения порогов не должны ломать контракт данных без version/change log.
- **Observability:** `dq_soft_fail_rate`, `dq_hard_fail_rate`, `dq_rule_coverage`, `dq_config_load_errors`.

______________________________________________________________________

## C) Migration Runbook

### 1) Подготовка

1. Зафиксировать scope изменений по backlog (CB-01…CB-12) и классифицировать breaking/non-breaking.
1. Обновить schema registry: создать новые версии Silver/Gold контрактов для каждого breaking-change.
1. Для breaking-имен/форматов включить dual-read/compat layer (где требуется), без закрепления legacy в целевом контракте.
1. Подготовить migration checklist по сущностям: Activity, CellLine, UniProt Protein, Semantic Scholar Publication, publication typing.
1. Определить rollback markers до начала cutover (см. шаг 5).

### 2) Silver migration (Delta)

1. **Additive этап:** добавить новые колонки/типы, не удаляя старые до cutover window.
1. **Type fix:** применить типовые изменения taxonomy полей и публикационных list-полей по утверждённым ADR.
1. **Rename этап:** для полей `action_type_action_type` и `document_*` — создать canonical колонки через deterministic трансформации.
1. **Backfill:** пересчитать historical partitions затронутых сущностей (Activity/CellLine/и др. по backlog).
1. **Constraints:** включить schema constraints + DQ rules на новые поля, убедиться в отсутствии critical drift.
1. **Partition hygiene:** пересоздать/оптимизировать партиции только по low-cardinality полям (без high-cardinality partition explosion).

### 3) Gold migration (контракты)

1. Выпустить versioned Gold contracts для каждого breaking-change (`vNext`).
1. Включить strict validation (schema + nullability + aliases policy) на pre-publish этапе.
1. Задать breaking window (параллельное обслуживание):
   - чтение legacy alias допустимо,
   - запись только в canonical контракт.
1. По завершении окна выключить legacy aliases и зафиксировать major/minor contract versions в docs/changelog.

### 4) DQ externalization rollout

1. Перенести DQ-правила в конфиги для затронутых сущностей.
1. Запуск в dry-run (только метрики), затем warn mode, затем blocking mode.
1. Обязательный мониторинг порогов и алертов до/после каждого этапа.
1. Синхронизировать DQ overrides с contract versions.

### 5) Cutover + rollback plan

1. **Cutover критерии:**
   - 0 critical schema drift,
   - contract compatibility checks зелёные,
   - downstream smoke tests зелёные.
1. **Rollback критерии (обязательные):**
   - рост contract validation failures выше согласованного SLO,
   - критичные DQ hard-fail всплески,
   - невозможность чтения Gold API у целевых потребителей.
1. **Rollback действия:**
   - переключить readers на предыдущую версию контракта,
   - остановить публикацию новых partition в vNext,
   - восстановить последнюю стабильную snapshot/таблицу,
   - открыть post-incident ADR amendment.

______________________________________________________________________

## D) Standardization Pack (целевая унификация)

### 1) Unified OutputMetadata fields

Обязательный минимум (тип):

- `run_id` (string)
- `run_type` (string)
- `provider` (string)
- `entity` (string)
- `source_system` (string)
- `schema_version` (string)
- `ingestion_ts` (timestamp)
- `processed_ts` (timestamp)
- `content_hash` (string)
- `record_source` (string, nullable)
- `dq_status` (string)
- `dq_error_count` (int)
- `pipeline_version` (string)

### 2) Unified Key Strategy

- Канонический бизнес-ключ: `<entity>_id`.
- Provider-ключ всегда сохраняется как `provider_<entity>_id` (или `provider_primary_id` для публикаций).
- Merge keys в Silver: `[provider, <entity>_id]` если есть межпровайдерный overlap.
- Gold API ключи: только canonical names; provider-specific — как атрибуты совместимости, не как public PK.

### 3) Content hash standard

- Алгоритм: `sha256(provider + canonical_json(record))`.
- Каноникализация перед hash:
  - NaN/Inf → `null`
  - float rounding до 10 знаков
  - даты в `YYYY-MM-DD`
  - строки: `strip()`
  - deterministic ordering ключей
- Exclude list: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.
- Null handling: отсутствующие/пустые значения нормализуются единообразно в `null`.

### 4) Naming стандарты

- Базовый стиль: `snake_case`; обязательные суффиксы `*_id`, `*_name`, `*_count`, `is_*`.
- Provider-qualified policy:
  - **Нужно**: когда значение является внешним provider PK/идентификатором (`provider_*_id`).
  - **Запрещено**: для канонических публичных полей Gold API (исключение — явно документированные compatibility aliases).
- Контекстные префиксы допустимы только при реальной коллизии полей в одной записи.

### 5) Partitioning guidelines

- Bronze: append-only по дате инжеста/provider/entity.
- Silver: партиционирование по времени (`year`, `month`) и только low-cardinality контекстам при обосновании.
- Запрет: high-cardinality partition keys (например, raw IDs) без подтверждённой производственной необходимости.
- Любое изменение partition strategy проходит через ADR + benchmark.

______________________________________________________________________

## E) Контроль качества (гейт)

### Что должно быть в CI

1. Schema diff tests (Silver/Gold) с классификацией additive vs breaking.
1. Golden tests на колонки/типы/канонические имена для затронутых пайплайнов.
1. Contract compatibility checks (N vs N-1).
1. DQ checks (soft/hard thresholds) в test fixtures.
1. Drift detection checks по metadata/content-hash/typing.

### Какие проверки блокируют merge

- Любой non-approved breaking schema diff.
- Падение contract compatibility checks.
- DQ hard-fail в regression datasets.
- Несоответствие OutputMetadata mandatory fields.
- Отсутствие обновлённой документации контракта при schema change.

### Документирование breaking changes

- Обязательные артефакты на каждый breaking-change:
  1. ADR (decision + migration + compatibility notes).
  1. Changelog entry с contract version и migration window.
  1. Runbook update с rollback criteria.
  1. Ссылка на verification evidence (schema diff/golden/compat checks).
