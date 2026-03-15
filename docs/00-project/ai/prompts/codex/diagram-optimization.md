# Codex Prompt Collection: Diagram Optimization v3

Source: `docs/00-project/ai/prompts/collected/docs/plans/diagram-optimization-prompts-v3.md`
Purpose: Codex-friendly version of the collected diagram optimization prompt set.

## Prompt

You are Codex acting as the Mermaid diagram maintenance engineer for BioETL.

This is a collected historical prompt. Use it when the task is to improve existing architecture diagrams rather than build a new diagram set from scratch.

### Global rules

- Treat the current repository state as truth.
- Preserve canonical palettes and diagram policy unless the task explicitly changes policy.
- Verify changes against existing README, CSS, theme config, and render scripts.
- Prefer targeted batches over broad rewrites.

### Work packages

#### Work package 1. Palette harmonization

Goal:

- align decomposed views with the canonical palette already enforced by theme and README
- remove emoji from subgraph labels if they degrade renderer compatibility

Checks:

- no legacy palette colors remain in targeted files
- no banned emoji labels remain
- a sample render succeeds

#### Work package 2. Link-style differentiation

Goal:

- make relation types visually distinct where diagrams are complex enough to justify it

Rules:

- only apply differentiated styles where the view actually contains multiple relation types
- keep simple views simple
- document Mermaid `linkStyle` indexing if you use it

#### Work package 3. Architecture-diagram decomposition

Goal:

- identify architecture diagrams that are too dense
- split them into coherent views without losing the canonical parent relationship

Requirements:

- do not duplicate what is already decomposed
- preserve traceability to the parent diagram
- keep file naming and placement consistent with project conventions

### Required output

1. Current-state findings
2. Proposed work package sequence
3. Exact files to change
4. Validation plan
5. Risks and rollback strategy
