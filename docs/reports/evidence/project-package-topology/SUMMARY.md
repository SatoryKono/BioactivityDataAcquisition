# Сводка evidence: project-package-topology

Дата: 2026-08-17
Статус: refreshed

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see
`docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md`
for wave status, retained-vs-reopened interpretation, and current review scope.

Refresh note (2026-07-19): the summary was remeasured from the live working
tree with deterministic Python file and first-order package scans excluding
`__pycache__`. The summary is reconciled with the source-tree portion of
`reports/quality/module-coverage-inventory.json` after running the canonical
module-coverage producer. The inventory retains its `2026-07-28` coverage-data
snapshot date because no newer canonical coverage run was substituted for the
tracked coverage measurements.

Current-baseline note (2026-08-17): architectural planning and GitHub issues
MUST cite this summary or a newer regenerated package-topology pack for current
counts. The current source baseline is
`source_module_count=2431` with
`source_tree_sha256=e10426c41d09fa9c54e524f1bf4556269d6de7a13d7734a0b271c3f17092534d`.
Raw files dated before `2026-07-19` are retained only as historical detailed
inputs and must be refreshed before they are used for line-item topology
evidence. Refresh (2026-08-05) followed the #4343 composite facade narrowing
and related module-coverage inventory hash-only reconcile.

Refresh note (2026-08-17): remeasured after the validation-helper and
service-invocation refactors. Source baseline remains
`source_module_count=2431` with the updated `source_tree_sha256` above; the
module-coverage inventory was reconciled with its canonical source-tree-only
refresh path (coverage measurements were preserved).

Pandera bootstrap ownership remains reconciled with the current runtime:
`apply_runtime_compatibility_patches` is a no-op compatibility seam, while the
retired Pandera-specific validation shim and import-time side effects stay
absent.

> Это summary — repo-only evidence layer для package-topology
> интерпретации. Он помогает калибровать structural observations, но не
> заменяет canonical architecture guidance в `docs/00-project/` и
> `docs/02-architecture/`.

## Созданные объекты evidence

1. `EV-project-package-topology-top-level-repo-zones-are-separated`
1. `EV-project-package-topology-application-layer-has-six-subpackages`
1. `EV-project-package-topology-composition-layer-has-five-subpackages`
1. `EV-project-package-topology-domain-layer-has-twenty-two-subpackages`
1. `EV-project-package-topology-infrastructure-layer-has-twenty-subpackages`
1. `EV-project-package-topology-interfaces-layer-has-two-subpackages`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Ключевые выводы

- The repository is not flat at the top level; it is split into clear zones
  for source, config, tests, scripts, docs, and reports.
- `src/bioetl/` reflects the intended layered architecture through distinct
  first-order package groups.
- Current Python file count under `src/bioetl` is `2427`, including two
  top-level package modules outside the five first-order architecture layers.
- Current layer file counts are: `domain=609`, `application=750`,
  `infrastructure=626`, `composition=283`, `interfaces=157`.
- Current first-order package counts are: `domain=22`, `application=6`,
  `infrastructure=20`, `composition=5`, `interfaces=2`.
- `application` and `infrastructure` remain the broadest package surfaces by
  Python file count; `infrastructure` remains the broadest adapter and
  external-system implementation boundary.

## Gaps

- This package-topology evidence confirms structure, not health, ownership, or
  API quality.
- The evidence does not inspect deeper module contents within each package
  beyond structural partitioning.
- Historical raw evidence files under this evidence pack still carry older
  snapshots; refresh those raw files before using them for line-item topology
  decisions.

## Source tree stamp

- source_tree_sha256: `e1c200a48a3cf63954919f44d80967fe668ef96fefd0cece930392e02a976c6a`

`source_module_count=2431`
