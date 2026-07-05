______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-03-30'

______________________________________________________________________

# Schema Evolution Guide

## Trigger

- Run this procedure when schema changes affect ingestion, storage, or downstream contract compatibility.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Scenario 1: Adding a New Field (Backward Compatible)

1. **Update Pydantic Model**:

- Add the new field to the entity model in `src/bioetl/domain/entities/`.
  ```python
  class MyEntity(BaseEntity):
      ...
      new_field: str | None = None  # Must be optional initially
  ```

2. **Update Pandera Schema**:

- Add the field to `src/bioetl/infrastructure/schemas/`.
  ```python
  class MySchema(pa.DataFrameModel):
      ...
      new_field: Series[str] = pa.Field(nullable=True)
  ```

3. **Deploy**:

- Deploy the changes. Delta Lake will automatically handle the schema evolution (mergeSchema).

### Scenario 2: Breaking Change (Rename/Type Change)

1. **Create Migration Plan**:

   - **Option A**: Full Rebuild (Simplest). Delete table and reload.
   - **Option B**: Dual Write (Zero Downtime). See [RULES.md Appendix E.3](../../00-project/RULES.md#e3-field-deprecation-workflow).

1. **Implement Dual Write (If needed)**:

   - Add `new-field`.
   - Populate `new-field` from `old-field` or source.
   - Keep `old-field` for compatibility.

1. **Deprecate Old Field**:

   - Mark `old-field` as deprecated in documentation/schema.
   - Notify consumers.

1. **Remove Old Field**:

   - After deprecation period, remove `old-field`.
   - Run `VACUUM` to clean up old versions.

### Handling Schema Drift Alerts

- **Warning**: "New fields detected: [...]".
  - Review the fields.
  - If useful, add to explicit schema.
  - If garbage, ignore (Silver will store them, Gold might drop them depending on `strict` mode).
- **Critical**: "Missing required field: [...]".
  - **Immediate Action**: Fix the parser or contact provider. Pipeline is broken.

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
