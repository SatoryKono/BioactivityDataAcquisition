# CLI Index

This index lists maintenance entrypoints for documentation and configuration checks.

## Validation utilities

- `python scripts/check_docs_alignment.py` — verify that ABC/Impl registries match `docs/01-ABC/INDEX.md` and that ChEMBL schema column orders documented in `docs/schemas/01-chembl-schema-columns.md` stay in sync with code.
- `npm run lint -- docs` — run markdown linting for documentation updates.

## Configuration guides

- [03-config-precedence-and-profiles.md](03-config-precedence-and-profiles.md) — precedence rules for configuration sources and profile handling.
