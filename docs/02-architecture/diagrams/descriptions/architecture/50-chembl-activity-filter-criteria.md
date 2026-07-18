______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-18'

______________________________________________________________________

# ChEMBL Activity Query And Filtering Criteria

- Исходная диаграмма: `architecture/50-chembl-activity-filter-criteria.mmd`
- SVG: `architecture/svg/50-chembl-activity-filter-criteria.svg`
- Паспорт: `generated/pipeline-dataflows/chembl_activity/pipeline-passport.md`

## Описание

Фиксирует полный набор критериев запроса к ChEMBL API, входной фильтр, структурные правила Silver, фильтры Gold и сводку DQ.

Диаграмма генерируется из единого типизированного IR; ручное редактирование источника не предусмотрено.

## Связанные представления

- `49-chembl-activity-dataflow`
- `51a-chembl-activity-silver-fields-1`
- `51b-chembl-activity-silver-fields-2`
- `52a-chembl-activity-gold-fields-1`
- `52b-chembl-activity-gold-fields-2`

## Метаданные

- Тип: `flowchart`
- Уровень: `Pipeline / Rules`
- Дата метаданных: `2026-07-18`
- Источник истины: `pipeline-dataflow-ir.json`
