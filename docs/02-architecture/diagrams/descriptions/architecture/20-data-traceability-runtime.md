______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Data Traceability Runtime Path

- Исходная диаграмма: `architecture/20-data-traceability-runtime.mmd`

## Описание

Диаграмма Data Traceability Runtime Path показывает, как один pipeline run в BioETL становится inspectable через manifest, ledger, lineage и artifact identity anchors, и использует нотацию flowchart. Она нужна для ревью end-to-end traceability surface: от caller и runtime assembly до stores, inspection services и идентификаторов, по которым потом ищутся артефакты и lineage fragments. В исходном файле прямо зафиксирован контекст: how one pipeline run becomes inspectable through manifest, ledger, lineage, and artifact identity anchors. Ключевые подграфы: Composition runtime assembly, Application control-plane services, Infrastructure stores, Execution + publication, Traceability anchors. Показательные узлы: build_pipeline_runner, EffectiveConfigService, RunManifestService, RunLedgerService, LineageInspectionService, dataset_ref. Диаграмма особенно полезна при проверке репликации control-plane данных, диагностике runtime lineage и валидации ADR-044 traceability anchors.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Runtime`
- Дата метаданных: `2026-03-28`
- ADR: `ADR-044`
