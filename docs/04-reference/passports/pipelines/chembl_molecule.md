# `chembl_molecule`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_molecule` |
| Status | `active` |
| Gold contract | `chembl.molecule v1.0.0` |

## Назначение и обработка данных

Extract molecules/compounds from ChEMBL API. Источник — `chembl.molecule.curated` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: inorganic_flag=0; molecule_type=Small molecule; structure_type=MOL; molecule_id=IDs from data/input/molecule.csv column molecule_chembl_id; CLI may override the input CSV.
В business-проекцию входят `molecule_id`, `pref_name`, `max_phase`, `structure_type`, `molecule_type`, `first_approval`, `therapeutic_flag`, `oral` и ещё 44 полей.
Silver использует профиль `chembl.molecule` и проверяет обязательные поля `molecule_id`, `molecule_type`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.molecule`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl.molecule.curated` |
| Resource / tables | `molecule` |
| Filters | `inorganic_flag`: 0; `molecule_type`: Small molecule; `structure_type`: MOL; `molecule_id`: IDs from data/input/molecule.csv column molecule_chembl_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (52 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.molecule`.
- Partitioning: `molecule_type`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.molecule v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_molecule` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_molecule --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_molecule --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_molecule --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_molecule --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_molecule` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl.molecule.curated"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.molecule + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.molecule (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/molecule.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/molecule.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
