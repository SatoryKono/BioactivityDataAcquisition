# 00 Molecule Chembl Overview

## Pipeline
- Использует универсальный `ChemblEntityPipeline` (`src/bioetl/application/pipelines/chembl/pipeline.py`) c базой `ChemblPipelineBase`.
- Схема и контракт: `domain/schemas/chembl/molecule.py` + `domain/schemas/pipeline_contracts.py` (entity `molecule`).

## Компоненты
- `ChemblExtractorImpl` — `input_mode=id_only` по умолчанию, использует `IdListRecordSourceImpl` (список ChEMBL ID из CSV) или API/CSV при смене режима.
- `ChemblTransformerImpl` — приводит к схеме `molecule`, нормализует вложенные объекты (structures, properties, hierarchy) и убирает null в обязательных столбцах.
- Post-transform: `HashColumnsTransformer`, `IndexColumnTransformer`, `DatabaseVersionTransformer`, `FulldateTransformer`.
- `ValidationService` + Pandera-схема `chembl.molecule`.
- `UnifiedOutputWriter` — стабильная сортировка, атомарная запись `<output>/molecule.csv`, `meta.yaml`, QC-отчёты.

## Особенности
- `primary_key`: `PipelineConfig.primary_key` или `pipeline.primary_key`, по умолчанию `molecule_chembl_id`.
- `input_mode`: `id_only` с путём по умолчанию `data/input/testitem.csv`; поддерживает `api` и `csv` режимы без изменения кода.
- Хеши рассчитываются на нормализованных данных; ключи — `hashing.business_key_fields`.
- Метрики стадий публикуются хуком `MetricsPipelineHookImpl`.

## Конфигурация
- `configs/pipelines/chembl/molecule.yaml` (использует профиль `chembl_default`).
- Рекомендация: smoke → `--profile dev --limit 50 --dry-run`; прод — полный запуск без `--dry-run`.

## Диаграммы
- Flow: `docs/application/pipelines/chembl/molecule/diagrams/flow/molecule-workflow.mmd`
- Sequence: `docs/application/pipelines/chembl/molecule/diagrams/sequence/molecule-main-sequence.mmd`
- Class: `docs/application/pipelines/chembl/molecule/diagrams/class/molecule-pipeline-class.mmd`

