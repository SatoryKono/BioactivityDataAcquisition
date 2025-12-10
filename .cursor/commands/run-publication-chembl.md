# /run-publication-chembl

**Goal:** Запуск пайплайна публикаций ChEMBL.

**Inputs**

- `--output PATH` (required)
- `--config PATH` (optional): `configs/pipelines/chembl/publication.yaml`
- `--dry-run` (optional)
- `--profile NAME` (optional)
- `--limit N` (optional)

**Steps**

1) Проверить `configs/pipelines/chembl/publication.yaml`
2) Создать выходную директорию
3) Запустить: `bioetl run publication_chembl --config configs/pipelines/chembl/publication.yaml --output <output> [--limit N] [--dry-run] [--profile NAME]`
4) Убедиться в коде возврата 0
5) Проверить артефакты и `meta.yaml`

**Constraints**

- Детерминизм, Pandera-валидация, UnifiedLogger

**Outputs**

- `data/output/document/`, `meta.yaml`, QC, логи

**References**

- `configs/pipelines/chembl/publication.yaml`
