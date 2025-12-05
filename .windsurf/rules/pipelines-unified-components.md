> Scope:
> - USE WHEN wiring cross-cutting concerns; use unified Logger, OutputWriter, APIClient, Schema
> - Use when editing files matching: `src/bioetl/**/*.py`
# MANDATORY
- Use provided unified components: `UnifiedLogger`, `UnifiedOutputWriter`, `UnifiedAPIClient`, and schema classes.

# BAD
Using `print()` or ad-hoc file I/O in pipelines.

# GOOD
Delegate logging and output to the unified components.

# REFERENCE
See ../../docs/styleguide/08-etl-architecture.md
