# Control-Plane Artifacts and Traceability

- Исходная диаграмма: `architecture/19-control-plane-artifacts.mmd`

## Описание
Диаграмма Control-Plane Artifacts and Traceability показывает, как runtime-сборка BioETL публикует immutable run metadata, ledger events и lineage fragments, и использует нотацию flowchart. Материал нужен для проверки того, что control-plane публикация согласована между composition/runtime builders, application services и file-backed stores без скрытых side channels. В исходном файле прямо зафиксирован контекст: how runtime assembly publishes immutable run metadata, ledger events, and lineage fragments. Ключевые подграфы в схеме: Composition runtime builders, Application services, Domain ports, Infrastructure stores, Published artifacts, Runtime publishers. Показательные узлы: EffectiveConfigService, RunManifestService, RunLedgerService, LineageStorePort, FileRunManifestStore, FileLineageStore. По ним удобно сверять архитектурный контракт публикации артефактов, инспекцию lineage и связку между PipelineRunner, writers и storage adapters.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-28`
