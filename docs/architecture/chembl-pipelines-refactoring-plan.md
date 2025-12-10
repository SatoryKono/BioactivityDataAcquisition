# ChEMBL Pipelines Refactoring Plan

- Moved from repository root to keep root clean per File Policy.

<!-- Original content follows -->

## 1. Goals

- Align all ChEMBL pipelines (`activity`, `assay`, `document`, `target`, `molecule`) with:
  - `PipelineConfig` contracts (`quality.*`, `extra="forbid"`).
  - Pandera schema & `SchemaRegistry` contracts.
  - Project rules in `docs/project/01-project-rules.md` and `00-rules-summary.md`.
  - The pipeline review checklist `docs/templates/pipeline-review-checklist.md`.

---

## 2. Current Issues (Summary)

1. **YAML quality section mismatch**
   - `assay.yaml`, `molecule.yaml`, `target.yaml` use legacy top-level `hashing`/`normalization` instead of `quality.hashing` / `quality.normalization`.
   - This conflicts with `PipelineConfig` (`quality: QualityConfig`, `extra="forbid"`), so these fields may be ignored or rejected.

2. **Duplicate `pipeline` section in `activity.yaml`**
   - Two `pipeline:` sections, second one overwrites the first (metadata lost at parse time).

3. **Missing per-entity tests for `assay_chembl` and `molecule_chembl`**
   - No `tests/bioetl/application/pipelines/chembl/assay/` or `/molecule/` directories.
   - Existing tests cover shared base, extraction, PK-resolution, and some pipelines, but not assay/molecule-specific behaviour.

4. **Confusing alias comment in registry**
   - In `src/bioetl/application/pipelines/registry.py`, `"molecule_chembl"` is still commented as `# Alias for molecule`, хотя это полноценный pipeline.

---

## 3. Phase 1 – YAML Config Migration

### 3.1. Preparation

- Verify that there is no implicit migration layer that maps legacy top-level `hashing`/`normalization` to `quality.*`.
- Snapshot the current ChEMBL configs for easy diff/rollback:
  - `configs/pipelines/chembl/assay.yaml`
  - `configs/pipelines/chembl/molecule.yaml`
  - `configs/pipelines/chembl/target.yaml`
  - `configs/pipelines/chembl/activity.yaml`

### 3.2. Move `hashing` and `normalization` under `quality`

- Wrap under `quality` and validate via CLI.

### 3.3. Merge duplicate `pipeline` in `activity.yaml`

- Combine into one block and re-validate.

---

## 4. Phase 2 – Tests for `assay_chembl` and `molecule_chembl`

- Add smoke and transform+validate tests; optional golden.

---

## 5. Phase 3 – Registry Comment and Documentation

- Clarify `molecule_chembl` comment or remove.

---

## 6. Phase 4 – Regression & Rules Alignment

- Validate configs; run tests; ensure determinism.
