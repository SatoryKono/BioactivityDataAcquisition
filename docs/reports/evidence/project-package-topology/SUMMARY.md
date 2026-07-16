# Сводка evidence: project-package-topology

Дата: 2026-07-13
Статус: refreshed

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Refresh note (2026-07-13): top-level package counts were remeasured from the
working tree with `find src/bioetl ... -name '*.py'` and first-order package
directory scans excluding `__pycache__`. Targeted raw evidence snapshots for the
`interfaces`, `composition`, and `application` pillar packs were refreshed in
place to remove known topology drift; older `2026-03-20` raw evidence files in
other layer packs remain historical inputs and should not be treated as the
latest package-count baseline.

Current-baseline note (2026-07-13): architectural planning and GitHub issues
MUST cite this summary or a newer regenerated package-topology pack for current
counts. The current baseline is reconciled with
`reports/quality/module-coverage-inventory.json` snapshot `2026-07-13`
(`source_module_count=2226`,
`source_tree_sha256=5d910a3d52558b336af19c1d64804cdbfec59f0a1711fad321a104a02f436f31`).
Raw files dated before `2026-07-13` are retained only as historical detailed
inputs and must be refreshed before they are used for line-item topology
evidence.

> Это summary — repo-only evidence layer для package-topology
> интерпретации. Он помогает калибровать structural observations, но не
> заменяет canonical architecture guidance в `docs/00-project/` и
> `docs/02-architecture/`.

## Созданные объекты evidence

1. `EV-project-package-topology-top-level-repo-zones-are-separated`
1. `EV-project-package-topology-application-layer-has-six-subpackages`
1. `EV-project-package-topology-composition-layer-has-six-subpackages`
1. `EV-project-package-topology-domain-layer-has-twenty-two-subpackages`
1. `EV-project-package-topology-infrastructure-layer-has-twenty-subpackages`
1. `EV-project-package-topology-interfaces-layer-has-two-subpackages`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Ключевые выводы

- The repository is not flat at the top level; it is split into clear zones for source, config, tests, scripts, docs, and reports.
- `src/bioetl/` reflects the intended layered architecture through distinct first-order package groups.
- Current Python file count under `src/bioetl` is `2226`, including two
  top-level package modules outside the five first-order architecture layers.
- Current layer file counts are: `domain=566`, `application=664`, `infrastructure=584`, `composition=274`, `interfaces=136`.
- Current first-order package counts are: `domain=22`, `application=6`, `infrastructure=20`, `composition=5`, `interfaces=2`.
- `application` and `infrastructure` are now the broadest package surfaces by Python file count; `infrastructure` remains the broadest adapter and external-system implementation boundary.

## Gaps

- This package-topology evidence confirms structure, not health, ownership, or API quality.
- The evidence does not yet inspect deeper module contents within each package beyond structural partitioning.
- Historical raw evidence files under this evidence pack still carry older
  snapshots; refresh those raw files before using them for line-item topology
  decisions.
