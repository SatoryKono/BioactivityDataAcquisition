# `composite_molecule`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:composite]` | `composite:composite_molecule` |
| Status | `active` |
| Gold contract | `composite.molecule v1.0.0` |

## Назначение и обработка данных

Composite pipeline `composite_molecule` использует seed `chembl_molecule` и объединяет его с configured dependencies/enrichers.
Join keys, cardinality и source tables берутся из composite configuration; merge и conflict resolution выполняются общей CompositePipelineRunner.
После merge применяется configured cross-validation; исключённые значения направляются в quarantine или nullification branch согласно composite policy.
Результат проходит строгий Gold-контракт `composite.molecule` и публикует manifest/checkpoint evidence.

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `composite` · `chembl_molecule` |
| Method / endpoint | — · — |
| Resource / tables | `silver/chembl/molecule`, `silver/pubchem/compound` |
| Filters | `pubchem_compound`: inchi_key IS NOT NULL |

## Silver и Data Quality

- Normalization profile: `composite.molecule`.
- Partitioning: —.
- DQ thresholds: soft `0.1`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `composite.molecule v1.0.0`; strict validation: `True`.
- Write mode: `configured`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run-composite --composite molecule` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run-composite --composite molecule --seed-limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run-composite --composite molecule --use-cached-bronze --dry-run` | Проверяет cached Bronze composite без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline composite_molecule --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline composite_molecule --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline composite_molecule` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Composite Flow

```mermaid
flowchart LR
    Seed["Seed: chembl_molecule"]
    Input1["pubchem_compound · inchi_key, canonical_smiles"]
    Input1 --> Merge
    Merge["Merge: left_outer / seed_priority"]
    Validate["Cross-validation: False"]
    Excluded["Quarantine / nullification"]
    Gold["Gold: composite_molecule"]
    Seed --> Merge --> Validate
    Validate -->|valid| Gold
    Validate -->|excluded| Excluded
```

## Owner-approved context

Enrich the ChEMBL molecule seed with compatible external compound facts.

## Evidence

- `composite_config`: `configs/composites/molecule.yaml`
- `effective_entity_config`: `configs/entities/composite/molecule.yaml`
- `gold_contract`: `configs/contracts/composite/molecule.yaml`
- `composite_cli`: `src/bioetl/interfaces/cli/commands/run_composite.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
