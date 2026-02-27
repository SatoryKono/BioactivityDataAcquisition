# Migration guide: 5.14.x → 6.0.0

## Composite config contract hardening

BioETL 6.0.0 restores strict composite config contract validation:

- `composite.version` is required by the canonical Pydantic model.
- `configs/-schema/composite.json` is generated from the same model and now marks `version` as required.

### What changed

Old (legacy) configs that omit `composite.version` are no longer part of the primary contract.

During a transition window, runtime still accepts them via an explicit compatibility path and emits a `DeprecationWarning`.

### Required action

Update every composite YAML:

```yaml
composite:
  name: composite-publication
  version: "1.1.0"  # required in v6+
```

## Deprecation window

- Compatibility mode for missing `composite.version`: **available in 6.0.x and 6.1.x**.
- Planned removal: **6.2.0**.

After removal, configs without `composite.version` will fail validation.
