# Decision: `bioetl.infrastructure.config` package-root is permanent public API

**Date:** 2026-07-27  
**Linked issue:** #6682 (TD-R-06)  
**Supersedes design-only closeout:** #6624 (TD-08)

## Decision

Keep `bioetl.infrastructure.config` as a **permanent external public API** convenience facade.

It is **not** transition debt and is **not** scheduled for removal. First-party `src/` importers remain forbidden (max_src_importer_count = 0); external consumers may import sanctioned package-root symbols.

## Terminal state

| Option | Chosen |
|---|---|
| Remove after deprecation window | No |
| Promote to permanent public product API | **Yes** |

## Rationale

1. Inventory already marks `sunset_status: permanent` and export contract budget.
2. Compatibility census shows zero first-party `src` importers through the root.
3. Removal would force an external breaking change without product benefit while owner modules remain available for internal code.
4. Governance continues via `infrastructure_config_root_facade_inventory.yaml` and freeze CI (TD-R-07).

## Constraints retained

- Ordinary first-party runtime code imports owner modules (`_base`, `contract_policy_loader`, …).
- Package-root growth requires architecture review + inventory update.
- Twin / transition metrics stay at zero.

## Evidence

- `configs/quality/compatibility_facade_inventory.yaml`
- `configs/quality/infrastructure_config_root_facade_inventory.yaml`
- `configs/quality/internal_compatibility_shim_inventory.yaml`
- `reports/quality/compatibility-importer-census.json`
