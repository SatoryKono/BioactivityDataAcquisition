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
python -m scripts.engineering.qa find-complex-functions
python -m scripts.engineering.repo check-catalog --catalog scripts/engineering/repo/catalog.yaml
python -m scripts.engineering.repo check-inventory --check --manifest configs/quality/scripts_inventory_manifest.json
python -m scripts.engineering.baselines dq-baseline --dry-run
python -m scripts.engineering.dev migrate-deprecated-names src/
```

For manual, non-gating structural inspection, the bounded supporting utilities
`scripts/engineering/qa/count_source_lines.py` and
`scripts/engineering/qa/get_large_modules.py` remain available. Their output is
diagnostic only; committed module-coverage and hotspot artifacts remain the
authoritative quality inputs.

## Catalog

`scripts/engineering/repo/catalog.yaml` is the governance manifest for canonical
roots and group ownership. If you add or relocate script domains, update the
catalog and rerun the repo governance checks.

## Scripts inventory policy (hold flat)

`configs/quality/scripts_inventory_manifest.json` is the machine inventory for
`scripts/**` (status classes: **active**, **supporting**, **temporary_diagnostic**).
Current counts are authoritative only in `summary.status_counts` of that
manifest and are intentionally not duplicated here. The catalog gate enforces
`active <= lifecycle.active_script_count_max`; the cap may only stay flat or
shrink.

When adding or renaming a script:

1. Register it in the inventory with an explicit class (`active` /
   `supporting` / `temporary_diagnostic`) via
   `python -m scripts.engineering.repo sync-inventory` (or the equivalent
   check/update path) so CI drift stays green.
2. Prefer a single canonical entrypoint (`python -m scripts...` or one
   language-native runner). Dual `.sh` / `.ps1` wrappers are allowed **only**
   when an operator transport truly requires both; do not pair wrappers by
   default.
3. Do not mass-delete scripts without ownership review and non-use evidence.
   Hold the surface flat-or-down (issues #7711 / #7735).

## Compatibility Policy

- Historical root-level wrappers have been consolidated into canonical domain packages.
- New integrations should target grouped module commands or canonical package paths only.
- Archive-only paths under `scripts/ops/archive/**` are historical context and
  should not be used as canonical command targets.
- Historical evidence under `docs/reports/evidence/**` may still mention removed
  paths; treat those references as archival, not canonical guidance.
