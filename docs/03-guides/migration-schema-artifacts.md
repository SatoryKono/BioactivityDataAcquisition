# Migration Guide: Canonical Schema Generation

## Scope

This guide describes migration to the canonical schema generation flow introduced in ADR-036.

## What Changed

- Canonical source is now defined as:
  - `configs/schemas/{provider}/{entity}.yaml` (field grouping and shape)
  - typed annotations in Silver Pandera schema classes (field typing)
- Generated artifacts are managed via a single command:

```bash
uv run python scripts/generate_schema_artifacts.py
```

- CI now blocks pull requests when generated artifacts are stale:

```bash
uv run python scripts/generate_schema_artifacts.py --check
```

## Required Developer Workflow

1. Update `configs/schemas/{provider}/{entity}.yaml` and/or Silver Pandera schema classes.

1. Regenerate artifacts locally:

   ```bash
   uv run python scripts/generate_schema_artifacts.py
   ```

1. Commit all generated changes:

   - `src/bioetl/domain/schemas/generated/registry.py`
   - `docs/04-reference/contracts/gold/*.json`
   - `docs/05-operations/verification/gold-contracts-export-diff-2026-02-17.json`

1. Run check mode before push:

   ```bash
   uv run python scripts/generate_schema_artifacts.py --check
   ```

## Notes

- Gold JSON contracts continue to be exported from `src/bioetl/domain/contracts/gold/*GoldSchema` classes.
- `--check` mode is the canonical CI guard for generated schema artifacts.
