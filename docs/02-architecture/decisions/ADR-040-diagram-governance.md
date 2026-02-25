# ADR-040: Diagram Governance and Layout Policy

## Status

Accepted

## Date

2026-02-25

## Context

BioETL contains Mermaid diagrams (`.mmd`) under `docs/02-architecture/mmd-diagrams/`.
Several diagrams exceeded practical Dagre readability limits and needed decomposition.

Existing diagram infrastructure:

- Theme: `theme/mermaid-config.json` + `theme/custom.css`
- Rendering: `mmd-diagrams/render.sh`
- Linting: `scripts/lint_diagrams.py`
- Policy baseline: `06-diagram-policy.md`

## Decision

### D1: View-based decomposition

Diagrams with more than 20 nodes are decomposed into letter-suffixed views (`01a-`, `13b-`, etc.).
Decomposed files must include `%% @view` and `%% @parent` metadata.

### D2: Superseded format

Replaced files are kept with a superseded marker block:

```text
%% ⚠️ SUPERSEDED — replaced by <list>
%% @status  superseded
%% @superseded-by <file.mmd>
```

Superseded diagrams are excluded from rendering and content lint checks.

### D3: Colour scheme is fixed

Approved layer colours are defined in `theme/custom.css` and must not be changed ad hoc in diagram files.

### D4: External theme config

Theming must be applied via `mmdc -c theme/mermaid-config.json --cssFile theme/custom.css`.
`%%{init:}` is allowed for historical files but not required for new files.

### D5: CI validation

`lint_diagrams.py` validates both `.mmd` and legacy `.mermaid` files and enforces view metadata, node-size heuristics, approved fill colours, and layout-hack limits.
A `lint-diagrams` pre-commit hook runs this check automatically.

### D6: Tool selection criteria

- `<=20` nodes: Mermaid
- `20–40` nodes with unresolved layout complexity: PlantUML
- `>40` nodes: D2 (ELK layout)
- Sequence diagrams with more than 8 participants: PlantUML

### D7: Canonical location

Canonical source location: `docs/02-architecture/mmd-diagrams/`.
Canonical extension: `.mmd`.
Legacy `.mermaid` files remain historical and supported by linter.

### D8: Legend

`00-legend.mmd` is the reference legend for layer colours and link semantics.

## Consequences

### Positive

- Better readability via decomposition.
- Stable, single-source theming.
- CI checks prevent future diagram quality regressions.
- Superseded files remain available for historical traceability.

### Negative

- More files to maintain.
- View synchronization required when architecture evolves.

### Risks

- `linkStyle` indices are fragile.
- Node counting is heuristic.
- Some Mermaid features are version-sensitive.

## Related ADRs

- ADR-005
- ADR-020
- ADR-025
