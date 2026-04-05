______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Reproducible Run Contract

- Исходная диаграмма: `architecture/23-reproducible-run-contract.mmd`

## Описание

Диаграмма описывает текущий reproducible-run contract BioETL: одна воспроизводимая идентичность запуска собирается из source refs, resolved/effective config, DQ compatibility anchors и control-plane manifest. Схема теперь явно разводит runtime descriptors и provenance artifacts, чтобы воспроизводимость не зависела от implicit runtime state.

Ключевые акценты:

- `EffectiveConfigService` публикует `ResolvedConfigSnapshot`, `EffectiveExecutionConfig` и `EffectiveConfigArtifact`.
- `RunManifestService` собирает `RunManifest` c `execution_fingerprint`, `effective_config_hash`, `dq_contract_compatibility_hash` и связью на effective-config artifact.
- `PipelineRunContext` получает launch-time anchors для старта pipeline, а `PipelineContext` остаётся только in-run processing context.
- `CompositeCheckpointState` хранит replay watermark (`manifest_id + last_event_id`) и проходит через `CheckpointCompatibilityService` и `CompositeCheckpointLoadService` при resume.

Эта диаграмма нужна, чтобы проверять сразу три контракта: воспроизводимость запуска, валидность checkpoint resume и корректное разделение runtime contexts против control-plane provenance.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата метаданных: `2026-04-02`
