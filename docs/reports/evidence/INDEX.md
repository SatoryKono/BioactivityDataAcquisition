# Evidence Index

Status: reviewed subset refreshed on 2026-06-19

This directory contains the project's evidence packages. The canonical path is `docs/reports/evidence` (not `docs/results/evidence`).

Use [../index.md](../index.md) for the higher-level reports surface map; use
this page when you specifically need evidence-pack navigation.

## Surface Type

- `docs/reports/evidence/` is a **repo-only evidence surface** tracked from the
  repository, not from the published MkDocs site.
- Evidence packs are designed for research traceability, synthesis,
  decisions, risks, and implementation planning.
- They can be newer or more detailed than canonical guides for a specific
  investigation, but they still do not replace active project guidance in
  `docs/00-project/`, `docs/02-architecture/`, `docs/03-guides/`, or
  `docs/04-reference/`.
- When an evidence pack and canonical guidance disagree, treat that as a
  signal to verify and reconcile, not as automatic authority for the evidence
  layer.
- High-signal summaries that still influence planning should either be
  refreshed after major closeout waves or carry an explicit rebaseline/freshness
  note. Historical raw evidence remains preserved as-is.

## Freshness Model

- `SUMMARY.md`, `INDEX.md`, and cross-synthesis pages are the preferred refresh
  layer for evidence packs.
- Raw notes, dated backlog items, and historical shard captures should usually
  remain unchanged unless they are themselves the subject of the audit.
- If a formerly current recommendation becomes historical trigger evidence,
  mark that fact in the top summary instead of rewriting the whole pack.

## Package Inventory

This table is a curated reviewed subset, not a full filesystem inventory. The
current `docs/reports/evidence/` root contains 50 top-level evidence packages as
of the 2026-06-19 architecture-quality audit. Use this index for reviewed
navigation and use the filesystem inventory when exhaustive package accounting
is required.

| Package                                            | Summary | Orchestration | Synthesis | Decisions | Risks |
| -------------------------------------------------- | ------- | ------------- | --------- | --------- | ----- |
| `adapter-interface-alignment`                      | yes     | no            | yes       | yes       | yes   |
| `architecture-doc-drift`                           | yes     | no            | yes       | no        | no    |
| `architecture-foundations`                         | yes     | no            | yes       | yes       | yes   |
| `code-duplication-dead-code`                       | yes     | yes           | yes       | yes       | yes   |
| `compatibility-registry-curated-ssot-drift`        | yes     | no            | yes       | no        | no    |
| `compatibility-registry-policy-history-mixing`     | yes     | no            | yes       | no        | no    |
| `compatibility-registry-refactor`                  | yes     | yes           | yes       | yes       | yes   |
| `compatibility-registry-snapshot-automation-drift` | yes     | no            | yes       | no        | no    |
| `composition-package-topology`                     | yes     | no            | yes       | yes       | yes   |
| `data-observability-audit`                         | yes     | no            | no        | no        | no    |
| `dependency-hotspots`                              | yes     | no            | yes       | yes       | yes   |
| `documentation-internal-surface-governance`        | yes     | no            | yes       | yes       | yes   |
| `documentation-publication-remediation`            | yes     | no            | yes       | yes       | yes   |
| `documentation-remediation-options`                | yes     | no            | yes       | yes       | yes   |
| `file-naming-drift`                                | yes     | no            | yes       | no        | no    |
| `function-naming-drift`                            | yes     | no            | yes       | no        | no    |
| `governance-signals`                               | yes     | no            | yes       | yes       | yes   |
| `infrastructure-package-topology`                  | yes     | no            | no        | no        | no    |
| `interfaces-package-topology`                      | yes     | no            | no        | no        | no    |
| `object-families-hierarchy`                        | yes     | yes           | yes       | yes       | yes   |
| `object-naming-drift`                              | yes     | no            | yes       | no        | no    |
| `operations-generated-doc-drift`                   | yes     | no            | yes       | no        | no    |
| `pipeline-config-loader-ownership`                 | yes     | no            | yes       | yes       | yes   |
| `project-and-ai-doc-drift`                         | yes     | no            | yes       | no        | no    |
| `project-diagram-artifact-surface`                 | yes     | yes           | yes       | yes       | yes   |
| `project-diagrams-refactor`                        | yes     | yes           | yes       | yes       | yes   |
| `project-documentation-drift`                      | yes     | yes           | yes       | yes       | yes   |
| `project-evidence-rebaseline`                      | yes     | yes           | yes       | no        | no    |
| `project-file-structure`                           | yes     | no            | yes       | yes       | yes   |
| `project-import-governance`                        | yes     | yes           | yes       | yes       | yes   |
| `project-naming-drift`                             | yes     | yes           | yes       | yes       | yes   |
| `project-package-topology`                         | yes     | no            | yes       | yes       | yes   |
| `project-package-topology-recursive`               | yes     | yes           | yes       | yes       | yes   |
| `project-test-health`                              | yes     | yes           | yes       | yes       | yes   |
| `provider-registry-runtime-ownership`              | yes     | no            | yes       | yes       | yes   |
| `refactor-backlog-calibration`                     | yes     | no            | yes       | yes       | yes   |
| `reference-guide-doc-drift`                        | yes     | no            | yes       | no        | no    |
| `scripts-layer-governance`                         | yes     | no            | no        | no        | no    |
| `src-bioetl-refactor-facts`                        | yes     | yes           | yes       | no        | no    |
| `technical-debt`                                   | yes     | yes           | yes       | yes       | yes   |
| `variable-naming-drift`                            | yes     | no            | yes       | no        | no    |

## Current Notes

- Use evidence packs for decision support and historical traceability, not as
  a substitute for canonical rule/reference pages.
- The previously tracked merged docs export is now treated as an on-demand
  generated artifact; related reader-confusion risk remains tracked under
  `operations-generated-doc-drift` as derivative-surface governance rather
  than as a permanently committed stale file.
- `project-evidence-rebaseline` remains the parent closeout pack for repo-wide
  freshness waves across mutable evidence families.
- `project-test-health` is fully refreshed to the current live-provider state.
- `scripts-layer-governance` captures the current repo-wide script inventory
  closeout where unknown/orphan script classes were reduced to `0` and the
  remaining non-active surface was converted into explicit legacy policy.
- `documentation-internal-surface-governance` is refreshed to the current
  `published` vs `repo-only` boundary model; do not read its older
  `internal-published` posture for `plans/**` and `reports/**` as current.
- `data-observability-audit` captures the current evidence-backed assessment
  of runtime metrics/logs/traces/control-plane visibility and the next-wave
  improvement plan for short-lived data runs.
- `project-test-health/semanticscholar-pilot-options` is retained as a historical pre-promotion shard.
- `project-test-health/semanticscholar-enforced-options` is the active post-promotion shard.
- `src-bioetl-refactor-facts` is now stored under the canonical
  `docs/reports/evidence/` root; the former standalone `evidence01` location
  has been folded into the package inventory.
- Some packages intentionally do not yet have full synthesis or decision/risk
  layers; the inventory table above records that explicitly instead of hiding
  it.
