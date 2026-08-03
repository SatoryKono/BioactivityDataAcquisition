______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-23'

______________________________________________________________________

# Пайплайн: ChEMBL Target Protein Classification

**Имя пайплайна:** `chembl_target_protein_classification`
**Провайдер:** `chembl`
**Сущность:** `target_protein_classification`
**Версия схемы:** 2.2.0

______________________________________________________________________

## 1. Описание

Пайплайн публикует relation rows между ChEMBL target/component surface и
иерархией `chembl.protein_class`. Это canonical provider-facing relation surface
для target-level protein-class evidence; standalone `chembl_target` не владеет
summary-полями классификации.

______________________________________________________________________

## 2. Канонические источники

- Конфигурация: `configs/entities/chembl/target_protein_classification.yaml`
- Runtime transformer:
  `src/bioetl/application/pipelines/chembl/target_protein_classification_transformer.py`
- Pipeline spec:
  `docs/04-reference/pipelines/chembl/11-target-protein-classification-spec.md`
- Upstream provider evidence:
  `docs/04-reference/providers/chembl/target-component.md`
- Hierarchy reference:
  `docs/04-reference/providers/chembl/protein-class.md`

______________________________________________________________________

## 3. Ключевые поля

### Identity and relation state

| Поле | Тип | Описание |
| --- | --- | --- |
| `target_id` | `str` | Canonical target identifier |
| `component_id` | `str` | Canonical target-component identifier |
| `leaf_id` | `int` | Leaf protein-class identifier in the resolved hierarchy |
| `classification_status` | `str` | Runtime-governed relation state used in identity and contracts |

### Canonical hierarchy representation

| Поле | Тип | Описание |
| --- | --- | --- |
| `path_ids` | `str` | Hierarchy path IDs |
| `path_names` | `str` | Hierarchy path names |
| `path_labels` | `str` | Hierarchy path labels |
| `depth` | `int` | Resolved hierarchy depth |
| `root_id` | `int` | Root protein-class identifier |
| `is_leaf` | `bool` | Leaf-marker for the resolved class |

### Normalized top-level evidence

| Поле | Тип | Описание |
| --- | --- | --- |
| `canonical_l1` | `str` | Canonical informative L1 class used by downstream composite projection |
| `l1_normalization_status` | `str` | Whether L1 normalization was mapped, unknown, or preserved for audit |
| `l1_mapping_version` | `str` | Versioned mapping surface for deterministic replay |
| `target_type_rule_version` | `str` | Version marker for downstream composite target-type derivation |

Legacy `l1_*` through `l5_*` columns remain backward-compatible projections
derived from the path fields. They are not the source of truth.

______________________________________________________________________

## 4. Boundary Notes

- `chembl_target_protein_classification` is the authoritative relation surface
  for target-level classification evidence.
- `composite_target` derives `target_protein_class_type` from unique
  informative `canonical_l1` values, not directly from the raw nested
  `protein_classifications` payload.
- `unclassified_protein`, `unknown`, and missing informative L1 values are
  preserved for audit but are non-counting for multifunctional classification.
- Runtime composition prepares relation rows from local
  `chembl.target`, `chembl.target_component`, and `chembl.protein_class`
  snapshots; the active pipeline does not perform external runtime lookups
  against a live `/protein_classification` endpoint.

______________________________________________________________________

## 5. Использование CLI

```bash
bioetl run --pipeline chembl_target_protein_classification
bioetl run --pipeline chembl_target_protein_classification --limit 500
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент | Путь |
| --- | --- |
| Конфигурация | `configs/entities/chembl/target_protein_classification.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/target_protein_classification_transformer.py` |
| Pipeline spec | `docs/04-reference/pipelines/chembl/11-target-protein-classification-spec.md` |
| Target provider doc | `docs/04-reference/providers/chembl/target.md` |
| Target component provider doc | `docs/04-reference/providers/chembl/target-component.md` |

______________________________________________________________________

## Contract References

| Артефакт | Ссылка |
| --- | --- |
| Gold contract export | [chembl_target_protein_classification_v2.2.json](../../contracts/gold/chembl_target_protein_classification_v2.2.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль | Статус | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass | Active config, transformer, and published pipeline spec are linked above |
| Contract linkage | Pass | [chembl_target_protein_classification_v2.2.json](../../contracts/gold/chembl_target_protein_classification_v2.2.json) |
| API governance | Pass | See [API Compliance](#api-compliance) |

## API Compliance

### Rate limits & retries

Официальная ChEMBL REST documentation не публикует числовой request limit.
Клиент SHOULD использовать консервативный rate limiting и exponential backoff;
точный retry budget — [неуточнено].

### 429 handling policy

Явная HTTP 429 policy в доступной официальной документации ChEMBL —
[неуточнено]. При признаках throttling клиент SHOULD снижать частоту запросов.

### Authentication model

Read-only ChEMBL REST endpoints документированы как открытые; обязательная
аутентификация для чтения в официальной документации не указана.

### ToS URL

- https://www.ebi.ac.uk/about/terms-of-use

### Data license

ChEMBL data are available under the Creative Commons Attribution-ShareAlike 3.0
Unported license (CC BY-SA 3.0).

### Personal data notes

Наборы данных ChEMBL не ориентированы на персональные данные. EMBL-EBI Privacy
Notice описывает служебные access/logging surfaces; API-specific guidance по
персональным данным — [неуточнено].

### Official sources

- [ChEMBL REST Web Services](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL homepage / license statement](https://www.ebi.ac.uk/chembl/)
- [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use)
- [EMBL-EBI Privacy Notice](https://www.ebi.ac.uk/about/privacy-notice)
