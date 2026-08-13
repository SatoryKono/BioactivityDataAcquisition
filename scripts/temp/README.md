# Temporary Diagnostic Scripts

This directory holds **temporary** diagnostic scripts with bounded lifecycles.
Every executable below `scripts/temp/` (`.py`, `.sh`, `.ps1`, `.cmd`, `.bat`),
except the package marker `__init__.py`, MUST:

- be listed in this README
- `configs/quality/scripts_lifecycle_registry.json` (`decision: temporary_diagnostic`, with `review_by`)
- `configs/quality/scripts_inventory_manifest.json` (`status: temporary_diagnostic`)

## Scripts

_No temporary diagnostic executables are currently checked in._

Campaign helpers retired in tech-debt closeout (#8709 / #8705):
basedpyright snapshot generators, Grafana contour cycle-2 tools, and one-shot
issue/merge helpers. Reintroduce only with owner + `review_by` ≤ 30 days.

## Lifecycle Management

- **Owners:** `@bioetl-platform`, `@bioetl-observability`
- **Policy:** no perpetual `temporary_diagnostic` without a near-term `review_by`
