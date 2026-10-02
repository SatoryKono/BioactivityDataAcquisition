# Audit #11859: source-bound coverage closeout

Date: 2026-10-02. Validation tier: local full producer; CI and live Grafana acceptance are separate.

Producer commit: `20b95b1f3b1d7e12316ad43e0614b8726f6d48b5`.
Source tree SHA-256: `2ded428f3384dd12845fdea38e6a157340f54dc4265c35d939e75514271f803b`.
Coverage XML SHA-256: `32ec2bdc964a7e3a46f529cfc48af9887b73de81e385331fad40a25198b3c76f`.

All 17 canonical groups completed with exit code 0. Each SQLite coverage hash and JUnit result was verified before the canonical nonregressing inventory refresh.
JUnit: 32188 PASS, 181 SKIP, 0 failures, 0 errors.
Line coverage: 99.71%; branch coverage: 94.35%. Both unchanged 85% gates passed.

Inventory entries: 2520 to 2541 modules; 21 absent measurements added; source path parity is exact; unmeasured = 0. All previously accepted numeric coverage percentages never decreased. The additive reporter preserves historical accepted measurements when a candidate is lower; this is not a claim that every historical row was replaced.

The originally listed twenty-second module, `_run_manifest_control_plane_refs.py`, was removed upstream in #11885 and is absent from the current source tree. It was not recreated or assigned a synthetic measurement.

## Added measurements

| Module path | Line coverage | Status |
| --- | ---: | --- |
| `src/bioetl/application/core/_batch_write_events.py` | 100.0% | `fully_covered` |
| `src/bioetl/application/core/_quarantine_entries.py` | 100.0% | `fully_covered` |
| `src/bioetl/application/core/publication_term_enrichment.py` | 89.06% | `partially_covered` |
| `src/bioetl/application/services/control_plane/ledger/_input_snapshot_manifest.py` | 86.36% | `partially_covered` |
| `src/bioetl/application/services/control_plane/manifest/input_snapshot_resolution.py` | 100.0% | `fully_covered` |
| `src/bioetl/application/services/run_reports/artifact_digest.py` | 96.55% | `partially_covered` |
| `src/bioetl/composition/providers/publication_term_pubmed_enricher.py` | 83.72% | `partially_covered` |
| `src/bioetl/composition/providers/registration_bio_uniprot.py` | 100.0% | `fully_covered` |
| `src/bioetl/domain/config/effective_config_payloads.py` | 100.0% | `fully_covered` |
| `src/bioetl/domain/control_plane/_reproducibility_policy_persistence.py` | 94.12% | `partially_covered` |
| `src/bioetl/domain/control_plane/effective_config_runtime_identity.py` | 100.0% | `fully_covered` |
| `src/bioetl/domain/run_reports/accounting_projections.py` | 96.43% | `partially_covered` |
| `src/bioetl/domain/run_reports/reason_catalog_data.py` | 100.0% | `fully_covered` |
| `src/bioetl/infrastructure/adapters/chembl/target_protein_classification_loading_mixin.py` | 98.46% | `partially_covered` |
| `src/bioetl/infrastructure/control_plane/replay_object_verifier.py` | 88.04% | `partially_covered` |
| `src/bioetl/interfaces/cli/commands/domains/health/_observability_backend_ensure_parts.py` | 100.0% | `fully_covered` |
| `src/bioetl/interfaces/http/_health_server_records_table.py` | 100.0% | `fully_covered` |
| `src/bioetl/interfaces/http/_selected_run_artifact_probes.py` | 77.38% | `partially_covered` |
| `src/bioetl/interfaces/http/_selected_run_report_assessment.py` | 94.87% | `partially_covered` |
| `src/bioetl/interfaces/http/_selector_options_cache.py` | 99.09% | `partially_covered` |
| `src/bioetl/interfaces/http/run_report_index.py` | 100.0% | `fully_covered` |

## Scope and limits

Five-dashboard cutover is explicit in ADR-053 and RULES. Runtime and Provider Health remain retired; optional Scenes fallback contracts and tests match the five shipped UIDs. The merged navigation contract retains exact-run inbound rejection tests, replay checks, row identity and local Provider Evidence.

The full producer excludes opt-in network/live launches. Skips retain their JUnit reasons, including Windows symlink/platform limitations and unavailable optional local tooling. No skipped case is claimed as passed.

GitHub Actions has an external account billing blocker; this local producer is not an exact-SHA CI PASS or machine ADMIT. Live Grafana/browser/render acceptance remains NOT_VERIFIED; no monitoring stack was started.

Raw evidence is retained in `reports/quality/proof-or-stop/audit-11859-coverage-20261002-r8/` in the acceptance worktree. Failed/incomplete earlier attempts were not combined into this XML.

## Concurrent-main refresh (R9)

Producer commit: `98658994ed2cbbe77434de73b4db25f24639dc56`. Source tree SHA-256: `14130992652285370fe8050b43145e3860e88a4374e92f32752407af6607fd32`. XML SHA-256: `427a6bf9bd527084c64d50f1b300d784354e094a11ca7d7a7d46bd197f200a10`.

All 17 groups passed: 32210 PASS, 181 SKIP, 0 failures/errors. Line coverage 99.69%, branch coverage 94.32%; unchanged gates passed. Each shard hash and JUnit result was verified.

Inventory now contains all 2546 current source modules, with no absent paths and unmeasured = 0. The five modules added by concurrent main work are measured below; all accepted numeric values remain nonregressing. R8 above is retained as historical evidence for the original 21 missing measurements.

| Module path | Line coverage | Status |
| --- | ---: | --- |
| `src/bioetl/application/services/dq/disabled_gold_filter.py` | 100.0% | `fully_covered` |
| `src/bioetl/application/services/run_reports/composite.py` | 90.7% | `partially_covered` |
| `src/bioetl/composition/bootstrap/runtime/composite_child_runner.py` | 94.12% | `partially_covered` |
| `src/bioetl/composition/bootstrap/runtime/composite_contract_evidence.py` | 94.74% | `partially_covered` |
| `src/bioetl/composition/bootstrap/runtime/composite_reporter.py` | 71.43% | `partially_covered` |

Raw R9 evidence: `reports/quality/proof-or-stop/audit-11859-coverage-20261002-r9/`. CI remains BLOCKED_EXTERNAL; live browser/render acceptance remains NOT_VERIFIED.
