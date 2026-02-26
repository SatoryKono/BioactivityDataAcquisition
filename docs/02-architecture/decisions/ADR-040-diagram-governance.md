# ADR-040: Diagram Governance and Layout Policy

## Status

Accepted

## Date

2026-02-25

## Context

BioETL contains 84 Mermaid diagrams (`.mmd`) in `docs/02-architecture/mmd-diagrams/`.
A subset of diagrams exceeded practical Dagre layout limits and became difficult to read.

Existing infrastructure:

- Theme: `theme/mermaid-config.json` + `theme/custom.css`
- Rendering: `render.sh` (SVG + PNG)
- Linting: `scripts/lint_diagrams.py` (extended for `.mmd`)
- Policy baseline: `06-diagram-policy.md`

## Decision

### D1: View-based decomposition

Diagrams with >20 nodes should be decomposed into views (`01a`, `01b`, ...). Decomposed files must include `%% @view` and `%% @parent` metadata.

### D2: Superseded format

Replaced files keep a standard marker and are not deleted:

```text
%% ⚠️ SUPERSEDED — replaced by <files>
%% @status  superseded
%% @superseded-by <file>
```

Superseded files are skipped by rendering and content lint checks.

### D3: Colour scheme stays fixed

Layer colours remain sourced from `theme/custom.css` and README colour tables.

### D4: External theming preferred

Use `mmdc -c theme/mermaid-config.json --cssFile theme/custom.css`. Avoid new per-file `%%{init:}` blocks.

### D5: CI validation

`lint_diagrams.py` enforces naming, metadata, node-count warnings/errors, colour validation, and view metadata for decomposed files. Pre-commit includes `lint-diagrams` hook.

### D6: Tool selection criteria

- ≤20 nodes: Mermaid
- 20–40 nodes with unresolved layout complexity: PlantUML
- > 40 nodes: D2 (ELK)
- Sequence with >8 participants: PlantUML

### D7: Canonical location

Canonical source directory: `docs/02-architecture/mmd-diagrams/`, canonical extension: `.mmd`.

### D8: Legend file

`00-legend.mmd` is the reference for layer colours and link types.

## Consequences

### Positive

- Better readability through decomposition
- Stable, shared colour governance
- CI guardrails for future changes
- Historical files retained through superseded markers

### Negative

- More files to maintain
- linkStyle indices can be brittle when editing links

### Risks

- Mermaid feature support varies by version
- Node-count linting is heuristic and approximate

## Related ADRs

- ADR-005
- ADR-020
- ADR-025
