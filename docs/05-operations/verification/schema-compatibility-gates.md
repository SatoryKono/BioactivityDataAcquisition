# Schema Compatibility Gates

## CI Blocking Policy

The schema compatibility check is enforced by CI via:

```bash
uv run python src/tools/verify_schema_parity.py
```

The step regenerates expected Gold contracts into a temporary directory and diffs them against committed files in `docs/04-reference/contracts/gold/`.

### Blocking (PR must fail)

- **Parity diff** between generated and committed Gold JSON contracts.
- **PK coverage break** in schema compatibility review.
- **Nullable break** (tightening nullable → non-nullable without major bump).

### Warning (PR may proceed with review)

- **Additive non-breaking nullable fields**.

## Changelog Classification Template

Use this template in PR notes/release notes for schema changes:

- **MAJOR**: remove/rename fields, type tightening, non-null tightening.
- **MINOR**: additive nullable fields.
- **PATCH**: descriptions/examples/docs-only updates.
