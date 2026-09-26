# Invariant Audit Rebaseline: June 2026

Review date: `2026-06-19`
Repository: `SatoryKono/BioactivityDataAcquisition`
Tracker issues: #5461, #5462, #5463

## Summary

- Total findings: `17`
- Needs follow-up: `0`
- Missing cited paths rebaselined: `13`
- Classification counts: `{'duplicate-existing-issue': 2, 'implemented': 15}`
- Severity counts: `{'CRITICAL': 3, 'HIGH': 4, 'LOW': 3, 'MEDIUM': 7}`

## Matrix

| ID | Severity | Theme | Classification | Current anchors | Issues |
| --- | --- | --- | --- | --- | --- |
| F01 | CRITICAL | Batch FSM lifecycle | `implemented` | `src/bioetl/application/core/lifecycle/batch_fsm.py`<br>`src/bioetl/domain/aggregates/_batch_lifecycle.py`<br>`tests/unit/application/core/test_batch_fsm.py` | #5444, #5451 |
| F02 | CRITICAL | PipelineRun completion invariant | `implemented` | `src/bioetl/domain/aggregates/pipeline_run.py`<br>`src/bioetl/domain/aggregates/_pipeline_run_mixins.py`<br>`tests/unit/domain/aggregates/test_pipeline_run.py`<br>`tests/unit/domain/aggregates/test_pipeline_run_invariant_properties.py` | #5443, #5451 |
| F03 | CRITICAL | Sanctioned HTTP client usage | `implemented` | `src/bioetl/infrastructure/adapters/http/client.py`<br>`tests/architecture/test_adapter_http_client_enforcement.py`<br>`tests/unit/infrastructure/adapters/http/test_http_client.py` | #5417, #5447, #5451 |
| F04 | HIGH | Quarantine payload immutability | `implemented` | `src/bioetl/domain/aggregates/quarantine_entry.py`<br>`src/bioetl/domain/aggregates/_quarantine_value_objects.py`<br>`src/bioetl/domain/ports/quality/quarantine.py`<br>`tests/architecture/test_quarantine_immutability.py`<br>`tests/unit/domain/aggregates/test_quarantine_entry.py` | #5420, #5445, #5451 |
| F05 | HIGH | META_FIELDS content-hash exclusion | `implemented` | `src/bioetl/domain/constants.py`<br>`src/bioetl/domain/transformations/hashing.py`<br>`tests/unit/contracts/test_content_hash_contract.py`<br>`tests/contract/test_content_hash_schema_drift_contract.py` | #5447, #5451 |
| F06 | HIGH | Observability canonical labels and run identity | `implemented` | `src/bioetl/domain/_observability_contract_core.py`<br>`src/bioetl/domain/observability_contract.py`<br>`tests/unit/domain/test_observability_contract.py`<br>`tests/architecture/test_observability_signal_governance.py`<br>`tests/architecture/test_observability_metric_governance.py` | #5446, #5451 |
| F07 | HIGH | Gold strict validation | `implemented` | `src/bioetl/infrastructure/storage/gold/validation_mixin.py`<br>`src/bioetl/domain/contracts/gold/_strict_gold_contract_schema.py`<br>`tests/architecture/test_gold_strict_validation_policy.py`<br>`tests/contract/test_gold_schema_strict_violations.py`<br>`tests/unit/storage/gold/test_strict_validation.py` | #5448, #5451 |
| F08 | MEDIUM | Retry determinism | `implemented` | `src/bioetl/domain/resilience.py`<br>`src/bioetl/infrastructure/adapters/http/client_retry_mixin.py`<br>`tests/unit/infrastructure/adapters/http/test_retry_config.py`<br>`tests/unit/infrastructure/adapters/http/test_client_retry_mixin.py` | #5447, #5451 |
| F09 | MEDIUM | Checkpoint resume anchors | `implemented` | `src/bioetl/application/services/checkpoint_compatibility_service.py`<br>`src/bioetl/application/services/control_plane/manifest/diagnostics/resume_contract.py`<br>`src/bioetl/application/composite/checkpoint/_anchor_context.py`<br>`tests/integration/ci/test_reproducibility_contract_manifest_diff.py`<br>`tests/unit/application/composite/checkpoint/test_checkpoint_service.py` | #5449, #5451 |
| F10 | MEDIUM | Business logic placement in infrastructure | `duplicate-existing-issue` | `src/bioetl/infrastructure/adapters/chembl/`<br>`src/bioetl/infrastructure/adapters/pubchem/`<br>`tests/architecture/test_strict_architecture_contracts.py`<br>`tests/architecture/test_adapter_contracts.py` | #5450, #5451 |
| F11 | MEDIUM | Composite merge determinism | `implemented` | `src/bioetl/domain/composite/`<br>`src/bioetl/application/composite/merger.py`<br>`tests/contract/test_composite_merge_golden.py`<br>`tests/unit/application/composite/test_merger.py`<br>`tests/unit/application/composite/test_composite_merge_conflicts.py` | #5449, #5451 |
| F12 | MEDIUM | Schema drift detection | `implemented` | `src/bioetl/domain/transformations/drift.py`<br>`src/bioetl/infrastructure/storage/silver/schema_drift_operations.py`<br>`tests/e2e/test_pipeline_with_schema_drift_e2e.py`<br>`tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py`<br>`tests/contract/test_content_hash_schema_drift_contract.py` | #5448, #5451 |
| F13 | MEDIUM | Infrastructure imports application | `implemented` | `src/bioetl/infrastructure/`<br>`tests/architecture/test_strict_architecture_contracts.py` | #5450, #5451 |
| F14 | MEDIUM | Critical-path integration coverage | `duplicate-existing-issue` | `tests/integration/`<br>`tests/integration/ci/test_reproducibility_contract_manifest_diff.py`<br>`tests/integration/composite/test_composite_cross_validation.py`<br>`tests/integration/infrastructure/storage/test_gold_writer_versioning.py` | #5450, #5451 |
| F15 | LOW | Governance audit trail | `implemented` | `src/bioetl/domain/control_plane/run_ledger.py`<br>`src/bioetl/domain/control_plane/workflow_ledger.py`<br>`src/bioetl/infrastructure/control_plane/file_run_ledger_store.py`<br>`tests/unit/application/services/test_run_ledger_service.py`<br>`tests/unit/application/core/test_runner.py`<br>`tests/unit/application/composite/test_runner.py` | #5450, #5451 |
| F16 | LOW | Dead abstractions | `implemented` | `reports/quality/dead-code-inventory.json`<br>`reports/quality/port-adapter-factory-coverage.json`<br>`tests/architecture/test_port_contracts.py`<br>`tests/architecture/test_retirement_candidate_triage.py`<br>`tests/architecture/test_source_test_facade_ownership.py` | #5450, #5451 |
| F17 | LOW | Compatibility shim lifecycle | `implemented` | `configs/quality/config_compatibility_registry.yaml`<br>`configs/quality/compatibility_facade_inventory.yaml`<br>`reports/quality/compatibility-importer-census.json`<br>`tests/architecture/test_config_transition_registry.py`<br>`tests/architecture/test_public_facade_inventory.py`<br>`tests/architecture/test_public_surface_importer_census_governance.py` | #5410, #5435, #5450, #5451 |

## Gate Interpretation

- Missing original paths do not create implementation work unless current repo evidence also reproduces the gap.
- Duplicate remediation themes must point to existing GitHub issue anchors before new issues are opened.
- `needs-follow-up` rows must be backed by current source/test anchors and a GitHub issue.
