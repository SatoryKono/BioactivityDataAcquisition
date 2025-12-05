> Scope:
> - USE WHEN merging configuration; precedence is env > CLI > config files > profiles
> - Use when editing files matching: `src/**/config*.py`, `src/**/*.py`
# Config precedence

## Mandatory

- Apply configuration in this order: environment overrides > CLI > config files > profile defaults.

## Reference

See [docs/styleguide/09-secrets-config.md](../../docs/styleguide/09-secrets-config.md)
