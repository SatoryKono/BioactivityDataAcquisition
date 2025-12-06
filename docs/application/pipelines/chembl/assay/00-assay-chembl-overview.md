# 00 Assay Chembl Overview

## Pipeline
**ChemblAssayPipeline** строится на ChemblCommonPipeline и отвечает за нормализацию описаний ассеев.

## Компоненты
- **AssayTransformer** — приводит поля ассеев (тип, организм, параметры) к целевому формату.
- **AssaySchema** — описывает обязательность `assay_chembl_id`, типы полей и порядок колонок.

## Особенности
- Извлечение ассеев через общий ChemblClient с дескрипторами из ChemblDescriptorFactory.
- Нормализация ключевых идентификаторов и ссылок на таргеты.
- Дополнительные проверки обязательных полей и соответствия типов согласно схеме.

## Связи
Данные ассеев используются Activity-пайплайном для контекста экспериментов; общие компоненты (ValidationService, UnifiedOutputWriter) обеспечивают консистентную запись и QC.

## Конфигурация
- `configs/pipelines/chembl/assay.yaml` (профиль `chembl_default`).
- Smoke: `--profile dev --limit 100 --dry-run`; прод — полный запуск без `--dry-run`.

## Диаграммы
- Flowchart: `docs/application/pipelines/chembl/assay/diagrams/flow/assay-workflow.mmd`
- Sequence: `docs/application/pipelines/chembl/assay/diagrams/sequence/assay-main-sequence.mmd`
- Class: `docs/application/pipelines/chembl/assay/diagrams/class/assay-pipeline-class.mmd`