# `uniprot_protein`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:uniprot_protein` |
| Status | `active` |
| Gold contract | `uniprot.protein v1.0.0` |

## Назначение и обработка данных

Pipeline for ingesting UniProt proteins. Источник — `uniprot:protein` на `https://rest.uniprot.org`; применяемые extraction/input filters: accession=IDs from data/input/protein.csv column uniprot_id; CLI may override the input CSV.
В business-проекцию входят `accession`, `entry_name`, `entry_type`, `secondary_accessions`, `protein_name`, `protein_short_names`, `protein_alternative_names`, `protein_ec_numbers` и ещё 84 полей.
Silver использует профиль `uniprot.protein` и проверяет обязательные поля `accession`, `organism_scientific`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `uniprot.protein`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `uniprot:protein` |
| Resource / tables | `protein` |
| Filters | `accession`: IDs from data/input/protein.csv column uniprot_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (92 fields) |

## Silver и Data Quality

- Normalization profile: `uniprot.protein`.
- Partitioning: `organism_scientific`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `uniprot.protein v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline uniprot_protein` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline uniprot_protein --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline uniprot_protein --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline uniprot_protein --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline uniprot_protein --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline uniprot_protein` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["uniprot:protein"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: uniprot.protein + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: uniprot.protein (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/uniprot/protein.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/uniprot/protein.yaml`
- `provider_config`: `configs/providers/uniprot.yaml`
