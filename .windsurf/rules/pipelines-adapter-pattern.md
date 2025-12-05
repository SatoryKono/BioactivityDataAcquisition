> Scope:
> - USE WHEN integrating external sources; implement an adapter and delegate extract to it
> - Use when editing files matching: `src/bioetl/clients/**/*.py`, `src/bioetl/pipelines/**/*.py`
# MANDATORY
- External API/data access goes through a dedicated adapter class; pipelines delegate fetch/normalize to the adapter.

# BENEFIT
Decouples source-specific logic from pipeline orchestration; simplifies testing.

# REFERENCE
See ../../docs/styleguide/08-etl-architecture.md
