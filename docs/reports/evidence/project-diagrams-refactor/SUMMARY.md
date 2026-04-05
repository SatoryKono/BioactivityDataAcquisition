# Сводка evidence по диаграммам проекта и их рефакторингу

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Дата: 2026-03-21

## Интерпретация верхнего уровня

- Формальная cross-shard интерпретация теперь находится в [03-synthesis/CROSS-SYNTHESIS.md](./03-synthesis/CROSS-SYNTHESIS.md).
- Принятая позиция теперь находится в [04-decisions/DECISIONS.yaml](./04-decisions/DECISIONS.yaml).
- Активные риски теперь находятся в [05-risks/RISKS.yaml](./05-risks/RISKS.yaml).

## Общий результат

- Режим сбора evidence: hierarchical
- Завершённые pillars: `diagram-state`, `diagram-refactor-needs`
- Всего семантических объектов evidence: `11`
- Итоговый результат gate: `PASS`

## Выходы shard-ов

- Diagram state shard: [diagram-state/SUMMARY.md](./diagram-state/SUMMARY.md)
- Diagram refactor-needs shard: [diagram-refactor-needs/SUMMARY.md](./diagram-refactor-needs/SUMMARY.md)
- Orchestration log: [ORCHESTRATION.md](./ORCHESTRATION.md)

## Что подтверждает текущее evidence

- The diagram estate is a governed publishing system, not a loose collection of Mermaid files.
- Canonical sources are concentrated in `.mmd` files under `docs/02-architecture/diagrams/`, while views, indexes, bundles, descriptions, PNG, and SVG outputs form a substantial derived-artifact surface.
- The strongest refactor pressure is on derived publication layers: mirrored PNG/SVG render trees, large bundle/index surfaces, and stale diagram descriptions already corroborated by architecture-doc-drift evidence.
- Core and foundation diagram zones appear intentionally governed and should not be treated as casual cleanup targets.
- The main risk is refactoring diagram artifacts without preserving the boundary between canonical diagram sources and derived publication outputs.
- This summary was revalidated against the current repository state after the 2026-03-20 documentation remediation wave.

## Интерпретация

- This evidence pack does not support a blanket redraw or flattening of the entire diagram estate.
- It does support targeted refactoring of derived artifact layers, especially where duplicated render trees and maintenance-heavy bundles create drift pressure.
- Diagram refactoring should start from publication surfaces and stale descriptions, not from canonical Mermaid source families.

## Уровень уверенности

- Higher confidence on state findings because they are corroborated by the diagram README, ADR/governance references, diagram tooling, and architecture tests.
- Higher confidence on refactor-needs findings around duplicated render artifacts and bundle/index maintenance pressure.
- Moderate confidence only on which exact bundle or index layer should be refactored first; that sequencing belongs in a follow-up planning step.
