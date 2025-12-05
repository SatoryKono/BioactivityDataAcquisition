> Scope:
> - USE WHEN secrets are required; fail fast if missing/invalid with actionable error
> - Use when editing files matching: `src/**/*.py`, `src/**/config*.py`
# MANDATORY
- If a required secret is missing or invalid, stop at startup with a clear error; do not proceed with dummy defaults.

# REFERENCE
See ../../docs/styleguide/09-secrets-config.md
