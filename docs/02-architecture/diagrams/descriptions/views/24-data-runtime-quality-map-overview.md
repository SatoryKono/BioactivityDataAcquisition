______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Data Runtime Quality Map Overview

- Исходная диаграмма: `views/24-data-runtime-quality-map-overview.mermaid`

## Описание

Эта views-диаграмма Data Runtime Quality Map Overview представляет срез типа overview для quality-runtime-views и использует нотацию flowchart. Она нужна как компактная карта shared runtime anchors, на которых одновременно держатся traceability, idempotency, observability и reproducibility. В метке view зафиксировано назначение: Overview. Показательные узлы в диаграмме: run_id, manifest_id, effective_config_hash, execution_fingerprint, dataset_ref. Через этот view удобно быстро проверять, что разные quality/runtime narratives проекта сходятся к одному набору контрольных идентификаторов, а не описывают разрозненные anchor-модели.

## Метаданные

- Тип: `flowchart`
- View: `Overview`
- Parent: `quality-runtime-views`
