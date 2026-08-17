# TRIAGE — CR-FULL 20260816

Code/config/contracts and executable gates outrank CodeRabbit output.

| id | status | final severity | reason | evidence |
|---|---|---|---|---|
| `CR-20260816-A-S01-domain-aggregates-001` | reject | major | Coverage-inventory refresh treats already-inventoried aggregate modules as new; same class as 20260811-002. | reports/quality/module-coverage-inventory.json; CR-20260811-A-S01-domain-aggregates-002 |
| `CR-20260816-A-S01-domain-aggregates-002` | reject | major | PipelineRun.__init__ nominal and defensive metadata-copy coverage already exists. | tests/unit/domain/aggregates/test_pipeline_run.py |
| `CR-20260816-A-S01-domain-aggregates-003` | reject | major | Adding entry_id to QuarantineEntryCreated is a contract expansion; Created already carries payload_hash and inputs used to derive identity. | src/bioetl/domain/aggregates/events.py QuarantineEntryCreated |
| `CR-20260816-A-S01-domain-aggregates-004` | reject | major | Canonical resolution types are validated on ResolutionInfo; event payload is only emitted as ignored/reprocessed. | src/bioetl/domain/aggregates/_quarantine_value_objects.py; events.py QuarantineEntryResolved |
| `CR-20260816-A-S01-domain-aggregates-005` | reject | major | Synthetic new-export/ADR request; event facade already ships on main under ADR-021. | src/bioetl/domain/aggregates/events.py; ADR-021 |
| `CR-20260816-A-S01-domain-aggregates-006` | reject | major | StageResult.status is already StageStatus; isinstance guard is typing hardening, not a missing invariant. | src/bioetl/domain/aggregates/pipeline_run_stage_result.py |
| `CR-20260816-A-S01-domain-aggregates-007` | reject | major | new_record_id is enforced on mark_reprocessed; VO construction is not the production invariant surface. | src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py mark_reprocessed |
| `CR-20260816-A-S01-domain-aggregates-008` | reject | trivial | Style-only rename of is_resolved; property already means terminal status. | src/bioetl/domain/aggregates/_quarantine_entry_properties_mixin.py |
| `CR-20260816-A-S01-domain-aggregates-009` | reject | trivial | Docstring-only; quarantine_record already uses structural equality. | src/bioetl/domain/aggregates/_batch_mixins.py |
| `CR-20260816-A-S01-domain-aggregates-010` | reject | trivial | Magic-literal extraction; fail() already emits failed_stage='unknown' and is tested. | src/bioetl/domain/aggregates/_pipeline_run_mixins.py fail |
| `CR-20260816-A-S01-domain-aggregates-011` | reject | major | Slots/DRY refactor; QuarantineEntry already declares __slots__. Same class as 20260811-009. | src/bioetl/domain/aggregates/_quarantine_aggregate.py |
| `CR-20260816-A-S01-domain-aggregates-012` | reject | major | Early return is unreachable on the public API: record_stage_failure leaves the run FAILED and a later call is blocked by _assert_running. RUNNING->FAILED replacement already fixed (#8645). | src/bioetl/domain/aggregates/_pipeline_run_mixins.py record_stage_failure |
| `CR-20260816-A-S01-domain-aggregates-013` | reject | trivial | Exception-order style only; empty id and terminal status already fail closed. | src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py mark_reprocessed |
| `CR-20260816-A-S01-domain-aggregates-014` | confirm | major | seal_with_counts accepts external transform counts but mark_committed emits BatchWritten.record_count=self.valid_count, so sealed valid_count is lost. | src/bioetl/domain/aggregates/_batch_mixins.py seal_with_counts, mark_committed |
| `CR-20260816-A-S01-domain-aggregates-015` | reject | major | PD3 host-attr Any pattern is accepted by the Any gate; 20260811-012 rejected the same claim. | src/bioetl/domain/aggregates/_quarantine_entry_properties_mixin.py; tests/architecture/test_any_budget.py |
| `CR-20260816-A-S01-domain-aggregates-016` | reject | major | Documented contract: mark_expired records ResolutionInfo and does not emit QuarantineEntryResolved (only ignored/reprocessed do). | docs/04-reference/domain/aggregate-state-machines.md; _quarantine_entry_transitions_mixin.py mark_expired |
| `CR-20260816-A-S01-domain-aggregates-017` | reject | trivial | BatchID is NewType(UUID); empty-string guard is not a meaningful identity check. | src/bioetl/domain/types/identifiers.py; _batch_aggregate.py open_with_id |
| `CR-20260816-A-S01-domain-behavior-001` | reject | major | UnitConverter nominal/alias/round-trip tests already exist. | tests/unit/domain/services/test_unit_converter.py |
| `CR-20260816-A-S01-domain-behavior-002` | reject | major | validate_activity_value already parses via ActivityType.from_string; percent-with-unit routing from #8643 is fixed. | src/bioetl/domain/behavior/value_validator.py; tests/unit/domain/test_cr_streams_8643_8644_8645.py |
| `CR-20260816-A-S01-domain-behavior-003` | reject | major | UnitConverter already ships on main; no public-API diff requiring release artifacts. | src/bioetl/domain/behavior/unit_converter.py |
| `CR-20260816-A-S01-domain-behavior-004` | reject | major | Test-only request for a thin ValidationResult envelope; no broken contract. | src/bioetl/domain/behavior/validation_result_envelopes.py |
| `CR-20260816-A-S01-domain-behavior-005` | reject | major | validate_data 0/False/None/empty coverage already exists including frozenset. | tests/unit/domain/behavior/test_domain_behavior_cr_residuals_8178_8214.py |
| `CR-20260816-A-S01-domain-behavior-006` | reject | major | Alias and percent bound/non-finite coverage already exists. | tests/unit/domain/behavior/test_value_validator.py |
| `CR-20260816-A-S01-domain-behavior-007` | reject | major | ValueValidator nominal/strict/percent/custom-range tests already exist. | tests/unit/domain/behavior/test_value_validator.py |
| `CR-20260816-A-S01-domain-behavior-008` | confirm | major | Configured molar window is applied only to nM/uM/mM/M; pM and fM keep DEFAULT_CONCENTRATION_RANGES. | src/bioetl/domain/behavior/value_validator.py:57-70 |
| `CR-20260816-A-S01-domain-behavior-009` | reject | trivial | Function-scoped import is style; module-level ValidationError already exists. | src/bioetl/domain/behavior/_dq_rule_evaluators_cross.py |
| `CR-20260816-A-S01-domain-behavior-010` | confirm | minor | Renderer emits status-warn but CSS still styles .status-warning, so warning badges stay unstyled. | src/bioetl/domain/behavior/_dq_serializer_html/_renderers.py; _styles.py:39-41 |
| `CR-20260816-A-S01-domain-behavior-011` | confirm | minor | extract_affiliations_from_authors stringifies list dict items instead of extracting name. | src/bioetl/domain/behavior/_author_helpers.py:279-304 |
| `CR-20260816-A-S01-domain-behavior-012` | reject | trivial | Compile-once regex is a micro-optimization without a correctness hole. | src/bioetl/domain/behavior/_dq_rule_evaluators.py |
| `CR-20260816-A-S01-domain-behavior-013` | reject | major | DRY dedupe of equivalent coerce helpers; no divergent outcome. | src/bioetl/domain/behavior/_dq_rule_evaluators_vocab.py; _dq_value_coercion.py |
| `CR-20260816-A-S01-domain-behavior-014` | reject | minor | Comma-split of author lists is the contracted behavior and is tested. | src/bioetl/domain/behavior/_author_helpers.py parse_delimited_authors |
| `CR-20260816-A-S01-domain-behavior-015` | reject | trivial | Shared hierarchy helper is DRY; predicates already match. | src/bioetl/domain/behavior/_dq_rule_evaluators.py |
| `CR-20260816-A-S01-domain-behavior-016` | reject | minor | observe_until/soft_fail_until are unused public metadata; domain does not consume wall-clock. API change, not a residual fix. | src/bioetl/domain/behavior/staged_enforcement.py |
| `CR-20260816-A-S01-domain-behavior-017` | confirm | minor | set(schema['required']) iterates a scalar string into characters and invents REQUIRED_FIELD diffs. | src/bioetl/domain/behavior/schema_classifier_helpers.py:108-109 |
| `CR-20260816-A-S01-domain-behavior-018` | confirm | major | classify_potency hardcodes 4.0 and 6.0 beside config thresholds, so screening/medicinal-chemistry presets make labels unreachable. | src/bioetl/domain/behavior/normalization_service.py:148-158 |
| `CR-20260816-A-S01-domain-behavior-019` | confirm | minor | Non-mapping properties still reach sorted()/index and raise instead of fail-soft/manual-review. | src/bioetl/domain/behavior/schema_classifier.py; schema_classifier_helpers.py |
| `CR-20260816-A-S01-domain-behavior-020` | reject | major | warning_count=0 matches DQMetricsInput which has no warning-record signal. | src/bioetl/domain/behavior/dq_metrics_calculator.py |
| `CR-20260816-A-S01-domain-behavior-021` | reject | trivial | Unused private report parameter is refactor-only. | src/bioetl/domain/behavior/dq_serializer.py |
| `CR-20260816-A-S01-domain-behavior-022` | reject | minor | Second WARN->QUARANTINE application is a no-op, not a wrong disposition. | src/bioetl/domain/behavior/dq_policy_resolver.py |
| `CR-20260816-A-S01-domain-behavior-023` | confirm | minor | enrichment_rate is still total_enrichments/total_records and can exceed 0-1 when a record has multiple enrichers. | src/bioetl/domain/behavior/merged_metadata_explainability.py |
| `CR-20260816-A-S01-domain-behavior-024` | confirm | major | Frozen explanation VOs still expose caller-mutable lists. | src/bioetl/domain/behavior/merged_metadata_explainability.py MergedFieldExplanation |
| `CR-20260816-A-S01-domain-behavior-025` | reject | major | Current tests treat a present priority_order as priority_based conflict; CR wants a different metric definition. | tests/unit/domain/behavior/test_merged_metadata_explainability.py |
| `CR-20260816-A-S01-domain-behavior-026` | reject | major | Private YAML helpers are live; replacing them with yaml.safe_dump would add infra to domain. | src/bioetl/domain/behavior/dq_serializer.py |
| `CR-20260816-A-S01-domain-behavior-027` | reject | trivial | Unused helper removal is dead-code cleanup. | src/bioetl/domain/behavior/cross_validation_validator.py |
| `CR-20260816-A-S01-domain-behavior-028` | confirm | minor | Pair self-comparisons are skipped without an issue while coverage still counts the source. | src/bioetl/domain/behavior/cross_validation_helpers.py |
| `CR-20260816-A-S01-domain-behavior-029` | reject | major | Memoize policy path is a perf suggestion; outcomes are already identical. | src/bioetl/domain/behavior/dq_rule_evaluator.py |
| `CR-20260816-A-S01-domain-behavior-030` | reject | major | Owner-aware private-import policy allows underscore helpers inside domain.behavior. | tests/architecture/test_private_module_imports.py |
| `CR-20260816-A-S01-domain-behavior-031` | reject | major | threshold_breach/anomaly_signal are accepted unused compatibility parameters, not a wrong disposition. | src/bioetl/domain/behavior/dq_policy_resolver.py |
| `CR-20260816-A-S01-domain-behavior-032` | confirm | major | _build_disposed_issue is not idempotent; a second apply_disposition rewrites already-disposed issues. | src/bioetl/domain/behavior/cross_validation_validator.py _build_disposed_issue |
| `CR-20260816-A-S01-domain-behavior-033` | confirm | minor | Explicit null cross_validation still enters precheck and becomes a blocker, unlike null aggregation. | src/bioetl/domain/behavior/composite_validation_layer.py:149-163 |
| `CR-20260816-A-S01-domain-behavior-034` | reject | trivial | Empty slots on extensions mixin is cleanup without a broken invariant. | src/bioetl/domain/behavior/activity_aggregator/_aggregator.py |
| `CR-20260816-A-S01-domain-behavior-035` | reject | trivial | Shared dict normalizer is DRY; helpers already convert the same way. | src/bioetl/domain/behavior/composite_metadata_helpers.py |
| `CR-20260816-A-S01-domain-behavior-036` | reject | trivial | Provenance contract intentionally encodes record_count as a string. | src/bioetl/domain/behavior/composite_metadata_cv.py |
| `CR-20260816-A-S01-domain-behavior-037` | confirm | minor | Group-key canonicalization still uses repr(value), so dict/list group-by keys are insertion-order dependent. | src/bioetl/domain/behavior/aggregation_validator.py:240-261 |
| `CR-20260816-A-S01-domain-behavior-038` | confirm | minor | `if not existing_fields` treats an empty existing schema as a missing table and suppresses incoming-field drift. | src/bioetl/domain/behavior/dq_metrics_calculator.py:94-95 |
| `CR-20260816-A-S01-domain-behavior-039` | confirm | minor | A present None identifier becomes the string 'None' instead of falling through. | src/bioetl/domain/behavior/merged_metadata_explainability.py:214-219 |
| `CR-20260816-A-S01-domain-behavior-040` | confirm | major | _json_fallback / exception path still hash repr(), which can embed object identities. | src/bioetl/domain/behavior/merged_metadata_explainability.py:222-246 |
| `CR-20260816-A-S01-domain-behavior-041` | reject | major | DQConfig stores override pairs; len(disposition_overrides) is the override count. | src/bioetl/domain/config/dq.py; dq_policy_resolver.py |
| `CR-20260816-A-S01-domain-behavior-042` | reject | minor | ci_integration is already bool with False default; no current producer hole. | src/bioetl/domain/behavior/composite_validation_layer.py:77-83 |
| `CR-20260816-A-S01-domain-behavior-043` | reject | trivial | Storing full duplicate records is a memory cleanup; sample payload is already limited. | src/bioetl/domain/behavior/aggregation_validator.py |
| `CR-20260816-A-S01-domain-behavior-044` | confirm | major | _optional_unit_interval accepts bool (True->1.0) and NaN because isinstance(True, int) and NaN comparisons are false. | src/bioetl/domain/behavior/composite_validation_helpers.py:173-181 |
| `CR-20260816-A-S01-domain-behavior-045` | reject | major | Construct CompositeOutputExt once is a refactor; both branches already produce intended fields. | src/bioetl/domain/behavior/composite_metadata_helpers.py |
| `CR-20260816-A-S01-domain-behavior-046` | reject | trivial | Import placement of dataclasses.replace is style-only. | src/bioetl/domain/behavior/composite_validation_layer.py:90-93 |
| `CR-20260816-A-S01-domain-behavior-047` | reject | trivial | Charge is typed int\|None; bool-as-0/1 guard is style without a demonstrated payload path. | src/bioetl/domain/behavior/chemical_standardization.py |
| `CR-20260816-A-S01-domain-behavior-048` | reject | trivial | list[Any]->list[object] is typing cleanup accepted by the Any gate. | src/bioetl/domain/behavior/author_normalization_service.py |
| `CR-20260816-A-S01-domain-behavior-049` | confirm | minor | Fallback columns/field_names still str()-coerce non-dict objects into fake field names. | src/bioetl/domain/behavior/aggregation_validator.py:174-193 |
| `CR-20260816-A-S01-domain-behavior-050` | reject | trivial | Hoisting the aggregation dispatch map is a micro-optimization. | src/bioetl/domain/behavior/activity_aggregator/_aggregator.py |
| `CR-20260816-A-S01-domain-behavior-051` | confirm | critical | validate_composite always runs deep preflight after structural fail-closed; non-mapping composite_config and untyped output_schema/sources still reach .get/set. | src/bioetl/domain/behavior/composite_validation_layer.py:65-71,133-163 |
| `CR-20260816-A-S01-domain-composite-001` | reject | trivial | Protocol vs concrete type is style; coerce_composite_collections already mutates known dataclass fields. | src/bioetl/domain/composite/config_composite_validation.py |
| `CR-20260816-A-S01-domain-composite-002` | reject | trivial | Export/naming hygiene for private protocols; no runtime invariant failure. | src/bioetl/domain/composite/config_composite_protocols.py |
| `CR-20260816-A-S01-domain-composite-003` | reject | trivial | getattr fallback is defensive protocol typing; method is already coerced to ComparisonMethod. | src/bioetl/domain/composite/config_composite_encoder.py |
| `CR-20260816-A-S01-domain-composite-004` | reject | trivial | Type-tightening around str() in _coerce_text_tuple; empty/duplicate checks already exist. | src/bioetl/domain/composite/aggregation.py |
| `CR-20260816-A-S01-domain-composite-005` | reject | major | Test-only; per-enricher threshold ordering is already enforced and covered. | tests/unit/domain/composite/test_domain_composite_cr_residuals_8220_8240.py |
| `CR-20260816-A-S01-domain-composite-006` | confirm | trivial | Decoder silently str()-coerces non-string field_priorities members into garbage provider names. | src/bioetl/domain/composite/config_composite_decoder.py:113-120 |
| `CR-20260816-A-S01-domain-composite-007` | confirm | minor | bool() on lineage/execution flags fail-opens: any non-empty string including 'false' becomes True. | src/bioetl/domain/composite/config_composite_section_decoders.py |
| `CR-20260816-A-S01-domain-composite-008` | reject | trivial | Test-only grammar matrix; accepted/rejected filter syntax already covered. | tests/unit/domain/composite/test_domain_composite_cr_residuals_8222_8255.py |
| `CR-20260816-A-S01-domain-composite-009` | reject | major | Annotation/type:ignore cleanup; threshold validation already runs. | src/bioetl/domain/composite/config_dq.py |
| `CR-20260816-A-S01-domain-composite-010` | confirm | major | _is_quoted_literal only checks matching start/end quotes, so RHS like 'foo' == 'bar' bypasses nested-operator rejection. | src/bioetl/domain/composite/aggregation_filters.py:27-48 |
| `CR-20260816-A-S01-domain-composite-011` | confirm | major | Present malformed optional sections are silently dropped; only dict values are attached. | src/bioetl/domain/composite/config_composite_decoder.py:177-196 |
| `CR-20260816-A-S01-domain-composite-012` | confirm | major | _validate_null_filter accepts any string containing IS [NOT] NULL and ignores trailing text. | src/bioetl/domain/composite/aggregation_filters.py:19-24 |
| `CR-20260816-A-S01-domain-composite-013` | reject | minor | Count thresholds are already int-parsed and range-checked; remaining annotation tightening is not a silent hole. | src/bioetl/domain/composite/config_cross_validation.py |
| `CR-20260816-A-S01-domain-composite-014` | confirm | minor | Whitespace-only output_field is truthy and becomes effective_output_field. | src/bioetl/domain/composite/aggregation.py:154-163 |
| `CR-20260816-A-S01-domain-composite-015` | reject | trivial | DRY helper extraction; both unique-name checks already reject duplicates. | src/bioetl/domain/composite/config_composite_validation.py |
| `CR-20260816-A-S01-domain-composite-016` | confirm | major | AggregationConfig._validate never rejects colliding effective_output_field values. | src/bioetl/domain/composite/aggregation.py:213-218 |
| `CR-20260816-A-S01-domain-composite-017` | confirm | major | build_cross_validation_config uses bool()/int(str())/float(str()); enabled:'false' fail-opens to True. | src/bioetl/domain/composite/config_composite_section_decoders.py:186-199 |
| `CR-20260816-A-S01-domain-composite-018` | reject | trivial | FromString mixin extraction is DRY; enums already parse and reject invalid values. | src/bioetl/domain/composite/strategy.py |
| `CR-20260816-A-S01-domain-composite-019` | confirm | major | records_enriched > records_merged is allowed when records_merged==0 because of the chained `> 0` guard. Residual of #8644. | src/bioetl/domain/composite/result_merge.py:32-36 |
| `CR-20260816-A-S01-domain-composite-020` | reject | trivial | Two equivalent timeout guards already reject non-finite/negative values. | src/bioetl/domain/composite/result_enrichment.py |
| `CR-20260816-A-S01-domain-composite-021` | reject | trivial | tuple() any-iterable is style; lists are already frozen. | src/bioetl/domain/composite/result_merge.py |
| `CR-20260816-A-S01-domain-composite-022` | reject | trivial | TRASH-as-unmapped-default is the current contract, not a defect. | src/bioetl/domain/composite/field_groups_registry.py |
| `CR-20260816-A-S01-domain-composite-023` | reject | trivial | Redundant freeze_fields call is style; mappings are still frozen. | src/bioetl/domain/composite/config_merge.py |
| `CR-20260816-A-S01-domain-composite-024` | reject | trivial | DRY collapse of ValueError branches; fail-closed already works. | src/bioetl/domain/composite/config_parsing.py |
| `CR-20260816-A-S01-domain-composite-025` | reject | trivial | Import hoisting of Mapping; no behavior change. | src/bioetl/domain/composite/lineage.py |
| `CR-20260816-A-S01-domain-composite-026` | reject | trivial | Completeness assert is defensive style; every state already has transitions and metrics. | src/bioetl/domain/composite/state.py |
| `CR-20260816-A-S01-domain-composite-027` | reject | trivial | Import hoisting of freeze_fields; __post_init__ unchanged. | src/bioetl/domain/composite/config_schema.py |
| `CR-20260816-A-S01-domain-config-001` | confirm | major | TableConfig accepts PARTITION_APPEND_WITH_STABLE_PARTITION_KEY with empty partition_cols. | src/bioetl/domain/config/table.py:71-105 |
| `CR-20260816-A-S01-domain-config-002` | reject | minor | Empty debug_export_formats with enabled=True is the documented default-all-formats path. | src/bioetl/domain/config/runtime.py |
| `CR-20260816-A-S01-domain-config-003` | reject | minor | YAML field_policy is a dict so keys are unique; leftover last-wins on a hand-built tuple is not a current hole. | src/bioetl/infrastructure/schemas/pipeline_config.py |
| `CR-20260816-A-S01-domain-config-004` | reject | trivial | Unreachable TYPE_CHECKING branch is style. | src/bioetl/domain/config/__init__.py |
| `CR-20260816-A-S01-domain-config-005` | reject | minor | Defensive copy/string-element tightening without a demonstrated broken enum invariant. | src/bioetl/domain/config/enum_loader.py |
| `CR-20260816-A-S01-domain-config-006` | reject | trivial | Import hoisting of isfinite; range validation already rejects non-finite values. | src/bioetl/domain/config/validation_config.py |
| `CR-20260816-A-S01-domain-config-007` | reject | minor | Missing CrossFieldValidation variant params already fail closed at evaluation. | src/bioetl/domain/behavior/_dq_rule_evaluators_cross.py |
| `CR-20260816-A-S01-domain-config-008` | reject | trivial | getattr-to-direct-attribute style; positivity checks already run. | src/bioetl/domain/config/validation_config.py |
| `CR-20260816-A-S01-domain-config-009` | reject | trivial | freeze_sequences list-only handling is style; config fields are lists/tuples. | src/bioetl/domain/config/_converters.py |
| `CR-20260816-A-S01-domain-config-010` | reject | major | Claim is false: in/not_in wrap a bare string as a one-element option, so matching is exact membership, not substring. | src/bioetl/domain/behavior/_dq_condition_matchers.py:23-40 |
| `CR-20260816-A-S01-domain-config-011` | reject | trivial | Replay uses date.fromisoformat(); non-canonical-but-parseable forms do not break date identity. | src/bioetl/domain/config/runtime.py |
| `CR-20260816-A-S01-domain-config-012` | reject | major | Already shipped: pyproject.toml requires-python >=3.12. | pyproject.toml:10 |
| `CR-20260816-A-S01-domain-config-013` | reject | major | Already-fixed dual-shape contract: DQConfig stores immutable pairs; invalid dispositions fail closed. | src/bioetl/domain/config/dq.py; tests/unit/domain/test_cr_stream_8644_domain_other.py |
| `CR-20260816-A-S01-domain-contracts-001` | reject | major | Test-only; alias/required-field coverage already exists for StrictGold and public Gold schemas. | tests/unit/domain/contracts/gold; tests/contract/gold_schemas |
| `CR-20260816-A-S01-domain-contracts-002` | confirm | major | Docstring requires 16-char SHA-256 entity_id and CHEMBL example_assay_id, but fields have no format checks unlike nearby tissue_id. | src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py |
| `CR-20260816-A-S01-domain-contracts-003` | reject | major | Coverage-inventory refresh is not an invariant hole. | src/bioetl/domain/contracts/gold/_base.py |
| `CR-20260816-A-S01-domain-contracts-004` | reject | major | ADR/version-bump for already-shipped public Gold schemas plus test-only ask. | src/bioetl/domain/contracts/gold/composite.py; tests/contract/gold_schemas |
| `CR-20260816-A-S01-domain-contracts-005` | confirm | major | pub_month/pub_day are coerced floats with only ge/le bounds, so 1.5 and 30.5 validate. | src/bioetl/domain/contracts/gold/publications_pubmed.py:37-38 |
| `CR-20260816-A-S01-domain-contracts-006` | confirm | major | top_level_count is a coerced float with only ge=0, so fractional counts are accepted. | src/bioetl/domain/contracts/gold/composite_bioassay.py:184-188 |
| `CR-20260816-A-S01-domain-control_plane-001` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-002` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-003` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-004` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-005` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-006` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-007` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-008` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-009` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-010` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-011` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-012` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-013` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-014` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-015` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-016` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-017` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-018` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-019` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-020` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-021` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-022` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-023` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-024` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-025` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-026` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-027` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-028` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-029` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-030` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-031` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-032` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-033` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-034` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-035` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-036` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-037` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-038` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-039` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-040` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-041` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-042` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-control_plane-043` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-001` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-002` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-003` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-004` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-005` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-006` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-007` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-008` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-009` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-010` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-011` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-012` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-013` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-014` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-015` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-016` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-017` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-entities-018` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-001` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-002` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-003` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-004` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-005` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-006` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-007` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-008` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-009` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-010` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-011` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-012` | pending | minor | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-013` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-014` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-015` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-016` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-017` | pending | critical | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-018` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-019` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-020` | pending | major | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-021` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-022` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-023` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-024` | pending | trivial | pending ground-truth reconciliation |  |
| `CR-20260816-A-S01-domain-exceptions-025` | pending | major | pending ground-truth reconciliation |  |

| CR-20260816-A-S01-domain-types-018 | confirm | critical | _normalize_semver pads with a single .0, so "1" becomes "1.0" and "1.2.3.4" becomes "1.2.3.4.0"; rom_legacy(..., "1") fails validate(). | src/bioetl/domain/types/contract_identity.py; #8893 |
| CR-20260816-A-S01-domain-types-022 | confirm | critical | ContractRolloutPolicy single-mode defaults 
ead_order/write_versions=() fail __post_init__ (ctive_version must be present in read_order). | src/bioetl/domain/types/contract_rollout.py; #8893 |

| CR-20260816-A-S01-domain-types-001 | reject | trivial | Stale Any comment; field is already JsonDict \| None. | docstring |
| CR-20260816-A-S01-domain-types-002 | reject | trivial | StrEnum/Literal for debug status/formats is an API expansion. | debug_export.py |
| CR-20260816-A-S01-domain-types-003 | reject | trivial | Literal resume_verdict is typing/API tightening, not a broken invariant. | checkpoint_compatibility_result.py |
| CR-20260816-A-S01-domain-types-004 | confirm | major | incompatible_result defaults identity_continuity_proven=True. | #8895 |
| CR-20260816-A-S01-domain-types-005 | reject | trivial | Extra dual_read/dual_write cardinality rules are a new policy, not the shipped contract. | contract_rollout.py |
| CR-20260816-A-S01-domain-types-006 | reject | trivial | Unconstrained severity string is the shipped API; enum swap is expansion. | dq_contracts.py |
| CR-20260816-A-S01-domain-types-007 | reject | minor | Whitespace-padded versions already fail membership; current path is fail-closed. | contract_rollout.py |
| CR-20260816-A-S01-domain-types-008 | reject | major | DRY consolidate of coerce helpers; no divergent outcome. | _checkpoint_metadata_support.py |
| CR-20260816-A-S01-domain-types-009 | reject | major | Transition lookup is phase-scoped; WRITE_TO_SUCCESS from CROSS_VALIDATION is an explicit degraded rule. | _execution_phase_transition_builders.py |
| CR-20260816-A-S01-domain-types-010 | confirm | major | ids-only fingerprint is None; equivalent refs hash. | #8895 |
| CR-20260816-A-S01-domain-types-011 | confirm | minor | coerce_snapshot_ids stringifies None/int into fake ids. | #8895 |
| CR-20260816-A-S01-domain-types-012 | confirm | minor | invoke_to_schema swallows ValueError from a valid to_schema(). | #8895 |
| CR-20260816-A-S01-domain-types-013 | confirm | minor | Empty/dot-only contract_ref validates; from_legacy('') -> .v1.0.0. | #8895 |
| CR-20260816-A-S01-domain-types-014 | confirm | minor | coerce_mapping returns a mutable dict. | #8895 |
| CR-20260816-A-S01-domain-types-015 | confirm | minor | _extract_with_fallback returns raw unstripped / non-string values. | #8895 |
| CR-20260816-A-S01-domain-types-016 | confirm | major | messages list on frozen VO is mutable and unhashable. | #8895 |
| CR-20260816-A-S01-domain-types-017 | confirm | major | affected_fields list on frozen VO is mutable and unhashable. | #8895 |
| CR-20260816-A-S01-domain-types-019 | confirm | major | DebugExportPack nested dicts stay mutable; pack is unhashable. | #8895 |
| CR-20260816-A-S01-domain-types-020 | reject | major | Unreachable TYPE_CHECKING / pragma is coverage style. | types/__init__.py |
| CR-20260816-A-S01-domain-types-021 | reject | major | DRY consolidate of from_legacy/from_dict constructors. | checkpoint_metadata.py |
| CR-20260816-A-S01-domain-types-023 | confirm | major | records_processed is not coerced; '10' stays str, None stays None. | #8895 |
| CR-20260816-A-S01-domain-types-024 | reject | trivial | Whitespace normalize-only; membership already fail-closes mismatches. | gold_schema_policy.py |
| CR-20260816-A-S01-domain-types-025 | reject | trivial | DRY generator for get_all_* accessors. | validation_result.py |
| CR-20260816-A-S01-domain-types-026 | confirm | minor | Inverted numeric min>max is accepted. | #8895 |
| CR-20260816-A-S01-domain-types-027 | reject | trivial | DRY from_mapping vs __post_init__ normalization. | gold_contracts_rules.py |
| CR-20260816-A-S01-domain-types-028 | confirm | minor | bool is accepted as SCD type because bool is an int. | #8895 |
| CR-20260816-A-S01-domain-types-029 | reject | trivial | CompositeFSM is a mutable state machine; history is internal state. | execution_phase.py |
| CR-20260816-A-S01-domain-types-030 | reject | minor | Required-before-reference is the shipped heuristic; CR wants a different order. | gold_contracts_rejects.py |
| CR-20260816-A-S01-domain-types-031 | reject | trivial | cls() vs explicit class name is subclass style. | schema_policy.py |
| CR-20260816-A-S01-domain-types-032 | reject | trivial | DRY shared transition lookup. | execution_phase.py |
| CR-20260816-A-S01-domain-types-033 | reject | major | Protocol-only runtime_checkable complaint. | identifiers.py |
| CR-20260816-A-S01-domain-types-034 | reject | trivial | Current CMP-RT blockers except SHADOW are already listed. | validation_severity.py |
| CR-20260816-A-S01-domain-types-035 | reject | trivial | Terminal phases do not overlap explicit table keys; no overwrite. | execution_phase_transitions.py |
| CR-20260816-A-S01-domain-types-036 | reject | trivial | Literal annotation only. | gold_contracts_rejects.py |

| CR-20260816-A-S01-domain-value_objects-001 | reject | - | inventory-hash-only |  |
| CR-20260816-A-S01-domain-value_objects-002 | reject | - | test-only facade coverage |  |
| CR-20260816-A-S01-domain-value_objects-003 | confirm | - | Concentration unit not validated as enum | #8905 |
| CR-20260816-A-S01-domain-value_objects-004 | confirm | - | from_string accepts trailing garbage | #8905 |
| CR-20260816-A-S01-domain-value_objects-005 | confirm | - | MolecularWeight(True) coerced via float | #8905 |
| CR-20260816-A-S01-domain-value_objects-006 | confirm | - | year 2000 century is 21 | #8905 |
| CR-20260816-A-S01-domain-value_objects-007 | confirm | - | 2024-99-99 parsed as 2024 | #8905 |
| CR-20260816-A-S01-domain-value_objects-008 | reject | - | UTC-offset requirement is contract expansion; naive already rejected |  |
| CR-20260816-A-S01-domain-value_objects-009 | reject | - | test-only SilverWriteResult |  |
| CR-20260816-A-S01-domain-value_objects-010 | reject | - | test-only PublicationFieldGroup |  |
| CR-20260816-A-S01-domain-value_objects-011 | confirm | - | PChemblValue accepts NaN | #8905 |
| CR-20260816-A-S01-domain-value_objects-012 | reject | - | path already validated; list freeze is style |  |
| CR-20260816-A-S01-domain-value_objects-013 | reject | - | test-only TaxonomyId |  |
| CR-20260816-A-S01-domain-value_objects-014 | reject | - | test-only DOI/PMID |  |
| CR-20260816-A-S01-domain-value_objects-015 | reject | - | inventory-hash-only |  |
| CR-20260816-A-S01-domain-value_objects-016 | reject | - | test-only ORCID |  |
| CR-20260816-A-S01-domain-value_objects-017 | reject | - | test-only DQ report result VOs |  |
| CR-20260816-A-S01-domain-value_objects-018 | confirm | - | _coerce_int truncates 1.9 | #8905 |
| CR-20260816-A-S01-domain-value_objects-019 | confirm | - | format_utc accepts naive datetime | #8905 |
| CR-20260816-A-S01-domain-value_objects-020 | confirm | - | PubChemCid.from_raw(True) -> 1 | #8905 |
| CR-20260816-A-S01-domain-value_objects-021 | confirm | - | InChI=1/ accepted | #8905 |
| CR-20260816-A-S01-domain-value_objects-022 | confirm | - | DQ timestamp allows non-UTC offset | #8905 |
| CR-20260816-A-S01-domain-value_objects-023 | confirm | - | SchemaSnapshotResult.schema mutable | #8905 |
| CR-20260816-A-S01-domain-value_objects-024 | confirm | - | DQResult.error_rate accepts NaN/1.5 | #8905 |
| CR-20260816-A-S01-domain-value_objects-025 | reject | - | redundant lower() style |  |
| CR-20260816-A-S01-domain-value_objects-026 | reject | - | compression_ratio inf is API change |  |
| CR-20260816-A-S01-domain-value_objects-027 | reject | - | exception-message style |  |
| CR-20260816-A-S01-domain-value_objects-028 | confirm | - | ColumnOrderConfig.field_groups mutable | #8905 |
| CR-20260816-A-S01-domain-value_objects-029 | confirm | - | error_records can exceed total_records | #8905 |
| CR-20260816-A-S01-domain-value_objects-030 | reject | - | set hashing is DRY/robustness without current producer |  |
| CR-20260816-A-S01-domain-value_objects-031 | confirm | - | extract_field drops dotted tails | #8905 |
| CR-20260816-A-S01-domain-value_objects-032 | reject | - | enum vs str style |  |
| CR-20260816-A-S01-domain-value_objects-033 | confirm | - | calculate_null_rate(total=0) ZeroDivisionError | #8905 |
| CR-20260816-A-S01-domain-value_objects-034 | reject | - | docstring Raises |  |
| CR-20260816-A-S01-domain-value_objects-035 | reject | - | docstring Raises |  |
| CR-20260816-A-S01-domain-value_objects-036 | reject | - | AssayId slots refactor |  |
| CR-20260816-A-S01-domain-value_objects-037 | reject | - | type annotation only; already MappingProxyType |  |
| CR-20260816-A-S01-domain-value_objects-038 | reject | - | comment wording |  |
| CR-20260816-A-S01-domain-value_objects-039 | confirm | - | ActivityType.from_string(None) AttributeError | #8905 |
| CR-20260816-A-S01-domain-value_objects-040 | reject | - | eq/hash subclass asymmetry without demonstrated producer |  |
| CR-20260816-A-S01-domain-value_objects-041 | reject | - | docstring KI membership |  |
| CR-20260816-A-S01-domain-schemas-001 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-002 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-003 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-004 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-005 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-006 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-007 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-008 | confirm | - | ISO date regex accepts Feb 30 | #8905 |
| CR-20260816-A-S01-domain-schemas-009 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-010 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-011 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-012 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-013 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-014 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-015 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-016 | reject | - | requiring UTC on ingestion_ts breaks shipped fixtures; regex already optional-TZ |  |
| CR-20260816-A-S01-domain-schemas-017 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-018 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-019 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-020 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-021 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-022 | confirm | - | duplicate column names silently dropped | #8905 |
| CR-20260816-A-S01-domain-schemas-023 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-024 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-025 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-026 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-027 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-028 | confirm | - | pd.isna on list/ndarray raises | #8905 |
| CR-20260816-A-S01-domain-schemas-029 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-030 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-031 | confirm | - | accession alternation is not full-match grouped | #8905 |
| CR-20260816-A-S01-domain-schemas-032 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-033 | confirm | - | str_matches_pattern is prefix match | #8905 |
| CR-20260816-A-S01-domain-schemas-034 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-035 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-036 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-037 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-038 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-039 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-040 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
| CR-20260816-A-S01-domain-schemas-041 | confirm | - | heavy_atom_count rejects 0 | #8905 |
| CR-20260816-A-S01-domain-schemas-042 | reject | - | style/DRY/test-only/docstring/unique-constraint or catalog expansion/shipped API |  |
