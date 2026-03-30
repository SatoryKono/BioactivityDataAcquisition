---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Reproducible Run Contract

- Исходная диаграмма: `architecture/23-reproducible-run-contract.mmd`

## Описание
Диаграмма Reproducible Run Contract показывает, как source refs, resolved config, runtime overrides и provenance сворачиваются в replay/comparison identity, и использует нотацию flowchart. Она помогает проверить, что воспроизводимость запуска выражена явными артефактами и hash anchors, а не implicit runtime state. В исходном файле прямо зафиксирован контекст: how source refs, resolved config, runtime overrides, and provenance collapse into a replay/comparison identity. Ключевые подграфы: Configuration inputs, Resolution services, Published reproducibility artifacts, Identity anchors, Replay / comparison consumers. Показательные узлы: ConfigSourceRef[], EffectiveConfigService, EffectiveConfigArtifact, resolved_config_hash, execution_fingerprint, CheckpointCompatibilityService. По ним удобно сверять связку конфигурационного resolution path с manifest identity и replay/diff tooling.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата метаданных: `2026-03-28`
