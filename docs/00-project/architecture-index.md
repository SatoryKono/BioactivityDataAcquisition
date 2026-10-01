______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-23'

______________________________________________________________________

# Архитектурные документы (канонические ссылки)

Этот индекс фиксирует канонические ссылки на архитектурные документы, которые
часто упоминаются в аудиторских шаблонах.

Для published contracts, CLI surfaces, provider/pipeline specs и API reference
используйте [Reference Index](../04-reference/index.md); этот индекс покрывает
именно architecture-side entry points.

| Запрошенный документ  | Канонический документ                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Domain Objects        | [01-domain-layer.md](../02-architecture/01-domain-layer.md)                                                         |
| ETL Layers            | [data-layers.md](../02-architecture/data-layers.md)                                                                 |
| Composite entities    | [composites.md](../04-reference/pipelines/composites.md)                                                            |
| Data Flow             | [data-flow.md](../02-architecture/diagrams/guide/data-flow-reference.md)                                            |
| Duplication Reduction | [module-consolidation-migration-requirements.md](../02-architecture/module-consolidation-migration-requirements.md) |
| Physical Layout       | [03-file-policy.md](governance/03-file-policy.md) + [local-storage-layout.md](../03-guides/local-storage-layout.md) |
| DQ Contract System    | [ADR-045-dq-contract-system.md](../02-architecture/decisions/ADR-045-dq-contract-system.md)                         |

> **Примечание:** Ранее использовались файлы-алиасы (`01-domain-objects.md`,
> `02-etl-layers.md` и т.д.) в `docs/00-project/`. Они удалены — используйте
> канонические документы напрямую.

## Workflow Control Plane (ADR-047)

- Target model: immutable `WorkflowManifest`, append-only `WorkflowLedger`, and mutable `WorkflowExecutionState`.
- Local runtime safety: one `MemoryLock` per workflow name (ADR-010 local-only boundary).
- Operator command flow: `bioetl workflow run`, `--resume-last`, `--repair-steps`, `--force-steps`, `bioetl workflow status`.

Canonical sources:

- [ADR-047](../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- [Workflow Object](../03-guides/workflows.md)
- [Workflow Control-Plane Recovery](../05-operations/runbooks/workflow-control-plane.md)
- [POST_CHANGE_VALIDATION](ai/agents/policy/POST_CHANGE_VALIDATION.md)

Deprecated framing (do not use):

- resume logic as ledger-only mutable state;
- resume keyed only by workflow name without execution fingerprint.

## Architecture scanner census

Three architecture scanners count different populations. They are not interchangeable
and a numeric gap is not a layer violation. Re-measure with the live commands before
copying these integers forward.

Snapshot: 2026-10-01, source commit `d50ecd5f35bd`.
Composition contains **282** Python modules (`src/bioetl/composition/**/*.py`,
including package initializers); its cap remains **295**, shrink-only.
Grafana/ops Python under `scripts/ops/observability/grafana/` stays outside
RF-06 hotspot families (decision C / `#10447`).

| Scanner | Artifact / command | What it counts |
| --- | --- | --- |
| Coverage inventory | `reports/quality/module-coverage-inventory.json` | Coverage-fact rows for existing source modules. Hash-only refresh drops deleted paths but adds new modules only after coverage XML measurement. Check `source_module_count` against the live tree before claiming complete measurement. |
| Dependency map | `docs/02-architecture/generated/module-dependency-map.json` | Live modules with a resolvable hexagonal layer and group; excludes package-root modules without a layer tag. |
| import-linter | `lint-imports --no-cache` (`.importlinter`) | Importable files in the package graph; excludes stubs and non-imported modules. Its count is not the coverage denominator. |

Read current family files, LOC, fan-in and budget warnings from
`reports/quality/hotspot-family-baseline.json` and the architecture scorecard.
Historical counts from earlier reviews are not live acceptance evidence.
Do not raise module, LOC, fan-in or duplication caps to reconcile a snapshot.

## Architecture scorecard semantics

`reports/quality/architecture-quality-scorecard.json` is a diagnostic grade,
not an independent proof that every architecture program gate is satisfied.
The `ddd_invariants` category uses module coverage status as a proxy; it does
not count aggregates or prove invariant completeness. The
`module_boundaries_coupling` category uses hotspot budget warnings and duplicate
clusters as proxies; families exactly at budget and cap saturation (lazy-import
utilisation, composition module count) **do** reduce the diagnostic grade.
Program-gate `max_count` / `max_modules` remain shrink-only and are not raised
by scorecard regeneration. Clean posture scores 10.0; live integral is sensitive
to those diagnostics (`schema_version` 2).

Interpretation bands (`_interpretation` in
`src/bioetl/infrastructure/quality/architecture_quality_scoring.py`) match
`prompt.architecture.cycle`:

| Band | integral | Machine token |
| --- | --- | --- |
| excellent | ≥ 9.5 | `excellent` |
| good / targeted improvements | [8.5, 9.5) | `good_targeted_improvements` |
| needs work | [5.0, 8.5) | `satisfactory_system_refactoring_required` |
| weak / critical | < 5.0 | `critical` |

The two lower machine tokens keep the committed names; they are not a separate
taxonomy. An integral of 10.0 is `excellent`, not `good_targeted_improvements`.
