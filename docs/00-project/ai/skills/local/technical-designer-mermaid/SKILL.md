> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/technical-designer-mermaid/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "technical-designer-mermaid"
description: "Design technical diagrams in Mermaid syntax for architecture, data flows, API interactions, domain models, and process behavior. Supports generic Mermaid tasks and BioETL project mode with ADR-040 compliance, lint/render workflow, and repository file conventions. Use when users ask for Mermaid diagrams, mention common typos like \"merimad/merimd\", convert text/design docs into diagrams, or improve existing Mermaid blocks."
---

# Technical Designer Mermaid

## Source Of Truth
- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`

## Overview

Create, refactor, and review Mermaid diagrams with a technical-design mindset.
Prioritize structural correctness, semantic clarity, and maintainability over decoration.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

This skill has two operation modes:

- Generic Mermaid mode: use for standalone diagrams or unknown repositories.
- BioETL project mode: use when working inside this repository (`BioactivityDataAcquisition`).

## Mode Selection

Use BioETL project mode when any of the following is true:

- The task references files under `docs/02-architecture/`.
- The user asks to update, render, lint, or fix diagrams in this repo.
- The user asks for architecture diagrams tied to BioETL layers/ports/adapters.

Otherwise use generic Mermaid mode.

## Generic Mermaid Workflow

1. Confirm intent.

- Identify boundary, audience, and purpose.
- Identify required fidelity (high-level, implementation-level, debug view).

2. Select minimal effective type.

- `flowchart` for component/process flow.
- `sequenceDiagram` for interactions.
- `classDiagram` for models and responsibilities.
- `stateDiagram-v2` for lifecycle behavior.
- `erDiagram` for relational modeling.
- `gantt` only when user explicitly asks for timeline planning.

3. Draft with stable naming.

- Use stable IDs (`service_api`, `db_core`) and clear labels.
- Use action-oriented edge labels (`validates`, `writes`, `publishes`).
- Keep orientation explicit (`TB` or `LR`).

4. Quality pass.

- Remove redundant edges and mixed abstraction levels.
- Ensure syntax validity and terminology consistency.

## BioETL Project Mode Workflow

1. Choose target file family first.

- Canonical source diagrams: `docs/02-architecture/mmd-diagrams/**.mmd`.
- Decomposed views: `docs/02-architecture/mmd-diagrams/views/*.mermaid`.
- Do not create new diagram files under `docs/99-archive/**`.

2. Enforce file purpose and placement.

- New architecture-level canonical work goes to `mmd-diagrams/architecture/`.
- Class families go to `mmd-diagrams/class-diagrams/`.
- Foundation canonical updates go to `mmd-diagrams/foundation/`.
- View decomposition outputs go to `mmd-diagrams/views/` as `-full/-overview/-domain/-infra/-dataflow`.

3. Enforce metadata contract.

- For `.mmd`, include:
  - `%% @version`
  - `%% @date` in `YYYY-MM-DD`
  - `%% @type`
  - `%% @level`
  - `%% @nodes`
  - optional `%% @adr` when relevant
- For `.mermaid` view files, include:
  - `%% View: <...> | Parent: <...>`

4. Enforce ADR-040 style rules.

- Use only canonical palette (no ad-hoc hex colors).
- No emoji prefixes in subgraph labels.
- Keep naming and layer semantics consistent with BioETL architecture docs.

5. Enforce density and layout rules.

- Node density targets:
  - \<=15 ideal
  - 16-20 soft limit
  - 21-35 decompose recommended
  - > 35 decompose required
- For `flowchart/graph`, add ELK init when `@nodes > 20` (required when >40 by lint policy).

6. Handle link semantics and readability.

- Prefer semantic `linkStyle` differentiation for larger flowcharts.
- Preserve or improve label readability and avoid unnecessary crossing.

7. Run project quality gate after edits.

- `python scripts/diagrams/lint_diagrams.py docs`
- `bash scripts/diagrams/validate_mermaid_syntax.sh`
- `bash docs/02-architecture/mmd-diagrams/render.sh` (or targeted render command)
- Optional smoke check:
  - `python scripts/diagrams/check_diagram_visual_smoke.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt`

8. Respect repository delivery rules.

- If source `.mmd/.mermaid` changed, ensure rendered `svg/png` outputs are updated in commit.
- Resolve or explicitly justify orphan nodes (`GRAPH-001`) using `%% keep-orphan: ...` only when intentional.

## Output Rules

- Prefer concise diagrams over verbose node text.
- Keep one language per diagram (all English or all Russian labels).
- If input Mermaid is broken, fix syntax first, then structure.
- If request is ambiguous, state assumptions immediately above the diagram.
- If task is repository modification, edit files and run checks instead of only returning snippets.

## Review Checklist

- Diagram type matches intent.
- Boundaries and ownership are visible.
- Critical paths are labeled.
- Abstraction level is consistent.
- Mermaid syntax is valid.
- In BioETL mode:
  - Metadata contract is present.
  - Palette and emoji constraints are respected.
  - `@nodes` and ELK policy are respected.
  - `lint/syntax/render` checks have been considered.

## Pattern Library

Use [patterns.md](references/patterns.md) as a source for ready-to-adapt templates.
Read only the relevant section for the selected diagram type.

## Prompt Handling

- Treat `merimad`, `mermiad`, `mermid`, and similar misspellings as `Mermaid`.
- Treat `merimd` as `Mermaid`.
- If the user asks in Russian, keep explanations in Russian and code in valid Mermaid syntax.
- If rendering target is unknown, prefer broadly compatible Mermaid constructs.
