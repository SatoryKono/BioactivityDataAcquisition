> Scope:
> - USE WHEN implementing runs; outputs must be idempotent and deterministic
> - Use when editing files matching: `src/bioetl/pipelines/**/*.py`, `tests/**/*.py`
# MANDATORY
- Re-running with the same inputs produces byte-identical outputs.
- Ensure canonical sort order and stable identifiers; write outputs atomically (no duplicates on re-run).

# REFERENCE
See ../../docs/styleguide/08-etl-architecture.md
