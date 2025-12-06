> Scope:
> - USE WHEN shaping output datasets; prefer star schema (dims + fact)
> - Use when editing files matching: `src/**`, `docs/pipelines/**/*.md`
# SHOULD
- Model data as a star schema: dimension tables (documents, targets, assays, testitems) and a fact table (activity) with foreign keys.

# BAD
One denormalized table duplicating dimension attributes on every row.

# GOOD
Separate dims (`assays_dim.csv`, `targets_dim.csv`, `documents_dim.csv`) and a fact (`activity_fact.csv`).

# REFERENCE
See ../../docs/styleguide/08-etl-architecture.md
