# #12475: physical/logical parity evidence

Status: local real-backend checks verified, with one confirmed Gold nullability finding. This report is evidence for the open issue, not acceptance or closure.

## Provenance

- Repository: `SatoryKono/BioactivityDataAcquisition`.
- Base `main`: `2f121a4117a0fdac9926a0c352cdd31330878429`; tree `5dc0dbeb0564423c7828d77fa876e92eb22cba66`.
- Tested implementation revision: `cb16dd9ea868f29e1f1dcadf337bed08967c0114`; tree `42955cad0dbd6b739e46363254bc15a51e479868`.
- Branch: `codex/issue-12475-parity`.
- Environment: Windows x64, CPython 3.13.7, `deltalake` 0.25.5, PyArrow 25.0.1, Polars 2.0.0, Pandera 0.34.1, zstandard 0.25.0. `.venv-win` was prepared by `scripts/engineering/dev/setup_env_windows.ps1` from checked-in `uv.lock` (SHA-256 `76596AAE5B29276D6287A91FAEAF984638E653C659E6AF20E39949075485F3C2`).
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

Owning test command, run on implementation revision `cb16dd9ea868f29e1f1dcadf337bed08967c0114`:

```text
.venv-win\Scripts\python.exe -m pytest -q tests/unit/domain/exceptions/test_storage.py tests/unit/infrastructure/storage/test_silver_writer_validation.py tests/integration/infrastructure/storage/test_issue_12475_physical_parity.py tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row tests/integration/infrastructure/storage/test_gold_writer_versioning.py::test_gold_writer_overwrite_is_idempotent_for_identical_records tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionErrorMode::test_schema_drift_error_mode_raises_on_new_field tests/e2e/test_pipeline_with_schema_drift_e2e.py::TestSchemaEvolutionEvolveMode::test_schema_evolve_mode_allows_new_fields -s
exit code: 0; 83 passed; stdout: 83 passing-test dots; stderr: empty
```

| Check | Exit | Outcome |
| --- | ---: | --- |
| Ruff on three changed source files and two changed test files | 0 | All checks passed |
| `python -m scripts.engineering.qa refresh-ci-drift-families --update --test-gov --flaky-fingerprint --evidence --remote-main --dataflow` | 0 | Documented order; no budget ratchet |
| `python -m scripts.engineering.qa.refresh_governance_artifacts` | 0 | Standard generated-artifact refresh completed |
| `python -m scripts.engineering.qa.refresh_governance_artifacts --check` | 0 | Current; clean-artifact assertion was skipped while source was dirty, then passed after implementation commit |
| `python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml` | 0 after refresh | Source hash rebound; existing measured rows retained |
| `python -m scripts.engineering.qa.generate_architecture_dependency_map --check` | 0 after refresh | Current |
| `git diff --check` | 0 | No whitespace errors |

The telemetry family check currently fails because the new tests changed its audited test-source hash. It may only be rebound from a qualifying full local 17-shard manifest or source-bound CI run; no synthetic coverage or run identity is used. The full local coverage run and telemetry rebind remain pending.

## Prior results and seven substantive PR #12597 review concerns

- Reused completed Jules sessions `10409628220972484284` and `13038177790950470904` and merged PR #12597; no third equivalent audit or parallel writer was started.
- Addressed four in-scope evidence gaps: distinguish field addition from type change; exercise a second SCD2 version; bind evidence to exact revision, commands, inputs, and backend versions; use the actual strict ChEMBL Publication schema.
- Three comments concern telemetry-source reset, an unrelated #12375 report discrepancy, and unrelated test-governance classification. They are outside #12475 and were not modified.
- The historical #12597 claim that `evolve` rejects field addition was false on the real Silver backend. Addition is accepted; type change is measured separately and rejected under the migration policy.

## Closeout still pending

- Independent reviewer is not assigned; the author does not self-approve the Gold nullability finding.
- Draft PR publication, remote SHA, PR CI, review/merge, and issue acceptance remain pending; none is implied by this report.
- #12474 has not been started and remains gated on confirmed full #12475 acceptance.
