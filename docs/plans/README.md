# Plans Directory

*Status: Working planning artifacts (non-normative)*
*Last updated: 2026-03-26*

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

- This folder is intentionally **repo-only**, not a MkDocs-published surface.
- Plans may be referenced from canonical docs for discoverability, but they
  remain working materials rather than normative guidance.
- When a plan conflicts with active docs under `docs/00-05`, active docs win.
- Historical or completed plans should move to `docs/99-archive/` rather than
  accumulate as competing active surfaces.

## Maintenance Rules

- Keep file names explicit and date-stamped when possible.
- Prefer updating an existing active plan over creating near-duplicates.
- Move obsolete or historical planning artifacts to `docs/99-archive/` when no longer active.

## Freshness Triggers

Refresh this index, or add a short freshness note to linked dated reports, when:

- a bounded refactor wave closes or materially changes a currently linked plan;
- a supporting assessment in `reports/plans/` or `reports/{LLM}/` still speaks in
  current tense about a now-closed wave;
- active backlog ownership or the “one active backlog” rule changes;
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

This is now the only active execution/backlog document in `docs/plans/`.

### Retained Operational Context

- [architecture-review-and-refactor-plan-2026-03-21.md](architecture-review-and-refactor-plan-2026-03-21.md)
- [curated-memory-density-governance-plan-2026-04-21.md](curated-memory-density-governance-plan-2026-04-21.md)
- [monitoring-observability-expansion-plan-2026-03-26.md](monitoring-observability-expansion-plan-2026-03-26.md)
- [project-memory-layer-implementation-plan-2026-04-20.md](project-memory-layer-implementation-plan-2026-04-20.md)
- [project-memory-layer-issue-pack-2026-04-20.md](project-memory-layer-issue-pack-2026-04-20.md)
- [repository-file-structure-cleanup-plan-2026-04-20.md](repository-file-structure-cleanup-plan-2026-04-20.md)

Earlier operational context files such as
`onboarding-checklist-day-1-2026-03-20.md` and
`project-briefing-capability-discovery-2026-03-20.md` are no longer retained as
active repo entrypoints in this workspace snapshot.

The architecture review plan was refreshed on `2026-03-23` with the current
integral score, updated category table, and RF-style roadmap. It remains a
supporting assessment map, not a second active backlog.

The curated memory density governance plan was added on `2026-04-21` as a
bounded next-wave plan for keeping `src/memory/curated/` small, source-backed,
reviewable, and high-density. It is retained as memory governance planning
context, not as a normative knowledge-management policy.

The monitoring observability expansion plan was added on `2026-03-26` as a
bounded rollout plan for extending the existing Prometheus/Grafana stack around
control-plane and lineage signals. It is retained as supporting operational
context, not as a second active backlog.

The project memory layer implementation plan was added on `2026-04-20` as a
bounded rollout plan for introducing a hybrid project-memory subsystem rooted
in `src/memory/`. It is retained as supporting implementation context, not as a
second active backlog or a normative knowledge-management policy.

The project memory layer issue pack was added on `2026-04-20` as a staging
surface for decomposing that rollout into bounded GitHub issues. It is retained
as implementation support context, not as a second backlog.

The repository file structure cleanup plan was added on `2026-04-20` as a
bounded hygiene and governance-convergence roadmap for root placement policy,
generated artifact cleanup, and report-surface normalization. It is retained as
supporting implementation context, not as a second active backlog.

If later waves close items named in that report, the report should keep its
original date and gain a short freshness note instead of being silently treated
as the live queue.

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
