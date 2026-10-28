# #12475: physical/logical parity evidence

Status: local real-backend checks verified, with one confirmed Gold nullability finding. This report is evidence for the open issue, not acceptance or closure.

## Provenance

- Repository: `SatoryKono/BioactivityDataAcquisition`.
- Base `main` at refresh: `71d01d3271874be76a2ab94744b55df1ba2cf6c4`; tree `4e1eccb8c0c23885d82375b5f9dde8b873e34489`.
- Tested implementation and full-matrix revision: `5d144a4458b73444979be8730be9fee09f7edd47`; tree `0850fdd992983dfe97754b139d81698d5516224b`.
- Branch: `codex/issue-12475-closeout`.
- Environment: Windows x64, CPython 3.13.7, `deltalake` 0.25.5, PyArrow 25.0.1, Polars 2.0.0, Pandera 0.34.1, zstandard 0.25.0. `.venv-win` was prepared with `powershell -ExecutionPolicy Bypass -File scripts/engineering/dev/setup_env_windows.ps1` from checked-in `uv.lock` (SHA-256 `76596AAE5B29276D6287A91FAEAF984638E653C659E6AF20E39949075485F3C2`).
- Write/read tests use deterministic inputs and real temporary local files/Delta tables; no mocks or repository data fixtures.

## Resolved configuration matrix

The canonical loader resolved all 27 entity configs to two effective sink tuples:

| Count | Bronze | Silver | Gold |
| ---: | --- | --- | --- |
| 25 | JSONL | Delta `merge`, `on_schema_mismatch=evolve` | Delta SCD2 |
| 2 | JSONL | Delta `merge`, `on_schema_mismatch=evolve` | Delta overwrite |

`test_every_resolved_pipeline_config_writes_and_reads_all_layers` reloads each of the 27 canonical configs and performs Bronze JSONL, Silver Delta merge/evolve, and the configured Gold Delta mode against distinct temporary physical tables; every layer is read back and checked for the expected record. Bronze stores no physical schema; its parsed JSON values and types are separately checked, while schema nullability is not applicable to its format.

## Criteria and results

| Criterion | Evidence and observation | Result |
| --- | --- | --- |
| Resolve and write/read every allowed layer configuration | `test_resolved_production_sink_matrix_for_issue_12475` and `test_every_resolved_pipeline_config_writes_and_reads_all_layers`; all 27 configs resolve to the tuples above and each config writes and reads each layer using its configured Gold mode | Verified |
| Bronze write/read | `test_bronze_jsonl_zstd_write_read_preserves_json_values`; `.zst` JSONL round trip preserves string, float, integer, boolean, and null | Verified; no persisted schema exists |
| Silver write/read, types, nullability, field addition | `test_silver_delta_evolve_readback_matches_types_and_nullability`; readback: `entity_id:string not-null`, `value:int64 not-null`, `new_field:string nullable`, two rows | Verified; nullable addition is accepted by active `evolve` policy |
| Silver type change under current evolution rules | `test_silver_delta_type_change_negative_control_is_schema_mismatch`; existing `value:string`, incoming `value:int64`; exact `SchemaEvolutionError.changed_fields={"value": ("string", "int64")}`; stored type remains string | Verified negative control; type changes require migration/new table version under RULES Appendix E |
| Gold types and nullability vs strict ChEMBL Publication contract | `test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row` reads the strict ChEMBL Publication Delta table; physical Arrow types match logical types | **Confirmed finding:** every physical field reads nullable, including logical non-null `entity_id`, `title`, `_is_current`, `_version`, and `_valid_from`. Nullability parity remains open for backend/contract-owner disposition. |
| Repeated Gold SCD2 write | Same test writes v1 at 12:00 UTC then v2 at 13:00 UTC: v1 is `_is_current=false`, `_version=1`, `_valid_from=12:00`, `_valid_to=13:00`; v2 is `_is_current=true`, `_version=2`, `_valid_from=13:00`, `_valid_to=null`. Rewriting unchanged v2 at 14:00 adds no row. | Verified after fixing the missing insert of a changed current version |
| Gold overwrite mode | `test_gold_writer_overwrite_is_idempotent_for_identical_records` | Verified |
| Negative control diagnoses schema mismatch, not conversion/I/O error | Silver type-change check asserts exact `SchemaEvolutionError` payload and unchanged persisted Delta type | Verified |

Gold uses the actual `ChEMBLPublicationGoldSchema` with `entity_id=CHEMBL123`, titles `Title v1` / `Title v2`, hashes `a…` / `b…`, and populated publication-year, citation-count, and source-ID fields. The checked physical types match that strict schema and the SCD2 metadata types. `DeltaTable.schema().to_pyarrow()` reports every field nullable. `_valid_to` is logically nullable, but required fields and `_is_current:boolean`, `_version:int64`, `_valid_from:string` also read nullable. This is not claimed as full nullability parity.

Physical Gold readback columns asserted by the test, grouped by Arrow type (all physical fields had `nullable=true`): `string`: `_source`, `_lookup_method`, `_original_id`, `entity_id`, `content_hash`, `publication_id`, `publication_doi`, `publication_pmid`, `publication_pmc_id`, `doi`, `pmid`, `title`, `authors`, `abstract`, `author_keys`, `publication_type`, `journal`, `volume`, `issue`, `page_first`, `page_last`, `chembl_release`, `creation_date`, `_valid_from`, `_valid_to`; `bool`: `_dq_warn`, `_dq_error`, `_is_current`; `int64`: `_index`, `_version`; `double`: `publication_year`, `citations_received`, `citations_made`, `src_id`. Silver's evolved readback was exactly `entity_id:string not-null`, `value:int64 not-null`, `new_field:string nullable`; run-scoped metadata columns are intentionally removed by `NONDETERMINISTIC_PERSISTED_FIELDS` before that schema comparison.

## Commands and outcomes

Owning test command, rerun on exact implementation revision `5d144a4458b73444979be8730be9fee09f7edd47`:

```text
.venv-win\Scripts\python.exe -m pytest -q tests/unit/domain/exceptions/test_storage.py tests/unit/infrastructure/storage/test_silver_writer_validation.py tests/unit/infrastructure/storage/silver_writer/test_silver_writer_schema.py tests/unit/infrastructure/storage/test_gold_writer.py::TestGoldWriterSCD2::test_write_gold_scd2_merge_existing_table tests/unit/infrastructure/storage/test_gold_writer_integration.py::test_write_scd2_existing_table tests/integration/infrastructure/storage/test_issue_12475_physical_parity.py tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_gold_writer_overwrite_is_idempotent_for_identical_records tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionErrorMode::test_schema_drift_error_mode_raises_on_new_field tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionEvolveMode::test_schema_evolve_mode_allows_new_fields -s
exit code: 0; 98 selected tests passed; stdout: 98 progress dots; stderr: empty

The command includes regressions for input fields excluded by the prepared Arrow schema and Gold's current Delta merge API. `test_schema_drift_detects_record_fields_outside_prepared_schema` verifies that `on_schema_mismatch="error"` still reports the added field after the configured schema filters it from the Arrow payload. The existing SCD2 unit check now asserts the current filtered `when_not_matched_insert(...)` behavior, including its insert predicate and entity-key projection; it no longer expects the obsolete unfiltered `when_not_matched_insert_all()` call. Two Silver unit assertions were updated to include the `incoming_schema` keyword argument. No tested contract was weakened.
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

Latest hash-only module-coverage, architecture dependency-map, governance-artifact and selected CI-family checks pass after their documented refreshes. `.venv-win\Scripts\python.exe -m scripts.engineering.qa refresh-ci-drift-families --check --telemetry` exits 1: the two telemetry governance tests detect live test-source hash `d65f6b20251c80ffbcc5b09ea96c66e5ee6603111f791054849d5fa7827e68bb` differing from committed baseline `fd232459ae26a6b0fd0373eac78702a3d0d12ed773d12a8b3dff492df1ab4c07`. No partial coverage or manually constructed identity was used to rebind it; a qualifying source-bound CI run is still required.

## Prior results and seven substantive PR #12597 review concerns

- Reused completed Jules sessions `10409628220972484284` and `13038177790950470904` and merged PR #12597; no third equivalent audit or parallel writer was started.
- Addressed four in-scope evidence gaps: distinguish field addition from type change; exercise a second SCD2 version; bind evidence to exact revision, commands, inputs, and backend versions; use the actual strict ChEMBL Publication schema.
- Three comments concern telemetry-source reset, an unrelated #12375 report discrepancy, and unrelated test-governance classification. They are outside #12475 and were not modified.
- The historical #12597 claim that `evolve` rejects field addition was false on the real Silver backend. Addition is accepted; type change is measured separately and rejected under the migration policy.

## Closeout still pending

- PR [#12606](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12606) was merged at `f8bbed37354c740165e41dd1acf70c5ba2d7ed49` from head `094a0e3031c9c98dd486a4af32475449fbb16c9c`, based on `cb17e466e267adaba386c522373f7460fa3bf4f8`. Its PR Gate Class lane and SonarCloud Code Analysis failed. The current `main` base `71d01d3271874be76a2ab94744b55df1ba2cf6c4` includes the later SCD2 complexity and VCR inventory corrections; those exact architecture and inventory tests pass on this follow-up branch.
- Follow-up branch `codex/issue-12475-closeout` contains the issue-specific Silver schema-drift fix and regression. The owning command above and selected architecture/route tests pass at implementation commit `5d144a4458b73444979be8730be9fee09f7edd47`; clean-state full governance-artifact check and the coupled CI drift check excluding telemetry also pass. The branch is not yet published as a PR.
- Committed telemetry remains stale for this branch's test-source tree. Per `docs/05-engineering/test-telemetry-baseline.md`, a manually dispatched Nightly run on this branch and its exact coverage and duration artifacts are required before refreshing the telemetry baseline. This run and the resulting clean telemetry check are pending.
- Independent reviewer is not assigned; the author does not self-approve the confirmed Gold nullability finding. The issue remains OPEN. Its seven review concerns and measured real-backend results are documented above; final acceptance and closeout passport still require a qualifying published revision, CI/review evidence, and independent review.
- #12474 has not been started and remains gated on confirmed full #12475 acceptance.
