# `pubchem_compound`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:pubchem_compound` |
| Status | `active` |
| Gold contract | `pubchem.compound v1.0.0` |

## Назначение и обработка данных

Pipeline for ingesting PubChem compounds. Источник — `pubchem:compound` на `https://pubchem.ncbi.nlm.nih.gov/rest/pug`; применяемые extraction/input filters: smiles=IDs from data/input/molecule.csv column canonical_smiles; CLI may override the input CSV.
В business-проекцию входят `molecule_id`, `canonical_smiles`, `isomeric_smiles`, `inchi`, `inchi_key`, `standardized_canonical_smiles`, `standardized_isomeric_smiles`, `standardized_inchi` и ещё 40 полей.
Silver использует профиль `pubchem.compound` и проверяет обязательные поля `molecule_id`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `pubchem.compound`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `pubchem:compound` |
| Resource / tables | `compound` |
| Filters | `smiles`: IDs from data/input/molecule.csv column canonical_smiles; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (48 fields) |

## Silver и Data Quality

- Normalization profile: `pubchem.compound`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `pubchem.compound v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline pubchem_compound` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline pubchem_compound --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline pubchem_compound --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline pubchem_compound --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline pubchem_compound --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline pubchem_compound` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["pubchem:compound"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: pubchem.compound + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: pubchem.compound (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/pubchem/compound.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/pubchem/compound.yaml`
- `provider_config`: `configs/providers/pubchem.yaml`
