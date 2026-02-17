# Composite Molecule Pipeline

*Updated: 2026-02-17*

## Overview

Merges ChEMBL molecules with PubChem compound data to produce a composite molecule table.

Current molecule pipeline remains a single-table composite contract, but aligns with ADR-035 decomposition principles:

- canonical fields SHOULD stay provider-agnostic;
- provider-qualified fields SHOULD be isolated when extension cardinality grows;
- lineage metadata SHOULD remain separable from analytical fields.

## Identity

| Field       | Value                                       |
| ----------- | ------------------------------------------- |
| Pipeline ID | `composite_molecule`                        |
| Provider    | `composite`                                 |
| Entity      | `molecule`                                  |
| Version     | `1.1.0`                                     |
| Config      | `configs/pipelines/composite/molecule.yaml` |

## Seed and Enrichers

- **Seed**: `chembl_molecule`
- **Enricher**: `pubchem_compound`
- **Join keys**: `inchi_key` (primary), `canonical_smiles` (fallback)

## Outputs

| Layer  | Path                                    |
| ------ | --------------------------------------- |
| Silver | `data/output/silver/composite/molecule` |
| Gold   | `data/output/gold/composite/molecule`   |

## Related Configs

- Filters: `configs/filters/entities/composite/molecule.yaml`

## Related ADRs

- [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-028](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-035](../../02-architecture/decisions/ADR-035-composite-decomposition-strategy.md)
