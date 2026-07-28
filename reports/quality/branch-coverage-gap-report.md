# Branch Coverage Gap Report

Generated: 2026-07-06

Source: `reports/coverage/coverage.xml` (`9a58b23b7c9cc7bb4c2ce0753dbd8999782d201d6cd1e0fd44214833bcdf3791`)

## Summary

- Line coverage: `95.88%` (87633/91396)
- Branch coverage: `85.002%` (17218/20256)
- 85% branch threshold requires: `17218` covered branch outcomes
- Branch threshold margin: `0` outcomes
- Files below 85% branch coverage: `552`
- Promotion status: `promoted_to_blocking_gate`

## Theme Summary

| Theme | Files below 85% | Missing branches |
| --- | ---: | ---: |
| `application_control_plane` | 46 | 247 |
| `composition_runtime` | 102 | 355 |
| `domain` | 91 | 364 |
| `infrastructure` | 172 | 785 |
| `other` | 141 | 648 |

## Top Branch Gaps

| Missing | Branch rate | Branches | Path | Lines sample |
| ---: | ---: | ---: | --- | --- |
| 22 | 68.57% | 48/70 | `src/bioetl/application/composite/_coalesce_policy_support.py` | 25, 35, 43, 121, 143, 165, 195, 222, 234, 236, 238, 240 |
| 22 | 54.17% | 26/48 | `src/bioetl/application/services/_observability_trace_support.py` | 36, 51, 58, 80, 89, 93, 115, 141, 144, 146, 148, 161 |
| 18 | 75.0% | 54/72 | `src/bioetl/interfaces/http/_processed_records_table_support.py` | 167, 179, 194, 242, 262, 264, 276, 278, 282, 284, 340, 347 |
| 18 | 60.87% | 28/46 | `src/bioetl/application/services/_observability_workflow_checkpoint_support.py` | 57, 198, 226, 242, 245, 270, 272, 274, 298, 309, 367, 371 |
| 15 | 79.17% | 57/72 | `src/bioetl/infrastructure/quality/architecture_debt_reduction.py` | 77, 94, 108, 112, 133, 139, 141, 143, 161, 171, 197, 291 |
| 15 | 71.15% | 37/52 | `src/bioetl/infrastructure/control_plane/artifact_byte_comparison.py` | 66, 82, 93, 94, 97, 224, 231, 257, 267, 279, 292 |
| 14 | 79.41% | 54/68 | `src/bioetl/infrastructure/adapters/chembl/protein_classification_graph.py` | 134, 177, 188, 190, 203, 210, 212, 218, 221, 232, 247, 249 |
| 14 | 73.08% | 38/52 | `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py` | 51, 58, 66, 74, 76, 78, 80, 190, 222, 312, 329, 356 |
| 14 | 65.0% | 26/40 | `src/bioetl/composition/factories/pipeline/registry_validation.py` | 26, 83, 101, 107, 111, 115, 151, 156, 162, 164, 189, 191 |
| 14 | 58.82% | 20/34 | `src/bioetl/interfaces/cli/commands/checkpoint.py` | 69, 106, 153, 160, 170, 191, 220, 223, 240, 251, 253, 260 |
| 13 | 80.3% | 53/66 | `src/bioetl/interfaces/cli/commands/_run_manifest_output.py` | 36, 38, 40, 86, 136, 144, 149, 243, 255, 265, 274, 284 |
| 13 | 75.93% | 41/54 | `src/bioetl/infrastructure/config/pipeline_normalizers.py` | 40, 42, 89, 94, 106, 108, 113, 122, 124, 129, 146, 165 |
| 13 | 74.0% | 37/50 | `src/bioetl/application/pipelines/chembl/target_protein_classification_summary.py` | 57, 59, 65, 152, 154, 165, 178, 196, 272, 273, 276, 278 |
| 13 | 71.74% | 33/46 | `src/bioetl/domain/normalization/rules.py` | 142, 145, 147, 156, 158, 161, 170, 176, 183, 224, 243, 270 |
| 13 | 67.5% | 27/40 | `src/bioetl/interfaces/cli/commands/lineage.py` | 67, 69, 84, 99, 123, 129, 155, 161, 167, 173, 179, 188 |
| 13 | 65.79% | 25/38 | `src/bioetl/domain/normalization/profiles/_profile_value_normalizers.py` | 33, 82, 91, 97, 100, 142, 156, 164, 171, 186, 189, 202 |
| 13 | 59.38% | 19/32 | `src/bioetl/interfaces/cli/commands/domains/maintenance/plan.py` | 34, 36, 39, 43, 51, 53, 59, 61, 64, 68, 79, 81 |
| 12 | 82.35% | 56/68 | `src/bioetl/application/composite/_preflight_orchestration.py` | 27, 46, 60, 81, 91, 115, 123, 125, 170, 253, 322 |
| 12 | 80.65% | 50/62 | `src/bioetl/infrastructure/control_plane/file_artifact_lifecycle_reasons.py` | 60, 87, 89, 109, 122, 126, 134, 138, 154, 158, 162, 177 |
| 12 | 70.0% | 28/40 | `src/bioetl/interfaces/cli/commands/_workflow_run_support.py` | 77, 83, 89, 95, 206, 209, 217, 220, 222, 246, 272 |
| 12 | 60.0% | 18/30 | `src/bioetl/interfaces/cli/commands/domains/diagnostics/rendering.py` | 80, 84, 147, 196, 201, 210, 222, 241, 251, 270, 284 |
| 12 | 57.14% | 16/28 | `src/bioetl/application/services/control_plane/replay/_historical_certification_support.py` | 82, 89, 96, 102, 113, 118, 144, 147, 234, 245, 258, 272 |
| 12 | 45.45% | 10/22 | `src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py` | 196, 198, 234, 276, 316, 328, 400, 402, 411, 414 |
| 12 | 0.0% | 0/12 | `src/bioetl/interfaces/http/health_server.py` | 113, 122, 127, 136, 145, 156 |
| 12 | 0.0% | 0/12 | `src/bioetl/infrastructure/quarantine/filtered_reads.py` | 55, 67, 70, 155, 174, 192 |
| 11 | 85.53% | 65/76 | `src/bioetl/application/services/control_plane/manifest/diagnostics/replay_state.py` | 92, 94, 110, 126, 130, 134, 156, 160, 165, 181, 185 |
| 11 | 77.08% | 37/48 | `src/bioetl/infrastructure/adapters/pubmed/_filter_fetch_support.py` | 23, 34, 40, 48, 58, 60, 67, 74, 81, 186 |
| 11 | 76.09% | 35/46 | `src/bioetl/composition/services/effective_config_serializer.py` | 34, 37, 173, 175, 177, 208, 212, 262, 270, 272 |
| 11 | 71.05% | 27/38 | `src/bioetl/composition/runtime_builders/ledger_collaborator.py` | 53, 87, 90, 93, 122, 138, 147, 150, 160, 192, 205 |
| 11 | 71.05% | 27/38 | `src/bioetl/application/services/_observability_workflow_evidence_support.py` | 44, 47, 55, 57, 60, 68, 76, 78, 80, 116 |

## Promotion Note

The repo is at the 85% branch threshold with zero branch-outcome margin. The branch gate is promoted through `python -m scripts.engineering.qa check-branch-coverage --coverage-xml reports/coverage/coverage.xml --min-percent 85` in the canonical `coverage-verify` lane; follow-up branch-tail work should build margin above the threshold.
