# Config-root coverage: W44

Closeout status: NOT CLOSED — publication and applicable merge/main acceptance remain required.

Measured HEAD: `896ef11f4c4e7f257d4c92ddff88245b59c84957`.
Source tree SHA-256: `35e6c64feb908c611bdb125ccb2a71a5ff692e0fcf32341032b0c17aec6c21f0`.
Canonical producer: `python -m scripts.engineering.qa.run_local_coverage_verify`.
Execution: native Windows, Python 3.13.7, local_single_host; this is not CI execution identity.

## Measurement

All 17 required shards exited 0. JUnit: 32,715 passed, 196 skipped, 0 failures/errors. Producer exit 0; complete=true; line/branch gates exit 0. Line coverage 99.65%; branch coverage 94.22% (25,386/26,944).

Raw config_root: 40/40 executable lines and 18/18 branches; line 32 hits=1; no missing lines. Meaningful isolated fallback/marker/cwd tests assert the selected filesystem paths. Targeted selection on the same clean SHA: 27 PASS, 40/40 lines, 18/18 branches.

Coverage XML SHA-256: `2b5fcd2a3468c17474b4758fa23612a5cc1f7f9bffe9ec6d3b00e75f206a037d`.

## Adoption and residuals

The canonical nonregressing reporter exited 0. Inventory now contains the exact 2,562-module measured roster, including nine formerly absent modules. No historical per-module floor was lowered. The direct raw candidate guard exited 1: 80 module rows remain below historical percentages; see coverage-regression-ledger-wave-44.json. Retained historical percentages are not fresh W44 measurement.

Three already-existing adopted rows remain below 85%: replay_readiness_checks.py 84.95% (unchanged), composite_reporter.py 75% (previously 71.43%), publication_term_pubmed_enricher.py 83.72% (unchanged). All newly added measured rows are >=85%. The initial local adoption helper stopped because it incorrectly assumed every historical row was already >=85%; the canonical reporter succeeded. adoption-validation-wave-44.json records the independent no-regression/new-roster checks. This does not change repository thresholds or claim all residuals resolved.

Owning checks before committing the inventory: 21 PASS, 1 dirty-artifact SKIP. The first clean rerun exposed stale live metrics in the Codex-authored #5376 historical record (12 below-85 rows versus three adopted rows). An auditable derivation rebinds only live metrics from the canonical inventory; historical shard values and regressed_after_closeout status are preserved. Final clean rerun on e478f838907d632f347e0e76cd5a6dea7ec68936: 22 PASS, 0 failures/errors/skips. Full docs verify on the measured HEAD exited 0.

## Acceptance blockers

CircleCI on measured HEAD confirmed all fast/integration jobs, duplication, Ruff, mypy and SonarCloud. Job 735 recorded 146 architecture failures; architecture PASS is not claimed. Detailed observed failures and sanitized logs are preserved. Docs job 722 lacked the docs extra; Docker config job 732 lacked a required validation-only password. Minimal repairs supply the docs extra and isolated syntax-validation environment; they require new remote checks.

Security job 741 failed on HIGH GHSA-vfj7-8cjw-p6xm, braces 3.0.3, in three lockfiles. The official advisory lists no patched version. No advisory suppression, new exemption, fake version, or security gate weakening is introduced.

No proof-or-stop ADMIT, global architecture closeout, main acceptance or issue closure is claimed. W43 remains immutable failed evidence. Runtime mirror parity N/A: runtime trees unchanged.
