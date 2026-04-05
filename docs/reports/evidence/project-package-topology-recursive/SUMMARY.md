# Сводка evidence: project-package-topology-recursive

Дата: 2026-03-21
Статус: актуализировано

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Статус пакета

- `ORCHESTRATION.md` exists and records the recursive evidence pass over dense nested package trees.
- A top-level cross-shard synthesis exists in [03-synthesis/CROSS-SYNTHESIS.md](./03-synthesis/CROSS-SYNTHESIS.md).
- Top-level decision and risk layers exist in [04-decisions/DECISIONS.yaml](./04-decisions/DECISIONS.yaml) and [05-risks/RISKS.yaml](./05-risks/RISKS.yaml).
- This package is organized as four recursive layer shards:
  - [application](./application/SUMMARY.md)
  - [composition](./composition/SUMMARY.md)
  - [domain](./domain/SUMMARY.md)
  - [infrastructure](./infrastructure/SUMMARY.md)

## Aggregate Findings

- All four recursive layer shards passed their evidence gates.
- `application` shows provider-oriented pipelines plus clearly segmented `core` and `composite` subtrees.
- `composition` shows the broadest recursive pressure in `bootstrap/runtime` and `factories/pipeline`, with narrower seams in `bootstrap/assembly` and `factories/dq`.
- `domain` remains strongly specialized, especially across `ports`, `schemas`, `contracts.gold`, and fault-domain exceptions.
- `infrastructure` is the richest recursive tree, with clear subdivision by provider adapters, medallion storage layers, and dedicated observability/config islands.

## Scope Boundaries

- This recursive package describes topology, not code health, import correctness, or refactor priority by itself.
- The shard summaries are structural evidence layers that can feed later health, ownership, or simplification decisions.

## Ключевые ссылки

- [ORCHESTRATION.md](./ORCHESTRATION.md)
- [03-synthesis/CROSS-SYNTHESIS.md](./03-synthesis/CROSS-SYNTHESIS.md)
- [04-decisions/DECISIONS.yaml](./04-decisions/DECISIONS.yaml)
- [05-risks/RISKS.yaml](./05-risks/RISKS.yaml)
- [application/SUMMARY.md](./application/SUMMARY.md)
- [composition/SUMMARY.md](./composition/SUMMARY.md)
- [domain/SUMMARY.md](./domain/SUMMARY.md)
- [infrastructure/SUMMARY.md](./infrastructure/SUMMARY.md)
