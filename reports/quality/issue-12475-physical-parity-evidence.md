# #12475: physical/logical parity evidence

Status: local real-backend checks verified, with one confirmed Gold nullability finding. This report is evidence for the open issue, not acceptance or closure.

## Provenance

- Repository: `SatoryKono/BioactivityDataAcquisition`.
- Base `main` at latest refresh: `cb17e466e267adaba386c522373f7460fa3bf4f8`; tree `5a46ccde440b84f8725a826658dbd391d9175b04`.
- Tested implementation revision: `70c26231d90e0a4c81f1fa6785525169317e5b3f`; tree `4c7588fe1061f9a54ad3dc2d771d7fa37c106e18`.
- Branch: `codex/issue-12475-parity`.
- Environment: Windows x64, CPython 3.13.7, `deltalake` 0.25.5, PyArrow 25.0.1, Polars 2.0.0, Pandera 0.34.1, zstandard 0.25.0. `.venv-win` was prepared with `powershell -ExecutionPolicy Bypass -File scripts/engineering/dev/setup_env_windows.ps1` from checked-in `uv.lock` (SHA-256 `76596AAE5B29276D6287A91FAEAF984638E653C659E6AF20E39949075485F3C2`).
- Write/read tests use deterministic inputs and real temporary local files/Delta tables; no mocks or repository data fixtures.

## Resolved configuration matrix

The canonical loader resolved all 27 entity configs to two effective sink tuples:

| Count | Bronze | Silver | Gold |
| ---: | --- | --- | --- |
| 25 | JSONL | Delta `merge`, `on_schema_mismatch=evolve` | Delta SCD2 |
| 2 | JSONL | Delta `merge`, `on_schema_mismatch=evolve` | Delta overwrite |

Real temporary-backend write/read tests exercise compressed Bronze JSONL, Silver Delta merge/evolve, Gold Delta SCD2, and Gold Delta overwrite. Bronze stores no physical schema; its parsed JSON string, float, integer, boolean, and null values are checked after readback, while schema nullability is not applicable to its format.

## Criteria and results

| Criterion | Evidence and observation | Result |
| --- | --- | --- |
| Resolve each layer's actual format and modes | `test_resolved_production_sink_matrix_for_issue_12475`; all 27 configs resolve to the tuples above | Verified |
| Bronze write/read | `test_bronze_jsonl_zstd_write_read_preserves_json_values`; `.zst` JSONL round trip preserves string, float, integer, boolean, and null | Verified; no persisted schema exists |
| Silver write/read, types, nullability, field addition | `test_silver_delta_evolve_readback_matches_types_and_nullability`; readback: `entity_id:string not-null`, `value:int64 not-null`, `new_field:string nullable`, two rows | Verified; nullable addition is accepted by active `evolve` policy |
| Silver type change under current evolution rules | `test_silver_delta_type_change_negative_control_is_schema_mismatch`; existing `value:string`, incoming `value:int64`; exact `SchemaEvolutionError.changed_fields={"value": ("string", "int64")}`; stored type remains string | Verified negative control; type changes require migration/new table version under RULES Appendix E |
| Gold types and nullability vs strict ChEMBL Publication contract | `test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row` reads the strict ChEMBL Publication Delta table; physical Arrow types match logical types | **Confirmed finding:** every physical field reads nullable, including logical non-null `entity_id`, `title`, `_is_current`, `_version`, and `_valid_from`. Nullability parity remains open for backend/contract-owner disposition. |
| Repeated Gold SCD2 write | Same test writes v1 at 12:00 UTC then v2 at 13:00 UTC: v1 is `_is_current=false`, `_version=1`, `_valid_from=12:00`, `_valid_to=13:00`; v2 is `_is_current=true`, `_version=2`, `_valid_from=13:00`, `_valid_to=null`. Rewriting unchanged v2 at 14:00 adds no row. | Verified after fixing the missing insert of a changed current version |
| Gold overwrite mode | `test_gold_writer_overwrite_is_idempotent_for_identical_records` | Verified |
| Negative control diagnoses schema mismatch, not conversion/I/O error | Silver type-change check asserts exact `SchemaEvolutionError` payload and unchanged persisted Delta type | Verified |

Gold uses the actual `ChEMBLPublicationGoldSchema` with `entity_id=CHEMBL123`, titles `Title v1` / `Title v2`, hashes `a…` / `b…`, and populated publication-year, citation-count, and source-ID fields. The checked physical types match that strict schema and the SCD2 metadata types. `DeltaTable.schema().to_pyarrow()` reports every field nullable. `_valid_to` is logically nullable, but required fields and `_is_current:boolean`, `_version:int64`, `_valid_from:string` also read nullable. This is not claimed as full nullability parity.

## Commands and outcomes

Owning test command, run on implementation revision `70c26231d90e0a4c81f1fa6785525169317e5b3f`:

```text
.venv-win\Scripts\python.exe -m pytest -q tests/unit/domain/exceptions/test_storage.py tests/unit/infrastructure/storage/test_silver_writer_validation.py tests/unit/infrastructure/storage/test_gold_writer_integration.py::test_write_scd2_existing_table tests/integration/infrastructure/storage/test_issue_12475_physical_parity.py tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_gold_writer_overwrite_is_idempotent_for_identical_records tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionErrorMode::test_schema_drift_error_mode_raises_on_new_field tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionEvolveMode::test_schema_evolve_mode_allows_new_fields -s
exit code: 0; 84 passed; stdout: 84 passing-test dots; stderr: empty
```

| Check | Exit | Outcome |
| --- | ---: | --- |
| `.venv-win\Scripts\python.exe -m ruff check` on three changed source files and four changed test files | 0 | All checks passed |
| `.venv-win\Scripts\python.exe -m scripts.engineering.qa refresh-ci-drift-families --update --test-gov --flaky-fingerprint --evidence --remote-main --dataflow` | 0 | Documented order; no budget ratchet |
| `.venv-win\Scripts\python.exe -m scripts.engineering.qa.refresh_governance_artifacts` | 0 | Standard generated-artifact refresh completed |
| `.venv-win\Scripts\python.exe -m scripts.engineering.qa.refresh_governance_artifacts --check` | 0 | Current; clean-artifact assertion was skipped while source was dirty, then passed after implementation commit |
| `.venv-win\Scripts\python.exe -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml` | 0 after refresh | Source hash rebound; existing measured rows retained |
| `.venv-win\Scripts\python.exe -m scripts.engineering.qa.generate_architecture_dependency_map --check` | 0 after refresh | Current |
| `git diff --check` | 0 | No whitespace errors |

Full local coverage verification was attempted with `.venv-win\Scripts\python.exe -m scripts.engineering.qa.run_local_coverage_verify --max-workers 1` at revision `46df68864ecef46dcd9ea1cef4b0aff98b282f28`. The preserved manifest is `C:\Users\Fedor\.codex\preserved\issue-12475-initial-20261028\local-coverage-run-f1949-20261028`; its SHA-256 is `53D04BBE68FFB3A2E6852D3D8275A4FA8C29060229865878A1D9939989DF34B3`. It contains 14 successful and 3 unsuccessful shards, so `complete=false` and cannot refresh telemetry. The infrastructure shard's SCD2 no-op regression was corrected in `70c2623`; two remaining failures are unrelated to this issue: `test_real_daily_caller_and_command_partition_are_complete` (expected workflow fallback option absent from `pr-required.yml`) and `test_private_host_delivery_binds_source_and_survives_data_volume` (optional Grafana provisioning artifact hash mismatch). The preserved manifest predates the latest main and is not treated as qualifying coverage.

Latest hash-only module-coverage, architecture dependency-map, governance-artifact and selected CI-family checks pass after their documented refreshes. `.venv-win\Scripts\python.exe -m scripts.engineering.qa refresh-ci-drift-families --check --telemetry` exits 1: the two telemetry governance tests detect live test-source hash `2933f65e1531d917d3fa98a97f9c774bff9d18781e781c3fddf4f63f9fd61aac` differing from committed baseline `fd232459ae26a6b0fd0373eac78702a3d0d12ed773d12a8b3dff492df1ab4c07`. No partial coverage or manually constructed identity was used to rebind it; a qualifying source-bound CI run is still required.

## Prior results and seven substantive PR #12597 review concerns

- Reused completed Jules sessions `10409628220972484284` and `13038177790950470904` and merged PR #12597; no third equivalent audit or parallel writer was started.
- Addressed four in-scope evidence gaps: distinguish field addition from type change; exercise a second SCD2 version; bind evidence to exact revision, commands, inputs, and backend versions; use the actual strict ChEMBL Publication schema.
- Three comments concern telemetry-source reset, an unrelated #12375 report discrepancy, and unrelated test-governance classification. They are outside #12475 and were not modified.
- The historical #12597 claim that `evolve` rejects field addition was false on the real Silver backend. Addition is accepted; type change is measured separately and rejected under the migration policy.

## Closeout still pending

- Independent reviewer is not assigned; the author does not self-approve the Gold nullability finding.
- Draft PR [#12606](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12606) was published from `codex/issue-12475-parity` at `23fcc8a0223b40481b88289a66d71eba091e0618`, based on `main` `cb17e466e267adaba386c522373f7460fa3bf4f8`. GitHub reported `Classify changes (decision matrix)` in progress at publication verification. Review, merge, and issue acceptance remain pending; none is implied by the Draft PR.
- #12474 has not been started and remains gated on confirmed full #12475 acceptance.
