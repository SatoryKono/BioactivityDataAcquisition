# scripts/engineering — Canonical Engineering Script Surface

The `scripts/engineering/` tree is the canonical home for engineering-facing
tooling and the scripts governance index.

## Scope

- `scripts/engineering/ci` — CI orchestration, resiliency runners, and compatibility telemetry.
- `scripts/engineering/dev` — local developer setup and test utilities.
- `scripts/engineering/qa` — architecture and quality-gate checks.
- `scripts/engineering/repo` — repository governance, inventory, and catalog validation.
- `scripts/engineering/diagnostics` — manual diagnostics helpers.
- `scripts/engineering/baselines` — baseline artifacts consumed by quality gates.
- `scripts/engineering/common` — shared engineering script helpers.

## Canonical Entry Points

Use grouped module entrypoints where available:

```bash
python -m scripts.engineering.dev --help
python -m scripts.engineering.qa --help
python -m scripts.engineering.repo --help
python -m scripts.engineering.baselines --help
python scripts/engineering/run.py --help
```

## Frequently Used Commands

```bash
python -m scripts.engineering.qa report-dep-map --check
python -m scripts.engineering.repo check-catalog --catalog scripts/engineering/repo/catalog.yaml
python -m scripts.engineering.repo check-inventory --check --manifest configs/quality/scripts_inventory_manifest.json
python -m scripts.engineering.baselines dq-baseline --dry-run
python -m scripts.engineering.dev migrate-deprecated-names src/
```

## Catalog

`scripts/engineering/repo/catalog.yaml` is the governance manifest for canonical
roots and group ownership. If you add or relocate script domains, update the
catalog and rerun the repo governance checks.

## Compatibility Policy

- Historical root-level wrappers have been consolidated into canonical domain packages.
- New integrations should target grouped module commands or canonical package paths only.
- Archive-only paths under `scripts/ops/archive/**` are historical context and
  should not be used as canonical command targets.
- Historical evidence under `docs/reports/evidence/**` may still mention removed
  paths; treat those references as archival, not canonical guidance.
