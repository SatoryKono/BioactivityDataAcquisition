# Schema Evolution Guide

*Reference: [RULES.md §2.2](../../00-project/RULES.md#22-политика-дрейфа-схемы-schema-drift) and [Appendix E](../../00-project/RULES.md#приложение-e-примеры-schema-evolution)*

This runbook describes how to handle schema changes in Bronze, Silver, and Gold layers.

## Scenario 1: Adding a New Field (Backward Compatible)

1. **Update Pydantic Model**:
   Add the new field to the entity model in `src/bioetl/domain/entities/`.
   ```python
   class MyEntity(BaseEntity):
       ...
       new-field: str | None = None  # Must be optional initially
   ```

2. **Update Pandera Schema**:
   Add the field to `src/bioetl/infrastructure/schemas/`.
   ```python
   class MySchema(pa.DataFrameModel):
       ...
       new-field: Series[str] = pa.Field(nullable=True)
   ```

3. **Deploy**:
   Deploy the changes. Delta Lake will automatically handle the schema evolution (mergeSchema).

## Scenario 2: Breaking Change (Rename/Type Change)

1. **Create Migration Plan**:
   - **Option A**: Full Rebuild (Simplest). Delete table and reload.
   - **Option B**: Dual Write (Zero Downtime). See [RULES.md Appendix E.3](../../00-project/RULES.md#e3-field-deprecation-workflow).

2. **Implement Dual Write (If needed)**:
   - Add `new-field`.
   - Populate `new-field` from `old-field` or source.
   - Keep `old-field` for compatibility.

3. **Deprecate Old Field**:
   - Mark `old-field` as deprecated in documentation/schema.
   - Notify consumers.

4. **Remove Old Field**:
   - After deprecation period, remove `old-field`.
   - Run `VACUUM` to clean up old versions.

## Handling Schema Drift Alerts
- **Warning**: "New fields detected: [...]".
  - Review the fields.
  - If useful, add to explicit schema.
  - If garbage, ignore (Silver will store them, Gold might drop them depending on `strict` mode).
- **Critical**: "Missing required field: [...]".
  - **Immediate Action**: Fix the parser or contact provider. Pipeline is broken.
