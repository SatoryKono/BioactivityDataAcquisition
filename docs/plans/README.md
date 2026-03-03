# Plans Directory

*Status: Working planning artifacts (non-normative)*
*Last updated: 2026-03-03*

This directory contains implementation plans, corrective roadmaps, and migration plans.

## Scope

- Planning and decomposition documents for upcoming work.
- Temporary execution plans that can be superseded by newer revisions.
- Non-authoritative operational guidance.

## Source Of Truth

- Project requirements and mandatory rules are defined in:
  - `docs/00-project/RULES.md`
  - `docs/01-requirements/REQUIREMENTS.md`
  - Accepted ADRs in `docs/02-architecture/decisions/`

Plans in this folder must not override normative documents.

## Maintenance Rules

- Keep file names explicit and date-stamped when possible.
- Prefer updating an existing active plan over creating near-duplicates.
- Move obsolete or historical planning artifacts to `docs/99-archive/` when no longer active.

## Active Plan Links

- [DIAGRAMS_DOCS_SCRIPTS_REFACTOR_PLAN.md](DIAGRAMS_DOCS_SCRIPTS_REFACTOR_PLAN.md)
- [diagram-views-improvement-plan.md](diagram-views-improvement-plan.md)
- [mkdocs-material-migration-track-2026-03-03.md](mkdocs-material-migration-track-2026-03-03.md)
- [wave-8-policy-decisions-2026-03-03.md](wave-8-policy-decisions-2026-03-03.md)

## Related Prompt

- [qa_orchestrator.md](../00-project/agents/qa_orchestrator.md)
