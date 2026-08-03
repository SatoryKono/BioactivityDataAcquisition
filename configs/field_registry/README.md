# Semantic Governance Authority

This directory is the maintainer entrypoint for field-level semantic authority.
Generated audit reports are evidence snapshots; they do not define semantic
ownership.

## Authority surfaces

- `canonical_registry.json` defines reviewed exact aliases and canonical field
  identity.
- `semantic_governance_authority_registry.yaml` indexes every semantic
  authority surface and its generated outputs.
- `assay_metadata_semantic_registry.yaml` owns source, composite, and lineage
  roles for assay metadata that intentionally remains non-canonical.
- `partial_identifier_owner_roles.yaml` owns the provider, composite, and
  lineage role split for reviewed `PARTIAL` identifier clusters.
- `composite_schema_authority_registry.yaml` publishes explicit Gold typing
  authority for inherited composite fields.
- `semantic_audit_review_registry.yaml` contains residual review workflow,
  promotion requirements, expiry, and risk caps. Dedicated authority data is
  projected into this review inventory and parity is enforced by
  `check-semantic-governance-policy`.
- `semantic_pair_matrix_budget.yaml` is the ratchet for permitted residual
  counts. Its budgets must never be increased to make a check pass.

## Base contract ownership

`configs/base/contract_registry.yaml` remains the runtime registry, but its
semantic ownership is segmented by responsibility:

- contract identity and version resolution: `contract_registry.yaml`;
- pipeline and Medallion defaults: `pipeline.yaml`;
- shared DQ policy defaults: `quality.yaml`;
- field-level alias, owner-role, and schema authority: the dedicated registries
  listed above.

The `base_semantic_governance_contracts` entry in
`semantic_governance_authority_registry.yaml` binds these base surfaces to the
generated base-config coverage artifact.

## Generated evidence and reviewed states

`reports/semantic_pipeline_audit/` contains reproducible pair matrices, cluster
registries, residual backlogs, and manifests. Regenerate them through
`python -m scripts.engineering.qa report-semantic-pipeline-audit`.

`PARTIAL` and `WEAK` are reviewed governance states, not runtime conflicts:

- `PARTIAL` means related fields have distinct owner/composite/lineage roles;
- `WEAK` means lexical similarity exists without proven canonical identity.

Promotion requires the evidence defined in
`semantic_audit_review_registry.yaml`; lexical similarity alone is never
sufficient.

## Required checks

```bash
python -m scripts.engineering.qa report-semantic-pipeline-audit --check
python -m scripts.engineering.qa check-semantic-governance-policy --check --json
pytest tests/integration/config/test_semantic_governance_policy.py \
  tests/integration/config/test_semantic_pair_matrix_budget.py \
  tests/integration/config/test_semantic_registry_drift.py
```
