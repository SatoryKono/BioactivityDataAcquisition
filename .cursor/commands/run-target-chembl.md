# /run-target-chembl

**Goal**

Запуск пайплайна targets ChEMBL с корректным CLI.

**Inputs**

- `--output PATH` (required)
- `--config PATH` (optional): `configs/pipelines/chembl/target.yaml`
- `--dry-run` (optional)
- `--profile NAME` (optional)
- `--limit N` (optional)

**Steps**

1) Проверить `configs/pipelines/chembl/target.yaml`
2) Создать выходную директорию
3) Запустить: `bioetl run target_chembl --config configs/pipelines/chembl/target.yaml --output <output> [--limit N] [--dry-run] [--profile NAME]`
4) Убедиться в коде возврата 0
5) Проверить артефакты и `meta.yaml`

**Constraints**

- Детерминизм, Pandera-валидация, UnifiedLogger
- Enrichment адаптеры через UnifiedAPIClient

**Outputs**

- `data/output/target/`, `meta.yaml`, QC, логи

**References**

- `configs/pipelines/chembl/target.yaml`

