# Reconciliation Note: 2026-05-14 Normalization Audit Claims vs Current Repo Evidence

Дата: `2026-05-14`
Режим: artifact-backed reconciliation against current `main`

## Scope

Этот note фиксирует, какие claims из внешнего normalization audit summary от `2026-05-14 12:40:30 DA`
подтверждаются текущими артефактами репозитория, а какие не должны порождать backlog без
дополнительного доказательства.

Проверенные evidence surfaces:

- composite publication configs: [configs/composites/publication.yaml](../../../configs/composites/publication.yaml),
  [configs/composites/field_groups/publication.yaml](../../../configs/composites/field_groups/publication.yaml)
- publication field-group mapping:
  [src/bioetl/domain/value_objects/_publication_field_groups_data.py](../../../src/bioetl/domain/value_objects/_publication_field_groups_data.py)
- DQ contract configs and loader:
  [configs/contracts](../../../configs/contracts),
  [src/bioetl/infrastructure/config/dq_contract_config_loader.py](../../../src/bioetl/infrastructure/config/dq_contract_config_loader.py)
- Gold strict-validation runtime seam:
  [src/bioetl/infrastructure/storage/gold/io_mixin.py](../../../src/bioetl/infrastructure/storage/gold/io_mixin.py),
  [tests/integration/config/test_pipeline_data_storage_contracts.py](../../../tests/integration/config/test_pipeline_data_storage_contracts.py)
- publication PK nullability evidence:
  [tests/contract/test_publication_schema_contracts.py](../../../tests/contract/test_publication_schema_contracts.py)
- non-ChEMBL normalization audit artifacts:
  [non-chembl-normalization-audit-2026-05-12.md](./non-chembl-normalization-audit-2026-05-12.md)

## Confirmed at Audit Time, Now Reconciled

### 1. Composite publication canonical identifier drift

Факт:

- publication composite раньше одновременно держал canonical `publication_id` и legacy
  `document_chembl_id` в publication field-group/config surfaces.

Evidence:

- historical config surfaces before this change were the basis for
  [#4083](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4083)

Resolution in current repo state:

- composite publication now retains `publication_id` as canonical ChemBL publication identifier
  and no longer exposes `document_chembl_id` in composite provider-id ordering or publication
  field-group mapping.

### 2. Contract `strict_validation` wording ambiguity

Факт:

- contract configs used `strict_validation`, while Gold runtime semantics already used a separate
  strict Gold validation path.

Evidence:

- contract config loader maps contract payload into `DQConfig.strict_validation`:
  [src/bioetl/infrastructure/config/dq_contract_config_loader.py](../../../src/bioetl/infrastructure/config/dq_contract_config_loader.py)
- Gold strict runtime seam is independently asserted in:
  [tests/integration/config/test_pipeline_data_storage_contracts.py](../../../tests/integration/config/test_pipeline_data_storage_contracts.py)

Resolution in current repo state:

- contract configs now use canonical `strict_dq_validation`;
- loader keeps legacy `strict_validation` as backward-compat alias only;
- DQ domain docs explicitly distinguish DQ strictness from Gold/runtime strict validation.

## Claims Not Confirmed by Current Repo Evidence

### 1. “Part of Gold fields lacks full Pandera validation / no not_null for IDs”

Not confirmed.

Artifact-backed counter-evidence:

- publication primary keys are explicitly tested as non-nullable in
  [tests/contract/test_publication_schema_contracts.py](../../../tests/contract/test_publication_schema_contracts.py).

Decision:

- no backlog item should be created from this claim without a failing schema- or contract-level
  artifact.

### 2. “Quarantine policies are inconsistent across pipelines”

Not confirmed for current contract layer.

Artifact-backed counter-evidence:

- active contract configs consistently declare `invalid_record_policy: "quarantine"` across current
  shipped `configs/contracts/**`.

Decision:

- treat this claim as stale unless a pipeline-specific effective-policy diff demonstrates drift.

### 3. “JSON handling is inconsistent versus ADR-035” as a general repo-wide conclusion

Only partially supported, not established as a broad current-state failure.

Artifact-backed context:

- ADR-035 exists and current non-ChEMBL publication/uniprot surfaces already use explicit
  structured payload governance and raw/canonical sidecars in the shipped audit baseline:
  [non-chembl-normalization-audit-2026-05-12.md](./non-chembl-normalization-audit-2026-05-12.md)

Decision:

- broad JSON-typing drift should not be backlogged from the external summary alone;
- only field-specific, artifact-backed JSON mismatches should become issues.

### 4. “non-ChEMBL audit” findings built from ChEMBL-only semantic clusters

Not admissible as non-ChEMBL evidence.

Artifact-backed constraint:

- current non-ChEMBL scope is explicitly limited to the seven registered non-ChEMBL entity pipelines
  plus composite impact surfaces, as documented in
  [non-chembl-normalization-audit-2026-05-12.md](./non-chembl-normalization-audit-2026-05-12.md).

Decision:

- ChEMBL-only cluster evidence must not be reused as proof of non-ChEMBL normalization drift.

## Outcome

- `#4083`: resolved by removing composite publication `document_chembl_id` drift.
- `#4084`: resolved by separating `strict_dq_validation` from Gold/runtime strict validation.
- `#4085`: closed by this reconciliation note; the remaining external-audit claims are either
  disproven by current repo artifacts or require narrower, field-specific evidence before entering
  backlog.
