# Diagram Rendering Improvement Plan (Actual State)

Updated: 2026-02-26
Owner: Docs/Architecture tooling
Scope: Mermaid diagram workflow in `docs/**`

## Goal

Bring diagram rendering and visual quality workflow to a single, enforceable, CI-stable pipeline aligned with ADR-040.

## Current State Snapshot

### Already implemented (in working tree)

- `docs.yml` now validates Mermaid via `scripts/validate_mermaid_syntax.sh` instead of inline loop.
- `docs.yml` drift check already includes both `docs/**/*.mmd` and `docs/**/*.mermaid` (excluding `docs/99-archive/**`).
- `render.sh` now scans `docs/**` (not only `mmd-diagrams/*`) and supports exclusion paths.
- `render.sh` already applies SVG post-processing via `scripts/inject_svg_styles.py`.
- `lint_diagrams.py` already scans full `docs/` and excludes `docs/99-archive/**`.

### Gaps vs ADR-040 / docs policy

- Large amount of manual `&nbsp;` padding remains in source diagrams.
- No image-based visual regression gate in CI.

## Execution Plan

## Phase 0: Policy-Grade Gates (High priority)

- [x] Add missing lint rules in `scripts/lint_diagrams.py`:
  - `COLOUR-001`: non-canonical palette usage in `style`/`classDef`.
  - `COLOUR-002`: emoji in subgraph labels.
  - `SIZE-001`: `@nodes > 35` -> `ERROR`.
  - `SIZE-002`: `@nodes > 20` -> `WARNING`.
- [x] Confirm thresholds/exemptions policy for `*-full.mermaid` reference views and align with ADR text.
- [x] Add/adjust tests for new lint behavior (target: `tests/` policy/architecture area).
- [x] Execute new tests in project runtime (`pytest`) and record result in this plan.

Acceptance:
- `lint_diagrams.py` output matches ADR-040 rule set.
- CI fails on canonical-policy violations, not only syntax errors.

## Phase 1: Single Render Pipeline (High priority)

- [x] Mark legacy pipeline deprecated:
  - `scripts/render_diagrams.py` (deprecation notice; keep temporary compatibility).
  - `.github/workflows/project-automation.yml` diagram render step disabled.
- [x] Keep canonical pipeline:
  - `docs/02-architecture/mmd-diagrams/render.sh`
  - `.github/workflows/docs.yml`

Acceptance:
- One authoritative render path documented and used in CI.

## Phase 2: Runtime Stability (Medium priority)

- [x] Add explicit preflight guidance for `mmdc` browser runtime:
  - required Chrome/Chromium setup for Puppeteer.
  - fallback/diagnostics in `scripts/validate_mermaid_syntax.sh`.
- [x] Update runbook text in `docs/02-architecture/mmd-diagrams/README.md`.

Acceptance:
- Local validation failures clearly distinguish content errors from missing browser runtime.

## Phase 3: Visual Quality Cleanup (Medium priority)

- [x] Add baseline hotspot report for manual padding density:
  - `scripts/report_diagram_padding.py`
  - `make report-diagram-padding`
- [x] Run pilot normalization on one hotspot (`foundation/30-port-adapter-mapping.mmd`) to confirm tooling flow.
- [x] Implement grouped-width normalization strategy in `uniform_diagram_sizes.py`:
  - new directive: `%% @uniform-width group`
  - metadata now records `width_strategy` and per-group `width`
  - idempotency covered by `tests/architecture/test_uniform_diagram_group_width.py`
- [x] Apply grouped-width mode to top class-diagram hotspots:
  - `class-diagrams/04-types-enums.mmd`
  - `class-diagrams/06-config-classes.mmd`
  - `class-diagrams/07-application-core-services.mmd`
  - `class-diagrams/08-application-services.mmd`
  - `class-diagrams/09-transformers.mmd`
  - `class-diagrams/10-adapters.mmd`
- [x] Apply grouped-width mode to highest flowchart hotspot pair:
  - `foundation/30-port-adapter-mapping.mmd`
  - `diagrams/mermaid/30-port-adapter-mapping-full.mermaid`
- [ ] Continue reducing manual `&nbsp;` in remaining hotspots:
  - `foundation/04-domain-layer-class-diagram.mmd`
  - `foundation/13-domain-models-relationship.mmd`
- [ ] Expand ELK/layout + differentiated `linkStyle` usage for overloaded flowcharts.

Progress metric (2026-02-26):
- Total `&nbsp;` across scanned Mermaid sources reduced from **56,971** to **49,978** (`-6,993`, ~`-12.3%`).

Acceptance:
- Fewer padding artifacts in source files.
- Better edge routing/readability in dense diagrams.

## Phase 4: Visual Regression Guard (Lower priority)

- [ ] Add smoke visual regression in CI for selected reference diagrams:
  - render deterministic SVG set.
  - compare against checked-in baseline (or artifact diff report).

Acceptance:
- Style/layout regressions are visible in PR checks.

## Implementation Order (next actions)

1. Apply `@uniform-width group` selectively to remaining grouped hotspots outside current class families (where safe).
2. Expand ELK/layout + differentiated `linkStyle` on overloaded flowcharts.
3. Add CI smoke visual regression set (Phase 4).

## Notes

- Working tree currently contains substantial unrelated changes; implementation should be scoped strictly to files listed per phase.
- Do not auto-reformat unrelated docs/diagram files during this workstream.
