# ChEMBL Pipelines Refactoring Plan

## 1. Goals

- Align all ChEMBL pipelines (`activity`, `assay`, `document`, `target`, `testitem`, `molecule`) with:
  - `PipelineConfig` contracts (`quality.*`, `extra="forbid"`).
  - Pandera schema & `SchemaRegistry` contracts.
  - Project rules in `docs/project/01-project-rules.md` and `00-rules-summary.md`.
  - The pipeline review checklist `docs/templates/pipeline-review-checklist.md`.

---

## 2. Current Issues (Summary)

1. **YAML quality section mismatch**
   - `assay.yaml`, `molecule.yaml`, `target.yaml`, `testitem.yaml` use legacy top-level `hashing`/`normalization` instead of `quality.hashing` / `quality.normalization`.
   - This conflicts with `PipelineConfig` (`quality: QualityConfig`, `extra="forbid"`), so these fields may be ignored or rejected.

2. **Duplicate `pipeline` section in `activity.yaml`**
   - Two `pipeline:` sections, second one overwrites the first (metadata lost at parse time).

3. **Missing per-entity tests for `assay_chembl` and `molecule_chembl`**
   - No `tests/bioetl/application/pipelines/chembl/assay/` or `/molecule/` directories.
   - Existing tests cover shared base, extraction, PK-resolution, and some pipelines, but not assay/molecule-specific behaviour.

4. **Confusing alias comment in registry**
   - In `src/bioetl/application/pipelines/registry.py`, `"molecule_chembl"` is commented as `# Alias for testitem`, while in fact it is a separate pipeline with its own schema and config.

---

## 3. Phase 1 – YAML Config Migration

### 3.1. Preparation

- Verify that there is no implicit migration layer that maps legacy top-level `hashing`/`normalization` to `quality.*`.
- Snapshot the current ChEMBL configs for easy diff/rollback:
  - `configs/pipelines/chembl/assay.yaml`
  - `configs/pipelines/chembl/molecule.yaml`
  - `configs/pipelines/chembl/target.yaml`
  - `configs/pipelines/chembl/testitem.yaml`
  - `configs/pipelines/chembl/activity.yaml`

### 3.2. Move `hashing` and `normalization` under `quality`

For each of:

- `configs/pipelines/chembl/assay.yaml`
- `configs/pipelines/chembl/molecule.yaml`
- `configs/pipelines/chembl/target.yaml`
- `configs/pipelines/chembl/testitem.yaml`

Steps:

1. **Wrap existing sections under `quality`**

   Example transformation:

   ```yaml
   hashing:
     business_key_fields:
       - assay_chembl_id
       - document_chembl_id
       - target_chembl_id

   normalization:
     id_fields:
       - assay_type
   ```

   becomes:

   ```yaml
   quality:
     hashing:
       business_key_fields:
         - assay_chembl_id
         - document_chembl_id
         - target_chembl_id
     normalization:
       id_fields:
         - assay_type
   ```

2. **Sanity-check field names**
   - Ensure that `business_key_fields` and `normalization` field lists only reference actual columns in the corresponding Pandera schema.
   - Remove obviously obsolete or unused keys if any are discovered.

3. **Validate configs**

   ```bash
   bioetl validate-config --config configs/pipelines/chembl/<entity>.yaml
   ```

   - All ChEMBL configs should pass without `extra`/unknown field errors.

### 3.3. Merge duplicate `pipeline` in `activity.yaml`

File: `configs/pipelines/chembl/activity.yaml`.

1. **Combine both `pipeline:` sections into one**

   ```yaml
   pipeline:
     name: activity_chembl
     version: "1.0.0"
     owner: "Data Acquisition Team"
     description: "Extract biological activity records from ChEMBL API"
     enable_denormalization: false
   ```

2. **Re-run config validation**

   ```bash
   bioetl validate-config --config configs/pipelines/chembl/activity.yaml
   ```

---

## 4. Phase 2 – Tests for `assay_chembl` and `molecule_chembl`

### 4.1. Test structure

Create:

- `tests/bioetl/application/pipelines/chembl/assay/test_assay_pipeline.py`
- `tests/bioetl/application/pipelines/chembl/molecule/test_molecule_pipeline.py`

Mirror existing patterns from:

- `activity/test_activity_pipeline.py`
- `document/test_document_pipeline.py`
- `target/test_target_pipeline.py`
- `testitem/test_testitem_pipeline.py`

### 4.2. Minimal test cases per entity

For each of `assay` and `molecule`:

1. **Smoke instantiation test**

   - Instantiate `ChemblPipelineBase` with a `MagicMock`/`PipelineConfig` where:
     - `entity_name = "<entity>"`;
     - `provider = "chembl"`;
     - `primary_key` set to the expected PK (`assay_chembl_id` / `molecule_chembl_id`).
   - Assert `pipeline.ID_COLUMN` and `pipeline.API_FILTER_KEY` are correct.

2. **Transform + validate happy path**

   - Build a small `DataFrame` with the minimal set of columns required by the schema (`AssaySchema` / `MoleculeSchema`).
   - Use either:
     - real schema via `ValidationService`, or
     - a simplified `MockSchema` as in `test_activity_pipeline.py`.
   - Call `pipeline.transform(df)` and assert:
     - DataFrame is non-empty;
     - required columns are present;
     - resulting column order matches `ASSAY_OUTPUT_COLUMNS` / `MOLECULE_OUTPUT_COLUMNS`.

3. **(Optional) Golden tests**

   - For each entity, prepare fixed small input data and expected output artifacts:
     - `<entity>_output.csv`, `meta.yaml`.
   - Write a golden test that runs the pipeline (via Python API or CLI in `--dry-run`/`--limit` mode) and compares the outputs byte-for-byte.

### 4.3. Determinism checks

- Add at least one test that:
  - runs transform+export twice with the same input, and
  - asserts identical row order, column order, and hash columns.

---

## 5. Phase 3 – Registry Comment and Documentation

### 5.1. Update confusing alias comment

File: `src/bioetl/application/pipelines/registry.py`.

- Current:

  ```python
  "molecule_chembl": ChemblPipelineBase,  # Alias for testitem
  ```

- Proposed:

  ```python
  "molecule_chembl": ChemblPipelineBase,  # Separate pipeline for /molecule endpoint
  ```

or simply remove the comment.

### 5.2. Ensure docs reflect actual semantics

- Verify that overview docs for `molecule` and `testitem` do not claim they are the same pipeline.
- If necessary, clarify in docs that both use the `/molecule` endpoint but differ in schema and output shape.

---

## 6. Phase 4 – Regression & Rules Alignment

### 6.1. Config validation

After all YAML changes:

```bash
bioetl validate-config --config configs/pipelines/chembl/activity.yaml
bioetl validate-config --config configs/pipelines/chembl/assay.yaml
bioetl validate-config --config configs/pipelines/chembl/document.yaml
bioetl validate-config --config configs/pipelines/chembl/target.yaml
bioetl validate-config --config configs/pipelines/chembl/testitem.yaml
bioetl validate-config --config configs/pipelines/chembl/molecule.yaml
```

### 6.2. Test suite

Run at least:

```bash
pytest tests/bioetl/application/pipelines/chembl -q
```

Ensure:

- New tests for `assay` and `molecule` run and pass.
- Legacy tests (`test_extraction.py`, `test_base.py`, `test_pipelines_smoke.py`, `test_pk_resolution.py`) remain green.

### 6.3. Optional smoke CLI runs

- For one or two pipelines (e.g. `activity_chembl`, `molecule_chembl`), run:

  ```bash
  bioetl run --pipeline-name <entity>_chembl \
    --config configs/pipelines/chembl/<entity>.yaml \
    --profile dev --dry-run --limit 50
  ```

- Check that run finishes without errors, logs look reasonable, and no breaking schema mismatches occur.

### 6.4. Project rules alignment

- Revisit `docs/project/01-project-rules.md` / `00-rules-summary.md` to confirm:
  - they already state that quality settings live under `quality.*`;
  - they enforce the need for Pandera schemas and deterministic output.
- Adjust wording only if new conventions were introduced during refactoring.
