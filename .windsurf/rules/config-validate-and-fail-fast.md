> Scope:
> - USE WHEN loading configuration; validate schema and fail fast on errors
> - Use when editing files matching: `src/**/config*.py`, `src/**/*.py`
# MANDATORY
- Validate configuration on load; if required keys are missing or invalid, exit with a clear message before execution.

# REFERENCE
See ../../docs/styleguide/09-secrets-config.md
