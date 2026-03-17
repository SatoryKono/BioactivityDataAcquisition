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

- [mkdocs-material-migration-track-2026-03-03.md](mkdocs-material-migration-track-2026-03-03.md)
- Historical plans moved to [docs/99-archive/plans/README.md](../99-archive/plans/README.md) *(archived reference only)*

## Related Prompt

- [py-qa-orchestrator.md](../00-project/ai/agents/runtime/py-qa-orchestrator.md)
