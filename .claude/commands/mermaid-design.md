______________________________________________________________________

## description: "Создание, проверка и рендеринг Mermaid-диаграмм для BioETL с ADR-040 compliance."

# /mermaid-design

## Использование

```
/mermaid-design [action] [target]
```

**Действия:** `create` (default), `lint`, `render`, `fix`, `review`
**Target:** path to `.mmd`/`.mermaid`, diagram type, or component name.

## Инструкции

### create

1. Choose type: `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`
1. Place file: `docs/02-architecture/mmd-diagrams/{name}.mmd` or `docs/02-architecture/diagrams/mermaid/{category}/{name}.mermaid`
1. Add metadata header:

```mermaid
%% @version 1.0.0
%% @date YYYY-MM-DD
%% @type flowchart
%% @level high|implementation|debug
%% @nodes N
```

4. Density limits: ≤15 ideal, 16-20 soft, 21-35 decompose, >35 mandatory decompose
1. > 20 nodes: add `%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%`
1. Use canonical ADR-040 palette only (no ad-hoc hex)
1. Apply Layout Best Practices (LBP-001..010)

### lint

```bash
python -m scripts.diagrams lint docs
bash scripts/diagrams/validate_mermaid_syntax.sh
```

### render

```bash
bash docs/02-architecture/mmd-diagrams/render.sh
```

### fix

Read file → check metadata, palette, density, syntax → fix issues → re-lint.

### review

Check: type matches intent, boundaries visible, critical paths labeled, single abstraction level.
BioETL mode: metadata, palette, no emoji in subgraph labels, @nodes/ELK policy.

## Layout Best Practices (LBP)

| Rule    | Summary                                                                   |
| ------- | ------------------------------------------------------------------------- |
| LBP-001 | Cluster by interaction radius (>3 links → same subgraph)                  |
| LBP-002 | Invisible links (`A ~~~ B`) only with documented reason                   |
| LBP-003 | Edge routing: ≤10 auto, 11-30 POLYLINE, >30 ORTHOGONAL                    |
| LBP-004 | Entry ports top/left, exit ports bottom/right                             |
| LBP-005 | Semantic stroke width: 3px data, 2px control, 1.5px DI, 1px observability |
| LBP-006 | Edge labels ≤15 chars                                                     |
| LBP-007 | Hub nodes (≥6 links): use Virtual Nodes                                   |
| LBP-008 | Max subgraph depth: 2 levels                                              |
| LBP-009 | `classDef` with `min-width` for each node type                            |
| LBP-010 | Edges/Nodes ratio >3.5 → mandatory decomposition                          |
