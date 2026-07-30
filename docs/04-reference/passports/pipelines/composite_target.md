# `composite_target`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:composite]` | `composite:composite_target` |
| Status | `active` |
| Gold contract | `composite.target v1.0.0` |

## Назначение и обработка данных

Composite pipeline `composite_target` использует seed `chembl_target` и объединяет его с configured dependencies/enrichers.
Join keys, cardinality и source tables берутся из composite configuration; merge и conflict resolution выполняются общей CompositePipelineRunner.
После merge применяется configured cross-validation; исключённые значения направляются в quarantine или nullification branch согласно composite policy.
Результат проходит строгий Gold-контракт `composite.target` и публикует manifest/checkpoint evidence.

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `composite` · `chembl_target` |
| Resource / tables | `silver/chembl/target`, `silver/chembl/target_component`, `silver/chembl/protein_class`, `silver/chembl/target_protein_classification`, `silver/uniprot/idmapping`, `silver/uniprot/protein` |
| Filters | `chembl_target_component`: no condition; `chembl_protein_class`: no condition; `chembl_target_protein_classification`: no condition; `uniprot_idmapping`: target_id IS NOT NULL; `uniprot_protein`: no condition |

## Silver и Data Quality

- Normalization profile: `composite.target`.
- Partitioning: —.
- DQ thresholds: soft `0.1`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `composite.target v1.0.0`; strict validation: `True`.
- Write mode: `configured`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run-composite --composite target` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run-composite --composite target --seed-limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run-composite --composite target --use-cached-bronze --dry-run` | Проверяет cached Bronze composite без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline composite_target --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline composite_target --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline composite_target` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Composite Flow

```mermaid
flowchart LR
    Seed["Seed: chembl_target"]
    Input1["chembl_target_component · primary_component_id"]
    Input1 --> Merge
    Input2["chembl_protein_class · protein_classification_id"]
    Input2 --> Merge
    Input3["chembl_target_protein_classification · target_id"]
    Input3 --> Merge
    Input4["uniprot_idmapping · target_id"]
    Input4 --> Merge
    Input5["uniprot_protein · uniprot_accession"]
    Input5 --> Merge
    Merge["Merge: left_outer / seed_priority"]
    Validate["Cross-validation: False"]
    Excluded["Quarantine / nullification"]
    Gold["Gold: composite_target"]
    Seed --> Merge --> Validate
    Validate -->|valid| Gold
    Validate -->|excluded| Excluded
```

## Owner-approved context

Enrich ChEMBL targets with component, classification, mapping, and protein context.

## Evidence

- `composite_config`: `configs/composites/target.yaml`
- `effective_entity_config`: `configs/entities/composite/target.yaml`
- `gold_contract`: `configs/contracts/composite/target.yaml`
- `composite_cli`: `src/bioetl/interfaces/cli/commands/run_composite.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
