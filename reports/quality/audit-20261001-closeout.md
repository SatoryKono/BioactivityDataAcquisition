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
