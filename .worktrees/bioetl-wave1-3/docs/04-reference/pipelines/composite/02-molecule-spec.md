# Composite Molecule Pipeline

*Updated: 2026-02-03*

## Overview

Merges ChEMBL molecules with PubChem compound data to produce a composite molecule table.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite_molecule` |
| Provider | `composite` |
| Entity | `molecule` |
| Version | `1.0.0` |
| Config | `configs/composites/molecule.yaml` |

## Seed and Enrichers

- **Seed**: `chembl_molecule`
- **Enricher**: `pubchem_compound`
- **Join keys**: `inchi-key` (primary), `canonical-smiles` (fallback)

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/molecule` |
| Gold | `data/output/gold/composite/molecule` |

## Related Configs

- Filters: `configs/composites/molecule.yaml#filters`

## Related ADRs

- [ADR-026](../../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-028](../../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
