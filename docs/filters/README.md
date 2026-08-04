______________________________________________________________________

Version: 0.3.0
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-04'

______________________________________________________________________

# Filters Surface (inventory + ADR pointer)

This folder is **not** a canonical ADR source. It retains only:

1. the committed silver-filter inventory baseline (generated control artifact);
2. this pointer to the normative filter-boundary decision.

## Normative source of truth

Use **ADR-050** for Silver structural / Gold semantic filter-boundary
governance:

- `docs/02-architecture/decisions/ADR-050-silver-structural-gold-semantic-filter-boundary.md`

Accepted ADR-048 is the domain-schema/Pandera compatibility decision
(`docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`).
Do **not** cite historical local filter drafts as ADR-048. Use ADR-050 for
normative filter-boundary governance.

## Active artifacts

| File | Type | Status |
| --- | --- | --- |
| `inventory-baseline.md` | Inventory report | Generated; regenerated via script below |
| `inventory-baseline.csv` | Inventory data | Generated |
| `inventory-baseline.json` | Inventory data | Generated |

Historical migration prose was archived on 2026-08-04 (docs audit cycle 2 /
#7428):

- `docs/99-archive/filters/migration-plan.md`
- `docs/99-archive/filters/retired-silver-filters-structural-scope.md`

## Compatibility implementation anchors

- `src/bioetl/infrastructure/config/silver_filter_migration.py`
- `src/bioetl/infrastructure/schemas/filter_config.py`
- `src/bioetl/infrastructure/schemas/pipeline_config.py`
- `src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py`

## How to regenerate the inventory

```powershell
python scripts/data_quality/inventory_silver_filters_migration.py
```

Routed outputs (do not rename without updating
`configs/quality/generated_artifact_routing.yaml`):

- `docs/filters/inventory-baseline.csv`
- `docs/filters/inventory-baseline.json`
- `docs/filters/inventory-baseline.md`
