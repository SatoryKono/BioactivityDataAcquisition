# ADR-040: Diagram Governance and Layout Policy

## Status

Accepted

## Date

2026-02-25

## Context

BioETL contains 84 Mermaid diagrams (`.mmd`) in `docs/02-architecture/mmd-diagrams/`.
Several diagrams exceed practical Dagre layout limits and become hard to read when
node density grows above 20 nodes.

Existing infrastructure:

- Theme: `theme/mermaid-config.json` + `theme/custom.css`.
- Rendering: `render.sh` (SVG + PNG, parallel).
- Linting: `scripts/lint_diagrams.py` (extended for `.mmd`).
- Policy: `06-diagram-policy.md` (POL-LLM-DIAGRAMS-001).

## Decision

### D1: View-based decomposition

Diagrams with >20 nodes SHOULD be decomposed into views (`a`, `b`, `c`, `d` suffixes).
Decomposed files MUST include `%% @view` and `%% @parent` metadata.
Hard limit is 20 nodes per file, recommended limit is 15.

### D2: Superseded file format

Replaced source files MUST use a standard superseded header:

```text
%% ⚠️ SUPERSEDED — replaced by <list>
%% @status  superseded
%% @superseded-by <file1.mmd>
```

Superseded files are retained for historical reference and skipped by render/lint
content checks.

### D3: Colour scheme remains fixed

Layer colours are fixed in `theme/custom.css` and README colour tables.
Subgraph styles MUST use approved colours only.

### D4: External theming as default

Styling is applied via:
`mmdc -c theme/mermaid-config.json --cssFile theme/custom.css`.
New files SHOULD avoid embedded `%%{init:}` blocks.

### D5: CI validation via lint rules

`lint_diagrams.py` enforces:

- `SIZE-001/002` node limits,
- `VIEW-001/002` decomposed metadata,
- `COLOUR-001` approved fill colours,
- `HACK-001` layout-hack threshold.

A pre-commit hook (`lint-diagrams`) runs the linter locally.

### D6: Tool-selection thresholds

| Condition                                     | Preferred tool |
| --------------------------------------------- | -------------- |
| ≤20 nodes                                     | Mermaid        |
| 20–40 nodes with unresolved layout complexity | PlantUML       |
| >40 nodes                                     | D2 (ELK)       |
| Sequence >8 participants                      | PlantUML       |

### D7: Canonical location and extension

Canonical diagram location: `docs/02-architecture/mmd-diagrams/`.
Canonical extension: `.mmd`.
Legacy `.mermaid` diagrams remain historical and backward-compatible.

### D8: Legend

A dedicated legend diagram (`00-legend.mmd`) is the reference for layer and link styles.
Files with `@type legend` are excluded from node-size checks.

## Consequences

### Positive

- Better readability via decomposition and metadata governance.
- Single source of truth for styles through theme config + CSS.
- CI/pre-commit reduces visual and policy regressions.
- Historical files remain available via superseded markers.

### Negative

- More files to maintain across decomposed views.
- Link-style index maintenance remains fragile when edges change.

### Risks

- Node counting is heuristic and may have small error margins.
- Mermaid feature support can differ by CLI/runtime version.

## Related ADRs

- ADR-005 (Layered Architecture)
- ADR-020 (Composition Layer)
- ADR-025 (Config Governance)
