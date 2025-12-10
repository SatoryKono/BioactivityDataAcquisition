# /run-assay-chembl

**Goal:** Запуск пайплайна assay ChEMBL через стандартный CLI.

**Inputs**

- `--output PATH` (required)
- `--config PATH` (optional): `configs/pipelines/chembl/assay.yaml`
- `--dry-run` (optional)
- `--profile NAME` (optional)
- `--limit N` (optional)

**Steps**

1) Проверить `configs/pipelines/chembl/assay.yaml`
2) Создать выходную директорию
3) Запустить: `bioetl run assay_chembl --config configs/pipelines/chembl/assay.yaml --output <output> [--limit N] [--dry-run] [--profile NAME]`
4) Убедиться в коде возврата 0
5) Проверить артефакты и `meta.yaml`

**Constraints**

- Детерминизм, Pandera-валидация, UnifiedLogger

**Outputs**

- `data/output/assay/`, `meta.yaml`, QC, логи

**References**

- `configs/pipelines/chembl/assay.yaml`

