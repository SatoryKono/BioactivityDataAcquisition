# Plans Directory

*Status: Working planning artifacts (non-normative)*
*Last updated: 2026-07-28 (DOC-GOV-08 / #6888)*

This directory holds **active** planning surfaces only. Completed plans live in
`docs/99-archive/plans/`.

## Scope

- Planning and decomposition for upcoming work
- Temporary execution plans that can be superseded
- Non-authoritative operational guidance

## Source of truth

Plans must not override:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `docs/02-architecture/decisions/`

## Publication hygiene

- Repo-only (MkDocs `exclude_docs: plans/**`)
- Cataloged in `configs/quality/repo_structure_catalog.yaml`
- Only one tracked plan may hold lifecycle `active_backlog`
- Historical/completed plans → `docs/99-archive/plans/`

## Freshness Triggers

Refresh this index, or add a short freshness note to linked dated reports, when:

- a bounded refactor wave closes or materially changes a currently linked plan;
- a supporting assessment in `reports/plans/` or `reports/{LLM}/` still speaks in
  current tense about a now-closed wave;
- active backlog ownership or the "one active backlog" rule changes;
- an index entry stops being a live planning surface and becomes only historical context.

Protocol:

- Keep `docs/plans/README.md` focused on the current reading order.
- For dated supporting assessments, prefer adding a `Freshness note` rather than
  rewriting their original date/history.
- Move superseded planning surfaces to archive only when they are no longer
  needed for active evidence references.

## Active Plan Links

### Primary Active Backlog

- [consolidated-open-tasks-plan-2026-03-21.md](consolidated-open-tasks-plan-2026-03-21.md)

This is the only active execution/backlog document in `docs/plans/`.

### Archived context (DOC-GOV-08)

Supporting context plans previously retained under `docs/plans/` were moved to
[docs/99-archive/plans/](../99-archive/plans/) on 2026-07-28. Use the archive
index for historical reading order; do not treat archived plans as live queues.

## Related

- [docs/99-archive/plans/](../99-archive/plans/)
- [docs/99-archive/engineering/](../99-archive/engineering/) (former `05-engineering` closeouts)
- `configs/quality/repo_structure_catalog.yaml`
