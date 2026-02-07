# Schema Inventory CI Check

## Root schema paths

Inventory and orphan checks are executed on these roots (replacing legacy `application/transformers/schemas` scope):

- `src/bioetl/infrastructure/schemas/**`
- `src/bioetl/domain/**` (entities/types/exceptions and other model containers)
- `src/bioetl/application/**` (DTO and typed service structures)

Source of truth: `configs/schema_roots.yaml`.

## Model type inventory

`python scripts/check_schema_inventory.py` builds inventory by model kind:

- `BaseModel`
- `dataclass`
- `TypedDict`
- `Protocol`
- Pandera models (`DataFrameModel` descendants)

## Orphan schema detection (including tests)

Orphan detection scans usages in:

- `src/**/*.py`
- `tests/**/*.py`

This explicitly treats references in `tests/**` as valid usage.

## Medallion schema generation block

The check also emits `medallion_schema_generation` entries bound to real pipeline configs under:

- `configs/pipelines/**/*.yaml`

Each entry links pipeline config to generator targets for Bronze/Silver/Gold schema surfaces.

## CI check script

- Strict CI mode:
  - `make schema-inventory-check`
  - runs: `python scripts/check_schema_inventory.py --fail-on-orphans --report-json reports/schema_inventory_report.json`
- Local audit mode (non-blocking):
  - `python scripts/check_schema_inventory.py --report-json reports/schema_inventory_report.json`

Output artifact:

- `reports/schema_inventory_report.json`

This closes the scope as: **root schemas + generators + CI check script**.
