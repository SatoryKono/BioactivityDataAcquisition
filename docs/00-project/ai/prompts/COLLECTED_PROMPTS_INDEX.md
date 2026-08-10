______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# Collected Prompts Index

*Статус: internal-published (Internal / Extended)*

This page is a curated discoverability index for unique prompt artifacts kept in
`docs/00-project/ai/prompts/collected/`.

These files are **not** the canonical source of project governance or runtime
workflow policy. Prefer:

- [RULES.md](../../RULES.md)
- current agent guides under `docs/00-project/ai/agents/`
- runtime orchestration docs and active skill surfaces

The collected prompt folder remains a **repo-only / historical helper surface**:
use it to find archive-only prompt snapshots that do not have an actively
maintained root-level twin, not to override current guidance.

## Current Inventory

- Target folder: `docs/00-project/ai/prompts/collected/`
- Collected files: **2**
- Surface role: archive-only prompt snapshots retained for historical
  discoverability

## Grouped Prompt Families

### Diagram Expansion Archive

- `docs/00-project/ai/prompts/collected/docs/02-architecture/mmd-diagrams/docs/PROMPT-diagram-expansion.md`

Historical archive prompt for earlier architecture diagram expansion waves.
Treat as reference-only and validate against current Mermaid skills and docs.

### Diagram Optimization Archive

- `docs/00-project/ai/prompts/collected/docs/plans/diagram-optimization-prompts-v3.md`

Historical optimization-wave prompt captured from an earlier diagrams plan.
Contains time-bound repository state and should not be treated as active policy.

## Usage Rules

1. Do not treat collected prompts as source-of-truth policy.
1. If a collected prompt conflicts with active docs, active docs win.
1. Prefer using this page as the single published entrypoint for the collected
   prompt surface instead of promoting raw archive snapshots into MkDocs nav.
1. If a collected prompt gets a maintained root-level counterpart, prefer the
   root-level file and remove the duplicate collected copy.

## Related Entry Points

- `docs/00-project/ai/prompts/README.md` — Prompt Library entrypoint
- `docs/00-project/ai/prompts/REGISTRY.yaml` — machine-readable active catalog
- `docs/00-project/ai/prompts/library/` — active operator-paste cards
- `docs/00-project/ai/prompts/archive/` — mirrors + campaign megaprompts
- `docs/00-project/ai/prompts/library/docs/ai-audit-planning.md` —
  `prompt.docs.ai-audit-planning`
- `docs/00-project/ai/prompts/library/architecture/review-assessment.md` —
  `prompt.architecture.review`
- `docs/00-project/ai/prompts/library/tests/speed-optimization-loop.md` —
  `prompt.tests.speed-optimization`
- [Skills Practical Index](../skills/SKILLS-PRACTICAL-INDEX.md)
- [Agent Orchestration Rules](../agents/policy/agent-orchestration-rules.md)
- Epic: #8513
