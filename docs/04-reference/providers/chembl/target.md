______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Target

**Имя пайплайна:** `chembl_target`
**Провайдер:** `chembl`
**Сущность:** `target`

______________________________________________________________________

## 1. Что делает пайплайн

`chembl_target` нормализует биологические мишени ChEMBL в Silver-модель
`Target`, включая агрегирование target components и derived organism metadata.

Source of truth:

- `configs/entities/chembl/target.yaml`
- `src/bioetl/application/pipelines/chembl/target_transformer.py`
- `src/bioetl/domain/schemas/chembl/target.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`

______________________________________________________________________

## 2. Конфигурация

Текущий pipeline config задаёт:

- `quality.entity_field_validations` для `target_id`, `target_type`, `organism`, `tax_id`
- `quality.entity_cross_field_validations`: `target_id` + `pref_name`
- `filters.extraction_params`:
  - `target_type: SINGLE PROTEIN`
  - `organism__isnull: false`
  - `tax_id__isnull: false`
- `filters.silver_filters.required_fields`:
  - `target_id`
  - `pref_name`
  - `organism`
- `filters.gold_filters`:
  - `target_type = SINGLE PROTEIN`
  - list-based checks for `component_accessions`, `component_ids`, `component_types`

______________________________________________________________________

## 3. Silver surface

### 3.1. Обязательные поля

Current Silver contract требует:

| Поле        | Где закреплено                  |
| ----------- | ------------------------------- |
| `target_id` | YAML required + Arrow + Pandera |
| `pref_name` | YAML required + Arrow + Pandera |
| `organism`  | YAML required + Arrow + Pandera |

`target_type` участвует в filters/partition semantics, но остаётся nullable в
Arrow/Pandera и не считается обязательным полем записи на уровне текущего
Silver schema.

### 3.2. Компоненты мишени

Трансформер читает `target_components`, агрегирует базовые списки и затем
сериализует их в canonical JSON string surface:

- `component_accessions`
- `component_ids`
- `component_types`
- `component_descriptions`
- `component_relationships`

Это не `list[...]` поля в Silver-таблице. И Arrow schema, и Pandera schema
ожидают здесь строки.

### 3.3. Дополнительные derived-поля

`TargetTransformer` также формирует:

- `primary_component_id` из первого элемента `component_ids`
- `taxonomy_id` как нормализованную форму входного `tax_id`
- `organism_class` как hash-governed profile-owned derived field из `organism` + `taxonomy_id`
- `description` из `target_description` или fallback `description`
- `downgraded` как bool-нормализацию входного значения
- `target_components`, `target_component_synonyms`, `cross_references`, `pipeline_stages` как JSON-строки
- `target_protein_synonyms`, `target_gene_synonyms`, `target_ec_numbers` как pipe-delimited derived-поля с sentinel `unknown`
- `target_xref_iuphar_ids`, `target_xref_pdb_ids`, `target_xref_go_component`, `target_xref_go_function`, `target_xref_go_process`, `target_xref_reactome_ids` как pipe-delimited xref-derived поля с sentinel `unknown`

### 3.4. Derived synonym projection

Из nested `target_components[].target_component_synonyms[]` runtime дополнительно
проецирует три scalar-поля:

- `target_protein_synonyms` ← `syn_type = UNIPROT`
- `target_gene_synonyms` ← `syn_type = GENE_SYMBOL` и `GENE_SYMBOL_*`
- `target_ec_numbers` ← `syn_type = EC_NUMBER`

Правила нормализации:

- `syn_type` сравнивается после `str(value).strip().upper()`
- `component_synonym` игнорируется, если `null` / пустой / whitespace-only
- значения проходят `strip()` и сохраняют исходный internal case
- символ `|` экранируется как `\|`
- dedupe идёт по нормализованному значению с first-seen ordering, без сортировки
- при отсутствии значений возвращается literal `unknown`

Forensic boundary для xrefs остаётся прежней:

- `target_component_synonyms` и `cross_references` сохраняют агрегированные raw JSON строки для аудита
- xref-derived scalar-поля формируются только из whitelisted `xref_src_db` значений; всё остальное сохраняется только в `cross_references`
- derived scalar-поля используются для аналитического Silver/Gold surface и hash-governed replay
- `cross_references` обрабатывает неизвестные/нестандартные `xref_src_db` как warn-only в DQ, не нарушая форензику

Nested `cross_references[].xref_src_db` namespaces are runtime-governed via
the shared registry `configs/vocab/chembl_reference_sources.yaml`; malformed JSON or unknown source namespaces are logged as warn by DQ validator and preserved for raw forensic payloads.

Текущий runtime boundary намеренно разделён так:

- transformer only extracts raw/provider-facing source fields;
- domain normalization profile детерминированно вычисляет `organism_class`
  через shared organism-classification policy перед hash/DQ/contract checks.

Документация не фиксирует literal-формулу `entity_id`; identity/content hash
вычисляются базовым ChEMBL transformer/runtime слоем.

______________________________________________________________________

## 4. Валидация

### 4.1. Arrow schema

Silver Arrow schema определяется в
`src/bioetl/infrastructure/schemas/silver_chembl_core.py` как
`CHEMBL_TARGET_SCHEMA`.

### 4.2. Pandera schema

Silver Pandera schema определяется в
`src/bioetl/domain/schemas/chembl/target.py` как `TargetSchema`.

Обе схемы отражают строковый contract для component/xref/synonym payloads.
Это включает forensic JSON field `target_component_synonyms` и три pipe-delimited
derived synonym поля.

______________________________________________________________________

## 5. CLI

```bash
bioetl run --pipeline chembl_target
bioetl run --pipeline chembl_target --limit 500
bioetl run --pipeline chembl_target --run-type rebuild
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент      | Путь                                                            |
| -------------- | --------------------------------------------------------------- |
| Конфигурация   | `configs/entities/chembl/target.yaml`                           |
| Трансформер    | `src/bioetl/application/pipelines/chembl/target_transformer.py` |
| Сущность       | `src/bioetl/domain/entities/chembl_structures_foundation.py`    |
| Arrow schema   | `src/bioetl/infrastructure/schemas/silver_chembl_core.py`       |
| Pandera schema | `src/bioetl/domain/schemas/chembl/target.py`                    |

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json)                  |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                                    |
| ----------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                    |
| Runtime alignment | Pass   | Config/schema/transformer paths задокументированы в разделах `Конфигурация`, `Валидация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json)                                     |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                       |

## API Compliance

### Rate limits & retries

Официальная ChEMBL REST Web Services documentation не публикует числовой лимит запросов. EMBL-EBI Terms of Use разрешают ограничивать или отзывать доступ, если использование мешает работе сервиса. Клиент SHOULD использовать консервативный rate limiting и экспоненциальный backoff; точный retry budget — [неуточнено].

### 429 handling policy

Явная HTTP 429 policy в доступной официальной документации ChEMBL — [неуточнено]. При признаках throttling или блокировки клиент SHOULD снижать частоту запросов и прекращать burst-нагрузку.

### Authentication model

Read-only web services документированы как открытые REST endpoints; обязательная аутентификация для чтения в официальной документации не указана.

### ToS URL

- https://www.ebi.ac.uk/about/terms-of-use

### Data license

ChEMBL data are available under the Creative Commons Attribution-ShareAlike 3.0 Unported license (CC BY-SA 3.0).

### Personal data notes

Наборы данных ChEMBL по своей природе не ориентированы на персональные данные. EMBL-EBI Privacy Notice описывает обработку служебных данных доступа и журналов безопасности; API-specific guidance по персональным данным — [неуточнено].

### Official sources

- [ChEMBL REST Web Services](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL homepage / license statement](https://www.ebi.ac.uk/chembl/)
- [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use)
- [EMBL-EBI Privacy Notice](https://www.ebi.ac.uk/about/privacy-notice)
