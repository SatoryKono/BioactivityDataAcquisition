# ADR-040: Diagram Governance and Layout Policy

## Status

Accepted

## Date

2026-02-25

## Context

BioETL contains two diagram directories:

- `docs/02-architecture/mmd-diagrams/` — 95 canonical `.mmd` files
  (architecture: 18 + 11 decomposed, class-diagrams: 16, foundation: 50)
- `docs/02-architecture/diagrams/mermaid/` — 156 decomposed `.mermaid` views
  (31 parent × 5 views + legend)

Foundation diagrams were decomposed by Views (overview/domain/infra/dataflow/full).
Architecture diagrams were partially decomposed — 4 overloaded files (>20 nodes)
yielded 11 sub-files using subdomain-based decomposition.

Existing infrastructure:

- Theme: `theme/mermaid-config.json` + `theme/custom.css`
- Render: `render.sh` (SVG + PNG)
- Lint: `scripts/lint_diagrams.py` (supports `.mmd` + `.mermaid`)
- Pre-commit hook: `lint-diagrams`

### Problem

Two independent colour palettes emerged: the approved scheme in `custom.css`
(purple/green/red/orange/blue) and an ad-hoc scheme in decomposed views
(amber/emerald/blue/violet/slate). All 5 architectural layers had conflicting
colours between the two directories.

Additionally, all 155 decomposed view files used uniform linkStyle (same stroke
for every connection), making diagrams visually flat with no distinction between
data flow, orchestration, DI, observability, and error connections.

## Decision

### D1: Canonical Colour Scheme

A single palette is fixed in `theme/custom.css` (lines 140–151).
All inline `style` directives in `.mermaid` and `.mmd` files **MUST** use this palette.

| Layer          | Fill      | Stroke    |
|----------------|-----------|-----------|
| Domain         | `#f3e5f5` | `#6a1b9a` |
| Application    | `#e8f5e9` | `#2e7d32` |
| Infrastructure | `#ffcdd2` | `#c62828` |
| Composition    | `#fff3e0` | `#e65100` |
| Interfaces     | `#e3f2fd` | `#1565c0` |
| External       | `#eceff1` | `#455a64` |

### D2: Dual Repository Structure

- `.mmd` in `mmd-diagrams/` — canonical location for non-decomposed and
  newly decomposed architecture diagrams
- `.mermaid` in `diagrams/mermaid/` — decomposed views (foundation)
- New architecture sub-views are created as `.mmd` in `mmd-diagrams/architecture/`

### D3: View-based Decomposition Rules

- Hard limit: 20 nodes per view-file (Mermaid Dagre rendering constraint)
- Soft limit: 15 nodes (recommended)
- Files >35 nodes = CRITICAL — decomposition is mandatory
- `foundation/` diagrams: decomposed by 4 standard views
  (overview/domain/infra/dataflow)
- `architecture/` diagrams: decomposed by subdomain (semantic grouping)
- Originals are preserved as full reference files

### D4: Metadata Formats

- `.mmd` files: `@version`, `@date`, `@type`, `@level`, `@nodes`
  (plus optional `@view`, `@parent`, `@adr`)
- `.mermaid` views: `%% View: <type> | Parent: <file>`

### D5: Differentiated Link Styles

Connections are visually classified by semantic type:

| Type            | Style                                            |
|-----------------|--------------------------------------------------|
| Data flow       | `stroke:#1E293B,stroke-width:3px`                |
| Orchestration   | `stroke:#2e7d32,stroke-width:2px`                |
| DI / implements | `stroke:#6a1b9a,stroke-width:1.5px,stroke-dasharray:5` |
| Observability   | `stroke:#94A3B8,stroke-width:1px`                |
| Error           | `stroke:#c62828,stroke-width:2px,stroke-dasharray:4`  |

Each file includes a `%% linkStyle:` comment mapping indices to types.

### D6: CI Validation

`scripts/lint_diagrams.py` scans both directories with these rules:

| Rule       | Severity | Description                       |
|------------|----------|-----------------------------------|
| META-001   | WARNING  | Missing metadata                  |
| NAME-001   | ERROR    | Naming convention violation       |
| CONTENT-001| ERROR    | Placeholder markers               |
| CONTENT-002| ERROR    | Too few non-comment lines         |
| STALE-001  | ERROR    | Diagram >180 days old             |
| STALE-002  | WARNING  | Diagram >90 days old              |
| SIZE-001   | ERROR    | >35 nodes (critical overload)     |
| SIZE-002   | WARNING  | >20 nodes (soft limit)            |
| COLOUR-001 | WARNING  | Unapproved fill colour            |

Pre-commit hook `lint-diagrams` triggers on `.mmd` and `.mermaid` file changes.

### D7: Tool Selection Criteria

| Complexity     | Tool    |
|----------------|---------|
| ≤20 nodes      | Mermaid |
| 20–40, complex | PlantUML|
| >40 nodes      | D2 (ELK)|

## Consequences

### Positive

- Single colour palette eliminates visual conflicts between directories
- Differentiated linkStyles provide immediate visual distinction of connection types
- CI prevents colour and size degradation
- Two directories allow independent evolution of canonical and view files
- Decomposed architecture diagrams are within the 20-node readability target

### Negative

- Two directories + two extensions create cognitive overhead for new contributors
- Synchronization needed: `foundation/*.mmd` ↔ `diagrams/mermaid/*-full.mermaid`
- linkStyle indices are brittle — editing connections requires index recalculation

### Risks

- Node count heuristic in lint is approximate (±20%)
- Layout hacks (invisible edges) may be needed for complex diagrams

## Related ADRs

- ADR-005 (Layered Architecture)
- ADR-020 (Composition Layer)
