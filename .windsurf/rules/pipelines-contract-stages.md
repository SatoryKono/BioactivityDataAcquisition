> Scope:
> - USE WHEN implementing pipelines; follow standard contract stages
> - Use when editing files matching: `src/bioetl/pipelines/**/*.py`, `docs/etl_contract/**/*.md`
# MANDATORY
- Implement the standard ETL sequence: `extract → transform → validate → export`.

# GOOD
Each pipeline class provides these stage methods; validation precedes export.

# REFERENCE
See ../../docs/styleguide/08-etl-architecture.md
