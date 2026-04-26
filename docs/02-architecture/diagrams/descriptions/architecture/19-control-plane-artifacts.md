______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Control-Plane Artifacts and Traceability

- Исходная диаграмма: `architecture/19-control-plane-artifacts.mmd`

## Описание

Диаграмма показывает актуальный control-plane runtime BioETL: composition сначала создаёт immutable provenance artifacts, затем привязывает ledger и lineage collaborators к pipeline runners, а composite resume восстанавливается как `checkpoint snapshot + ledger suffix replay`. Это уже не общая схема “manifest + немного артефактов”, а точная карта publication и inspection path для `RunManifest`, `RunLedger` и checkpoint replay.

Ключевой архитектурный акцент диаграммы — разделение runtime descriptors и control-plane artifacts. `PipelineRunContext` остаётся launch descriptor, `PipelineContext` обслуживает in-run processing, а `domain.control_plane.RunManifest` публикуется отдельно как immutable provenance artifact. Это согласовано с принятым execution-context contract и запрещает возврат к модели “one universal manifest for everything”.

Самые важные узлы и связи:

- `create_run_manifest_with_effective_config` публикует effective-config artifact и immutable run manifest до старта pipeline execution.
- `RunLedgerService` принимает `run_*`, `stage_started`, `stage_completed` и `artifact_published` события от ordinary/composite runners и writers.
- `CompositeCheckpointLoadService` читает checkpoint snapshot, использует `manifest_id + last_event_id`, затем достраивает coarse-grained resume state через `project_run_ledger_replay`.
- inspection surfaces читают manifest, ledger и lineage через соответствующие ports, а не через скрытые side channels.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-04-02`
