# Test Health Rollup

Historical test-health evidence for recent recorded lane runs.

Runs analyzed: 30

## Current Authoritative Baseline

- Current merge-blocking truth comes from live CI status and the `coverage-verify` hard coverage gate.
- This rollup is historical evidence only and must not be read as the current pass/fail baseline.
- Committed baseline artifact: `configs/quality/test_telemetry_baseline.yaml`
- Source branch: `main`
- Source commit: `667c3020ce74f87c319f77612c765a5aaf30e6ad`
- Source run id: `local-duration-rebuild-2026-07-23`
- Refresh status: `captured`
- Coverage baseline: `92.44%` (threshold `85.0%`)
- Duration telemetry cases: `23360`

## Suites

| Suite | Runs | Non-green | Pass rate | Test failures | Unique failing tests | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coverage-verify | 30 | 27 | 10.0% | 33 | 25 | 1811 |

## Failure Classifications

- `assertion`: 32
- `setup_error`: 1

## New Failures

- `coverage-verify`: `tests.architecture.test_tech_debt_issues_5707_5715_closeout::test_issue_5714_dead_code_governance_has_no_untriaged_candidates`

## Flaky Candidates

- `tests.architecture.test_adr_enforcement_matrix::test_adr_enforcement_matrix_artifact_matches_live_generator`
- `tests.architecture.test_architecture_quality_scorecard::test_architecture_quality_scorecard_artifact_matches_live_collector`
- `tests.architecture.test_documentation_issues_6487_6488_closeout::test_issue_6487_inventory_count_and_docs_workflow_are_source_derived`
- `tests.architecture.test_duplication_report_governance::test_specialized_duplication_markdown_matches_json_payload`
- `tests.architecture.test_low_coverage_targeted_tests_6045::test_issue_6045_targeted_low_coverage_closeout_is_coherent`
- `tests.architecture.test_observability_metric_governance::test_runtime_cardinality_evidence_artifact_is_committed_and_governed`
- `tests.architecture.test_quality_debt_scorecard::test_debt_scorecard_hotspot_family_metrics_match_committed_baseline`
- `tests.architecture.test_source_module_governance_inventory::test_oversized_source_module_inventory_tracks_current_top_modules`
- `tests.architecture.test_tech_debt_issues_5395_5401_closeout::test_issue_5400_hotspot_family_budget_warnings_are_reviewed_budget_closures`
- `tests.architecture.test_tech_debt_issues_5514_5515_governance::test_issue_5514_flaky_test_burndown_review_matches_canonical_inputs`

## Top Failing Nodeids

- 3x `tests.architecture.test_quality_debt_scorecard::test_debt_scorecard_hotspot_family_metrics_match_committed_baseline`
- 3x `tests.architecture.test_tech_debt_issues_5514_5515_governance::test_issue_5514_flaky_test_burndown_review_matches_canonical_inputs`
- 3x `tests.architecture.test_tech_debt_issues_5752_5755_closeout::test_issue_5752_narrative_reports_match_live_governance_artifacts`
- 2x `tests.architecture.test_documentation_issues_6487_6488_closeout::test_issue_6487_inventory_count_and_docs_workflow_are_source_derived`
- 2x `tests.architecture.test_tech_debt_issues_5790_5796_closeout::test_issue_5796_zero_reference_supporting_scripts_have_owner_or_removal_governance`
- 1x `tests.architecture.test_adr_enforcement_matrix::test_adr_enforcement_matrix_artifact_matches_live_generator`
- 1x `tests.architecture.test_architecture_quality_scorecard::test_architecture_quality_scorecard_artifact_matches_live_collector`
- 1x `tests.architecture.test_duplication_report_governance::test_specialized_duplication_markdown_matches_json_payload`
- 1x `tests.architecture.test_low_coverage_targeted_tests_6045::test_issue_6045_targeted_low_coverage_closeout_is_coherent`
- 1x `tests.architecture.test_observability_metric_governance::test_runtime_cardinality_evidence_artifact_is_committed_and_governed`
