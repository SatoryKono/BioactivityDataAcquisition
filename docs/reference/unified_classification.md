# Unified publication-type classification: canonical format and locations

## Canonical format

Canonical source for machine consumption is **CSV**:

- `data/input/reference/unified_classification.csv`

Rationale:

- CSV is diff-friendly and reviewable in Git.
- CSV is directly consumable by scripts without Excel-specific dependencies.

## Human-friendly companion

Optional Excel copy for manual review:

- `docs/reference/unified_classification.xlsx`

This file is non-canonical and must be kept synchronized from CSV when updated.

## Repository placement policy

Domain datasets and reference tables must not be stored in repository root.
Use semantic directories under `data/` (runtime/input artifacts) and `docs/` (human reference).
