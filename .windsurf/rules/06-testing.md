> Scope:
> - USE WHEN writing tests or changing code paths; enforce categories, golden tests, property tests, coverage >=85%
> - Use when editing files matching: `tests/**/*.py`, `src/**/*.py`
# CATEGORIES (pytest markers)

unit, integration, golden, determinism, property, schema, qc, slow, api, benchmark.

## RULES

- Unit tests do NOT hit network; mock external calls.
- Golden tests protect critical outputs and schemas.
- Use Hypothesis for transformation properties.
- CI blocks merge if coverage < 85% for `src/bioetl`.

## STRUCTURE

- Files `test_*.py`; functions `test_*`; classes `Test*`.

## REFERENCE

See [docs/styleguide/05-testing-standards.md](../../docs/styleguide/05-testing-standards.md) for detailed documentation.
