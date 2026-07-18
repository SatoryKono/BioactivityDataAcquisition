______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-18'

______________________________________________________________________

# ChEMBL Activity Source To Silver And Gold

- Исходная диаграмма: `architecture/49-chembl-activity-dataflow.mmd`
- SVG: `architecture/svg/49-chembl-activity-dataflow.svg`
- Паспорт: `generated/pipeline-dataflows/chembl_activity/pipeline-passport.md`

## Описание

Показывает сквозной путь записи от API ChEMBL через Bronze, структурную фильтрацию и DQ к фактическим выходам Silver и Gold.

Диаграмма генерируется из единого типизированного IR; ручное редактирование источника не предусмотрено.

## Связанные представления

- `50-chembl-activity-filter-criteria`
- `51a-chembl-activity-silver-fields-1`
- `51b-chembl-activity-silver-fields-2`
- `52a-chembl-activity-gold-fields-1`
- `52b-chembl-activity-gold-fields-2`

## Метаданные

- Тип: `flowchart`
- Уровень: `Pipeline / Dataflow`
- Дата метаданных: `2026-07-18`
- Источник истины: `pipeline-dataflow-ir.json`
