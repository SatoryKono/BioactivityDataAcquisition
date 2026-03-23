# Plans Directory

*Status: Working planning artifacts (non-normative)*
*Last updated: 2026-03-23*

This directory contains implementation plans, corrective roadmaps, migration
plans, and supporting architecture assessment snapshots.

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

## Publication Hygiene Note

- This folder is intentionally **internal-published**, not canonical.
- Plans may be linked from the docs site for discoverability, but they remain
  working materials rather than normative guidance.
- When a plan conflicts with active docs under `docs/00-05`, active docs win.
- Historical or completed plans should move to `docs/99-archive/` rather than
  accumulate as competing active surfaces.

## Maintenance Rules

- Keep file names explicit and date-stamped when possible.
- Prefer updating an existing active plan over creating near-duplicates.
- Move obsolete or historical planning artifacts to `docs/99-archive/` when no longer active.

## Active Plan Links

### Primary Active Backlog

- [consolidated-open-tasks-plan-2026-03-21.md](consolidated-open-tasks-plan-2026-03-21.md)

This is now the only active execution/backlog document in `docs/plans/`.

### Retained Operational Context

- [architecture-review-and-refactor-plan-2026-03-21.md](architecture-review-and-refactor-plan-2026-03-21.md)

Earlier operational context files such as
`onboarding-checklist-day-1-2026-03-20.md` and
`project-briefing-capability-discovery-2026-03-20.md` are no longer retained as
published plan pages in this workspace snapshot.

The architecture review plan was refreshed on `2026-03-23` with the current
integral score, updated category table, and RF-style roadmap. It remains a
supporting assessment map, not a second active backlog.

### Retained Historical Context With Live Evidence References

Historical RF-07 planning context is now retained through evidence packs and
archive indexes rather than published plan pages:

- `rf-07-provider-registry-migration-plan-2026-03-20.md`
- `rf-07d-runtime-deferred-wave-plan-2026-03-20.md`

These files are no longer active queues, but are still retained because
evidence packs and historical runtime-ownership references point to them.

### Cleanup Note

On 2026-03-21 the folder was reduced to remove superseded dated execution
plans, absorbed backlog inputs, and completed bounded-cluster plans that were
creating multiple competing “active” surfaces.

## Related Prompt

- [py-qa-orchestrator.md](../00-project/ai/agents/runtime/py-qa-orchestrator.md)
