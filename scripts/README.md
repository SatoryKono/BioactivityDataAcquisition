# Scripts Layout

This directory uses a **canonical-by-domain** structure.

## Canonical Directories

- `scripts/ci/` — CI orchestration and reporting jobs.
- `scripts/dev/` — local developer workflows and setup.
- `scripts/qa/` — architecture/quality/debt checks and reports.
- `scripts/docs/` — docs build, lint, drift checks, docs maintenance.
- `scripts/schema/` — schema/contracts/config invariants tooling.
- `scripts/data/` — data integrity, VCR policy, checksum/Delta utilities.
- `scripts/repo/` — repository hygiene and governance inventory.
- `scripts/ops/` — operational and platform support scripts.
- `scripts/diagnostics/` — manual probes, debug, one-off diagnostics.
- `scripts/migrations/active/` — active/repeatable migrations.
- `scripts/migrations/oneoff/` — one-time migration scripts.
- `scripts/diagrams/` — diagram quality/render tooling.

## Compatibility Policy

Historical entrypoints are kept in `scripts/` root as thin wrappers.

Rules:
- New integrations must target canonical paths under grouped directories.
- Root wrappers exist only for backward compatibility.
- Do not add new non-wrapper scripts to `scripts/` root.

## Inventory Governance

- Check inventory drift:
  - `python scripts/repo/check_scripts_inventory.py --check --manifest configs/quality/scripts_inventory_manifest.json`
- Update inventory manifest:
  - `python scripts/repo/check_scripts_inventory.py --update --manifest configs/quality/scripts_inventory_manifest.json`
- Validate lifecycle coverage for non-active scripts:
  - `python scripts/repo/check_scripts_inventory.py --check-lifecycle --forbid-evaluate-active --lifecycle-registry configs/quality/scripts_lifecycle_registry.json`

## Launcher

Use `scripts/run.py` for discovery and consistent invocation:

- `python scripts/run.py list`
- `python scripts/run.py find quality`
- `python scripts/run.py exec qa check_c901_baseline -- --help`
