> Scope:
> - USE WHEN handling secrets or configuration; env/secret manager only; typed Pydantic configs; profiles; validation
> - Use when editing files matching: `.env*`, `configs/**/*.yaml`, `src/**/config*.py`, `src/**/*.py`
# SECRETS
- Never hardcode or log secrets; load from env or secret manager; support rotation; CI scans for leaks.

# CONFIG
- Typed models via Pydantic; validate on load; profile inheritance for shared defaults.
- Precedence: env > CLI overrides > pipeline config > profiles.

# FAIL FAST
- If required secret/config missing or invalid, stop execution with actionable error.

# REFERENCE
See [docs/styleguide/09-secrets-config.md](../../docs/styleguide/09-secrets-config.md) for detailed documentation.
