# Audit issue batch: implementation and remaining acceptance

Source measurement SHA: `3d6b0a76c625f3fb04cde47f708613d3217422b5`.
Source tree SHA-256: `7a13b1bd58ed783e2c3c03d183387ac9715a1408d2c48b5be388614bf23cf9c9`.
Status: **NOT CLOSED / NOT READY TO MERGE**. No full-suite or render PASS is claimed.

## Issue map

The supplied titles were shifted relative to the live GitHub issue numbers.
The live mapping used here is:

| Issue | Implemented / verified surface | Remaining acceptance |
| --- | --- | --- |
| #11846 | Canonical census, hotspot, coverage digest, scorecard and debt gates reconciled; one generated current headline section; historical audited SHA retained | Final independent/CI evidence; complete coverage is separate #11745 |
| #11847 | Upstream Merge/Gold pilot retained after merge; scoped tests and typing pass | Trusted closeout on final SHA |
| #11853 | Typed hosts for Bronze, Silver, BatchWriter tracing, Merge output, DQ and Medallion lifecycle; unjustified casts 129 to 76, PD4 60 to 12 | Trusted closeout on final SHA |
| #11848 | Application owns manifest lookup and snapshot selection; Composition wires stores/settings; cached-empty and ID/run fallback behavior tested | Trusted closeout on final SHA |
| #11849 | Caller/export/owner decisions recorded; motivated no-change for four compatibility/policy-bearing seams | Trusted closeout on final SHA |
| #11850 | Two private Grafana script implementations consolidated into existing owners; active 340 to 338, cap 338 unchanged; public platform wrappers retained | Trusted closeout on final SHA |
| #11851 | DDD selected invariant/test links; tracked/excluded port universe; full-name import-time SCC cycle guard including three-node cycles | Trusted closeout; semantic DDD completeness and deferred imports remain explicitly outside these proxies |
| #11856 | Devin exception and Junie OpenCode already upstream; deprecated mirror reduced to runtime-first pointer | Trusted closeout; mirror check passes |
| #11857 | Upstream diagram residual fixes verified; leftover tool paths, disabled-nightly wording and security test import repaired | Trusted closeout; disabled nightly remains an accepted residual |
| #11858 | Active parity guide, generated panel block routing, single check-links chain; complete docs verify passed | Final docs verification after generated metadata refresh |
| #11859 | Upstream CLI/layer docs and shared RunReportStore retained; scanner counts/provenance clarified | Trusted closeout |
| #11842 | Retired UID absent from shipped matrix test; inventory/content contracts regenerated for 134 panels and five dashboards | Trusted closeout |
| #11843 | README shipped portfolio is five; generated panel guides reconciled | Trusted closeout |
| #11844 | Canonical semantic/render cycle attempted and failed honestly | Grafana env credentials return HTTP 401; worktree runtime identity differs from running canonical backend; full browser render not accepted |
| #11745 | Full local 17-shard producer attempted; partial XML is not combined or published as full coverage | Existing integration contract failures; rerun all 17 on fixed source/tests after repair |
| #11854 | Meta program tracks the children above; #11852 was already closed | Keep open until all children qualify |

## Evidence and limitations

- 276 focused source tests passed after merging main; mypy passed on 11 source files.
- 173 repo-backed observability tooling tests passed; the broader observability unit suite also passed after retiring old fixtures.
- Required dashboard operator readability, first-window no-scroll and replay layout checks passed (30 tests).
- Full `python -m scripts.docs verify` passed, including strict MkDocs build.
- Codex–Junie parity, cast census and hotspot baseline checks passed.
- Scripts catalog: 636 scripts, 338 active, 298 supporting; no status laundering or cap increase.
- Debt governance: 46 pass / 0 fail; these gates do not establish full-suite success.
- First coverage attempt stopped on an obsolete import of the removed Mermaid duplicate. Second attempt retained as failed diagnostics after a stale Runtime route assertion. Tests were then corrected; it is not an admissible fixed-test-tree coverage measurement and must not be reused as full coverage.
- Expanded dashboard integration run: **245 tests, 66 failures, 1 skip**. Failures include retired UID references, stale navigation/requirements, and geometry conflicts with the inherited new layout. Detailed nodeids follow below. These are not silently waived or made green by raising budgets.
- Grafana render API returned HTML (`<!DOCTYPE`, not PNG) in files named `.png`; those files are rejected as screenshot evidence. Playwright also failed authentication/expanded-row capture. No fake screenshot PASS.
- Live GitHub run 36915469730 / job 110548240854 on upstream SHA `98fdd9b7e27b97a3f50799a461eb188b87bf2226` had zero steps; annotation: account locked due to billing issue. This is evidence of external CI unavailability, not validation of this branch.
- Proof-or-stop policy limits `local_single_host` to DEGRADED; ADMIT is required for lifecycle transitions. No issues are closed from local prose alone.
- `.env` was read only. Main checkout and concurrent work were preserved.

## Remaining dashboard failures

- `tests.integration.test_dashboard_first_window_containment::test_every_first_window_table_owns_a_row_cap`
- `tests.integration.test_dashboard_first_window_containment::test_trust_9418_keeps_verdict_and_reason_count_visible`
- `tests.integration.test_dashboard_first_window_containment::test_trust_9416_hides_forensic_columns_without_wrapping_detail`
- `tests.integration.test_dashboard_first_window_containment::test_first_window_forced_widths_fit_200pct_css_budget`
- `tests.integration.test_dashboard_first_window_containment::test_first_window_scope_banners_name_current_range_and_selected_run`
- `tests.integration.test_dashboard_first_window_containment::test_overview_215_9002_fit_first_window_without_raising_fold`
- `tests.integration.test_dashboard_navigation_contract_sync::test_navigation_contract_uids_match_shipped_dashboards`
- `tests.integration.test_dashboard_navigation_contract_sync::test_required_inbound_paths_match_overview_first_action_mirror`
- `tests.integration.test_dashboard_cross_scope_titles::test_cross_scope_links_use_required_titles`
- `tests.integration.test_dashboard_cross_scope_titles::test_workflow_dashboard_provenance_banner_makes_scope_split_explicit`
- `tests.integration.test_dashboard_cross_scope_titles::test_workflow_status_panel_repeats_selected_range_contract`
- `tests.integration.test_dashboard_cross_scope_titles::test_provider_health_descriptions_separate_global_and_selected_scope`
- `tests.integration.test_dashboard_json_metadata_contract::test_dashboard_time_refresh_by_level`
- `tests.integration.test_dashboard_content_contract::test_content_contract_fails_closed_when_table_columns_are_omitted`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_panels_meet_type_aware_minimum_height`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_canonical_answer_panels_are_root_first_window`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_always_visible_nonrow_stack_fits_viewport`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_content_panel_titles_use_canonical_action_verbs`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_scalar_density_survey_runs_on_shipped_dashboards`
- `tests.integration.test_dashboard_geometry_and_purpose_contracts::test_group_scalar_density_exceeds_first_screen_where_enforced`
- `tests.integration.test_dashboard_collapsed_rows::test_every_dashboard_has_at_least_one_row`
- `tests.integration.test_dashboard_collapsed_rows::test_row_groups_materialize_expanded_for_test_stage`
- `tests.integration.test_dashboard_qa_9088::test_canonical_context_trims_run_id_and_shares_uuid_across_seven_uids`
- `tests.integration.test_dashboard_qa_9088::test_provider_freshness_is_not_present_ok_on_missing_health_status`
- `tests.integration.test_dashboard_qa_9088::test_current_card_disposition_covers_first_window_current_panels`
- `tests.integration.test_dashboard_provider_context_mapping::test_provider_context_mapping_preserves_source_values`
- `tests.integration.test_dashboard_qa_check_gates::test_dashboard_inventory_check_passes_shipped_dashboards`
- `tests.integration.test_dashboard_qa_check_gates::test_visual_semantics_check_passes_shipped_dashboards`
- `tests.integration.ci.test_dashboard_active_docs_sync::test_active_docs_sync_workflow_selector_and_cta_titles`
- `tests.integration.ci.test_dashboard_active_docs_sync::test_http_identity_panel_docs_match_shipped_datasource_contract[bioetl-overview-v2-Review Run Identity-Review Processed Records-9300-9301]`
- `tests.integration.ci.test_dashboard_active_docs_sync::test_http_identity_panel_docs_match_shipped_datasource_contract[bioetl-provider-health-v2-Inspect Run Identity-Inspect Processed Records-9402-9403]`
- `tests.integration.ci.test_dashboard_active_docs_sync::test_http_identity_panel_docs_match_shipped_datasource_contract[bioetl-runtime-Inspect Pipeline Identity-Inspect Processed Records-9402-9403]`
- `tests.integration.test_dashboard_vis_stream3_layout::test_overview_dq_timeline_hides_dotstar_and_in_band_state`
- `tests.integration.test_dashboard_vis_stream3_layout::test_set_range_action_names_run_explorer_handoff`
- `tests.integration.test_dashboard_vis_stream3_layout::test_overview_and_dq_lower_handoffs_are_explicit_links`
- `tests.integration.test_dashboard_vis_stream3_layout::test_run_id_selector_and_recent_runs_do_not_label_uuid_as_count`
- `tests.integration.test_dashboard_vis_stream2_layout::test_replay_anchor_tables_hide_internal_columns_and_rename_operator_fields`
- `tests.integration.test_dashboard_vis_stream2_layout::test_identity_values_and_gaps_use_short_values_and_compact_height`
- `tests.integration.test_dashboard_vis_stream2_layout::test_read_latency_defaults_to_p95_table_legend`
- `tests.integration.test_dashboard_vis_stream2_layout::test_provider_severity_column_has_min_width_and_narrower_provider`
- `tests.integration.test_dashboard_vis_stream2_layout::test_nav_chips_use_eight_px_gap_and_status_stats_stay_compact`
- `tests.integration.test_dashboard_visual_semantics::test_dq_history_colors_survive_trailing_missing_samples`
- `tests.integration.test_dashboard_visual_semantics::test_status_panels_have_correct_value_mapping`
- `tests.integration.test_dashboard_variable_dependencies::test_runtime_variable_dependencies`
- `tests.integration.test_dashboard_variable_dependencies::test_provider_health_variable_dependencies`
- `tests.integration.test_dashboard_structural_invariants::test_internal_dashboard_links_resolve_to_shipped_uids`
- `tests.integration.test_dashboard_structural_invariants::test_panel_types_are_allowlisted`
- `tests.integration.test_dashboard_static_fill_gates::test_navigation_bus_uses_full_width_short_band`
- `tests.integration.test_dashboard_selection_actions::test_navigation_preserves_selector_url_values[path0]`
- `tests.integration.test_dashboard_selection_actions::test_navigation_preserves_selector_url_values[path1]`
- `tests.integration.test_dashboard_selection_actions::test_navigation_preserves_selector_url_values[path2]`
- `tests.integration.test_dashboard_selection_actions::test_navigation_preserves_selector_url_values[path3]`
- `tests.integration.test_dashboard_scope_refactor::test_query_panel_descriptions_carry_scope_badge`
- `tests.integration.test_dashboard_scope_refactor::test_first_window_coverage_set_range_and_refresh_copy`
- `tests.integration.test_dashboard_scope_refactor::test_compact_selected_run_summary_uses_shared_projection`
- `tests.integration.test_dashboard_scope_refactor::test_provider_reason_and_causes_share_empty_state`
- `tests.integration.test_dashboard_scope_refactor::test_run_explorer_selects_rows_without_removed_detail_groups`
- `tests.integration.test_dashboard_requirement_gates::test_six_shipped_uids_match_requirement_gates`
- `tests.integration.test_dashboard_requirement_gates::test_operator_question_and_collapsed_forensics`
- `tests.integration.test_dashboard_requirement_coverage::test_dash_first_001_operator_question_contract`
- `tests.integration.test_dashboard_requirement_coverage::test_dash_first_002_fails_closed_on_uncollapsed_or_unallowlisted_inspect`
- `tests.integration.test_dashboard_requirement_coverage::test_dash_action_001_copy_001_state_002_cta_empty_state_and_palette`
- `tests.integration.test_dashboard_requirement_coverage::test_requirement_coverage_matrix_lists_every_dash_id_and_nodeids`
- `tests.integration.test_dashboard_requirement_coverage::test_dash_copy_001_fails_closed_without_empty_state_copy`
- `tests.integration.test_dashboard_required_panel_links::test_overview_dashboard_required_panel_links`
- `tests.integration.test_dashboard_required_panel_links::test_workflow_overview_required_panel_links`


## Architecture program and config-root measurement checkpoint — 2026-10-04

This checkpoint preserves the earlier audit results above. It records local implementation and measurement; the source-bound final acceptance receipts remain the authority for completion.

Branch: `codex/architecture-coverage-closeout-11854-11899`. Complete 17-group producer measurement commit: `24f569369ce169cf971fd19691158f7e78edf806`; measured production source SHA-256: `57404f9168a198c9f4398b1cd519f397d3d90e901588e8ecc6469b41af57d203`. All 17 groups exited 0: 32,330 passed, 179 skipped, 0 failures, 0 errors; producer exit 0. Global measured coverage: 99.74% lines and 94.43% branches. Config-root coverage is a fresh 40/40 executable lines and 18/18 branches, including fallback line 32; production config-root behavior is unchanged.

Current accepted inventory contains 2546 paths with no unmeasured/uncovered modules and none below 85%. Canonical nonregressing adoption preserves historical rows. The separate direct raw-candidate comparison failed with 67 remaining module regressions; global fresh measured nonregression is not claimed. Thirteen new paths were measured and adopted. Raw XML, shard hashes/JUnit, raw candidate, baseline copy and retained-row ledger are in the local `reports/quality/proof-or-stop/architecture-coverage-11854-11899/` evidence directory under distinct wave identities.

After this measurement, an explicit UniProt helper re-export preserved its existing API and removed the one introduced strict type diagnostic. The current accepted source-only binding is `3b2e81219500a0aa6a5c796addb7772d66cff70704e8a85a690ad04726693a75`. This later rebind does not relabel the earlier raw measurement; final validation must run on the resulting committed tree. Full strict Mypy remains a failed diagnostic: 108 errors versus 157 in the complete baseline source/scripts snapshot, with zero added diagnostics and 49 removed. It is not reported as a full type-check pass.

### Eight-stage merged/evidence matrix

Every merged commit below is present in this local branch. CLOSED describes the verified child issue state and does not substitute for current contract execution. Their current contracts are included in the full architecture acceptance suite.

| Child | Historical merged SHA | Ancestor of branch | Historical evidence |
| --- | --- | --- | --- |
| [#11846](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11846) | `d311a17e17c52f2f50b9f1020ed5e4181ff75b36` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11846#issuecomment-5946567048); [historical evidence 2](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11846#issuecomment-5948670893) |
| [#11847](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11847) | `8f024f97cb10d87d2d12b31f7a4282aac1cf895c` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11847#issuecomment-5947798826) |
| [#11848](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11848) | `294c90e7210bff8d63d489f6bf3b1e0d76fd8ef2` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11848#issuecomment-5953970678) |
| [#11849](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11849) | `294c90e7210bff8d63d489f6bf3b1e0d76fd8ef2` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11849#issuecomment-5953958374) |
| [#11850](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11850) | `294c90e7210bff8d63d489f6bf3b1e0d76fd8ef2` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11850#issuecomment-5953960202) |
| [#11851](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11851) | `294c90e7210bff8d63d489f6bf3b1e0d76fd8ef2` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11851#issuecomment-5953962311) |
| [#11852](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11852) | `dbc2ee7f257b8f8e7866383e1e05361555faf5de` | yes | [issue record](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11852) |
| [#11853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11853) | `294c90e7210bff8d63d489f6bf3b1e0d76fd8ef2` | yes | [historical evidence 1](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11853#issuecomment-5951017215); [historical evidence 2](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/11853#issuecomment-5953972399) |

### Final acceptance requirements and limits

Run complete `python -m pytest tests/architecture`, the complete 17-group coverage producer, strict docs verification, canonical debt/governance freshness checks and full-tree guard on one final committed tree. Record terminating exits and JUnit, then assemble and verify normalized proof receipts. The initial 133-failure architecture run and interrupted producers remain historical diagnostics, not acceptance. No budgets, thresholds, exemptions or exclusions are increased. All 161 files lost from tracking by the earlier index-isolation defect were restored with their original blobs; the affected temporary-Git fixture and coverage producer now isolate inherited `GIT_*` configuration.

Billing lock remains `CI=BLOCKED_EXTERNAL_PERMANENT`. Local execution is not CI PASS. `local_single_host` evidence can qualify only as DEGRADED under the existing proof policy; required ADMIT cannot be replaced by fabricated independent attestation. Publication/integration and the applicable lifecycle acceptance are separate requirements. Runtime mirror parity is N/A because Codex/Junie runtime sources were unchanged. The original shared checkout and all `.env` files are preserved.
