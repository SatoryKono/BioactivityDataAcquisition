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

Live counts below were re-measured 2026-09-23 (`#10610`/`#10611`). Grafana/ops Python
under `scripts/ops/observability/grafana/` stays outside RF-06 hotspot families
(decision C / `#10447`); do not fold those files into `debt_scorecard.yaml`
without a separate ADR.

Hash-only coverage refresh (`--allow-missing-coverage-xml`) hashes all
`src/bioetl/**/*.py` and drops deleted inventory paths. It does not add rows
for new modules until a coverage XML refresh. After `#10610` the committed
inventory matches the live tree (`source_module_count=2479`) because
`src/bioetl/composition/runtime_builders/inputs_extraction_preflight.py` was
added as a fully-covered additive row. `composition_runtime_builders` family
inventory is 56 modules (measured=56); hotspot coverage floors were ratcheted
to those live counts without raising debt budgets.

| Scanner | Artifact / command | What it counts |
| --- | --- | --- |
| Coverage inventory | `reports/quality/module-coverage-inventory.json` | Coverage-fact rows for `src/bioetl/**/*.py` that still exist in the tree (currently 2499 rows; live tree 2499 files). `report-module-coverage --check --allow-missing-coverage-xml` refreshes `source_tree_sha256` and drops deleted paths; new modules are added only from a coverage XML refresh (`--refresh-nonregressing-from-coverage-xml` or the coverage-verify lane). |
| Dependency map | `docs/02-architecture/generated/module-dependency-map.json` | Live modules with a resolvable hexagonal layer + group (currently 2495). Excludes package-root `bioetl` and `bioetl.__main__` (no hexagonal layer tag). |
| import-linter | `lint-imports --no-cache` (`.importlinter`) | Importable files in the `bioetl` package graph (2426 files in the 2026-09-23 review pass; Windows: `importlinter.cli.lint_imports(..., no_cache=True)` when `lint-imports.exe` is absent). Excludes stubs / non-imported modules |

`families_at_budget` on the architecture scorecard is currently empty after
`#10468`: `application_services_control_plane` fan-in is 1/2 and
`composition_runtime_builders` fan-in is 2/3. `module_boundaries_coupling` is
10.0. Do not raise the fan-in or loc caps; keep new internal imports and
oversized files flat. `composition_factories_pipeline` `files_ge_250_loc` is
0/0 (budget unchanged). `application_core` live LOC is 23443 with `files=194`
(budget unchanged).

Closeout evidence: `tests/architecture/test_issue_10468_module_boundaries_coupling_closeout.py`
and `reports/quality/hotspot-family-baseline.json`.

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
