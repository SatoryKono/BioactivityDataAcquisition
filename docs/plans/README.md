# Plans Directory

*Status: Working planning artifacts (non-normative)*
*Last updated: 2026-04-28*

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
- The tracked plan set and lifecycle classes are cataloged in
  `configs/quality/repo_structure_catalog.yaml`.

## Maintenance Rules

- Keep file names explicit and date-stamped when possible.
- Prefer updating an existing active plan over creating near-duplicates.
- Move obsolete or historical planning artifacts to `docs/99-archive/` when no longer active.
- Every tracked plan file MUST be present in `configs/quality/repo_structure_catalog.yaml`.
- Only one tracked plan file may hold lifecycle `active_backlog`.

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
- [repository-file-structure-remediation-plan-2026-04-28.md](repository-file-structure-remediation-plan-2026-04-28.md)
- [scripts-cli-wrapper-caller-matrix-2026-04-28.md](scripts-cli-wrapper-caller-matrix-2026-04-28.md)
- [codex-launcher-parity-review-2026-04-28.md](codex-launcher-parity-review-2026-04-28.md)
- [docs-cli-wrapper-closeout-2026-04-28.md](docs-cli-wrapper-closeout-2026-04-28.md)
- [mcp-wrapper-contract-audit-2026-04-28.md](mcp-wrapper-contract-audit-2026-04-28.md)
- [build-docs-site-parity-audit-2026-04-29.md](build-docs-site-parity-audit-2026-04-29.md)
- [mcp-wrapper-deep-audit-2026-04-29.md](mcp-wrapper-deep-audit-2026-04-29.md)

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
generated artifact cleanup, and report-surface normalization. It was refreshed
on `2026-04-21` after the root artifact cleanup wave: the current plan now
tracks policy convergence, generated-artifact routing, AI/editor surface
decisions, and enforcement hardening rather than repeating closed root cleanup
items. It is retained as supporting implementation context, not as a second
active backlog.

The repository file structure remediation plan was added on `2026-04-28` after
an architecture-strict audit found drift between the published root policy and
the live GitHub root snapshot. It supersedes the 2026-04-21 live-state claims
for remediation planning while retaining the older cleanup plan as historical
baseline and policy context. Its current execution state is grounded by
`configs/quality/root_hygiene_review_registry.yaml`, which tracks the
review-required and blocked cleanup lanes against the current live root
baseline. The linked GitHub remediation issue set is `#3219`, `#3223`, `#3226`,
and `#3227`; however, the actual branch-protection admin state for required
checks still needs authenticated owner/admin verification beyond public policy
docs.

The scripts CLI wrapper caller matrix was added on `2026-04-28` as supporting
evidence for RF-008 compatibility-wrapper retention decisions. It is generated
by `python -m scripts.engineering.repo sync-wrapper-caller-matrix` and retained
as operational context for scripts cleanup, not as a second active backlog.

The Codex launcher parity review was added on `2026-04-28` as a bounded
classification note for `scripts/ops/launchers/codex/*`. It distinguishes thin
compatibility wrappers from retained bootstrap and transport adapters so the
scripts cleanup wave does not treat the entire launcher cluster as removable by
default.

The docs CLI wrapper closeout note was added on `2026-04-28` as the bounded
closeout artifact for the `scripts/docs` wrapper wave. It records the removal
of `check_doc_links.py` and `run_mkdocs_build.py`, plus the retained parity
decision for `build_docs_site.sh`.

The MCP wrapper contract audit was added on `2026-04-28` to document why the
named `scripts/ai/mcp/*_wrapper.*` files are contract-bound runtime surfaces
and therefore out of scope for generic wrapper deletion.

The build-docs-site parity audit was added on `2026-04-29` to record the
follow-up redesign decision for `build_docs_site.sh`: retain it only as a shell
transport adapter while keeping all build semantics in
`scripts.docs.build.mkdocs_build`.

The MCP wrapper deep audit was added on `2026-04-29` to classify the retained
`scripts/ai/mcp/` wrapper families by launch semantics, generated-config
contract, and redesign prerequisites. It complements the earlier contract note
with a body-level family map.

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
