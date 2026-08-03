# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import pytest

from scripts.memory.query import (
    _claim_trace_statement,
    _cli_semantics_statement,
    _current_cycle_code_statement,
    _dead_code_candidates_statement,
    _docs_drift_statement,
    _field_lineage_statement,
    _fallback_pipelines_statement,
    _normalization_pipeline_statement,
    _overengineered_candidates_statement,
    _removable_complexity_statement,
    _run_artifacts_statement,
    _runtime_state_statement,
    _schema_drift_statement,
    _simplification_blockers_statement,
    _storage_lineage_statement,
    _workflow_artifacts_statement,
    _workflow_execution_statement,
    _workflow_gates_statement,
    QUERY_PROFILES,
    _duplication_cluster_statement,
    _format_rows,
    _neighbors_statement,
    _ownership_statement,
    _promotion_candidates_statement,
)

pytestmark = pytest.mark.memory

RUN_MANIFEST_LEDGER_DOC_PATH = "docs/04-reference/contracts/run-manifest-ledger.md"
RUN_MANIFEST_MODULE_PATH = "src/bioetl/domain/control_plane/run_manifest.py"
RUN_MANIFEST_LEDGER_DOC_CLAIM = f"{RUN_MANIFEST_LEDGER_DOC_PATH}#L24"
CHEMBL_ACTIVITY_CONFIG_PATH = "configs/entities/chembl/activity.yaml"
CHEMBL_ACTIVITY_PIPELINE = "chembl_activity"
PIPELINE_SURFACE = "pipeline_surface"
MODULE_SURFACE = "module_surface"
SILVER_CHEMBL_ACTIVITY = "silver/chembl/activity"
ADAPTER_LAYER = "adapter_layer"
MISSING_FAMILY = "missing-family"
RECORD_NORMALIZATION_PROCESSOR_PATH = (
    "src/bioetl/application/core/record_normalization_processor.py"
)
CHEMBL_ACTIVITY_CONTRACT = "chembl.activity"
CONTRACT_SURFACE = "contract_surface"
SILVER_CHEMBL_ASSAY = "silver/chembl/assay"
MANIFEST_CHAIN_SMOKE = "manifest-chain-smoke"
COMPOSITE_LAYER = "composite_layer"
RUNTIME_ANCHOR_COUNT = "runtime_anchor_count"
CONFIG_ANCHOR_COUNT = "config_anchor_count"
DOC_ANCHOR_COUNT = "doc_anchor_count"
TEST_ANCHOR_COUNT = "test_anchor_count"
STORAGE_LINEAGE_MODE = "storage-lineage"
DUPLICATION_CLUSTER_MODE = "duplication-cluster"
PROMOTION_CANDIDATES_MODE = "promotion-candidates"
DEAD_CODE_CANDIDATES_MODE = "dead-code-candidates"
CURRENT_CYCLE_CODE_MODE = "current-cycle-code"
OVERENGINEERED_CANDIDATES_MODE = "overengineered-candidates"
REMOVABLE_COMPLEXITY_MODE = "removable-complexity"
SIMPLIFICATION_BLOCKERS_MODE = "simplification-blockers"


def test_query_profiles_cover_operator_shortcuts() -> None:
    assert QUERY_PROFILES["owner-contract"]["target_label"] == CONTRACT_SURFACE
    assert QUERY_PROFILES["owner-doc"]["target_label"] == "doc_source_surface"
    assert QUERY_PROFILES["owner-doc-artifact"]["target_label"] == "doc_artifact"
    assert QUERY_PROFILES["owner-pipeline"]["target_label"] == PIPELINE_SURFACE
    assert QUERY_PROFILES["owner-alert"]["target_label"] == "alert_surface"
    assert QUERY_PROFILES["owner-storage"]["target_label"] == "storage_surface"
    assert (
        QUERY_PROFILES["owner-runtime-evidence"]["target_label"]
        == "runtime_evidence_surface"
    )
    assert (
        QUERY_PROFILES["owner-runtime-state"]["target_label"] == "runtime_state_surface"
    )
    assert QUERY_PROFILES["owner-workflow"]["target_label"] == "workflow_surface"
    assert (
        QUERY_PROFILES["owner-workflow-job"]["target_label"] == "workflow_job_surface"
    )
    assert (
        QUERY_PROFILES["owner-workflow-call"]["target_label"] == "workflow_call_surface"
    )
    assert (
        QUERY_PROFILES["owner-workflow-output"]["target_label"]
        == "workflow_output_surface"
    )
    assert QUERY_PROFILES["owner-cli-command"]["target_label"] == "cli_command_surface"
    assert QUERY_PROFILES["owner-cli-option"]["target_label"] == "cli_option_surface"
    assert (
        QUERY_PROFILES["owner-schema-field"]["target_label"] == "schema_field_surface"
    )
    assert QUERY_PROFILES["neighbors-pipeline"]["mode"] == "neighbors"
    assert QUERY_PROFILES["neighbors-alert"]["target_label"] == "alert_surface"
    assert QUERY_PROFILES["neighbors-storage"]["relation_types"] == (
        "WRITES_TO",
        "PROMOTES_TO",
        "DEPENDS_ON",
        "DEFINED_BY",
    )
    assert (
        QUERY_PROFILES["neighbors-runtime-evidence"]["target_label"]
        == "runtime_evidence_surface"
    )
    assert (
        QUERY_PROFILES["neighbors-runtime-state"]["target_label"]
        == "runtime_state_surface"
    )
    assert QUERY_PROFILES["neighbors-workflow"]["target_label"] == "workflow_surface"
    assert (
        QUERY_PROFILES["neighbors-workflow-job"]["target_label"]
        == "workflow_job_surface"
    )
    assert (
        QUERY_PROFILES["neighbors-run-instance"]["target_label"]
        == "run_instance_surface"
    )
    assert (
        QUERY_PROFILES["neighbors-cli-command"]["target_label"] == "cli_command_surface"
    )
    assert QUERY_PROFILES["docs-drift"]["mode"] == "docs_drift"
    assert QUERY_PROFILES["workflow-gates"]["mode"] == "workflow_gates"
    assert QUERY_PROFILES["workflow-artifacts"]["mode"] == "workflow_artifacts"
    assert QUERY_PROFILES["workflow-execution"]["mode"] == "workflow_execution"
    assert QUERY_PROFILES[STORAGE_LINEAGE_MODE]["mode"] == "storage_lineage"
    assert QUERY_PROFILES["field-lineage"]["mode"] == "field_lineage"
    assert QUERY_PROFILES["schema-drift"]["mode"] == "schema_drift"
    assert QUERY_PROFILES["run-artifacts"]["mode"] == "run_artifacts"
    assert QUERY_PROFILES["runtime-state"]["mode"] == "runtime_state"
    assert QUERY_PROFILES["runtime-locks"]["mode"] == "runtime_locks"
    assert QUERY_PROFILES["claim-trace"]["mode"] == "claim_trace"
    assert QUERY_PROFILES["cli-semantics"]["mode"] == "cli_semantics"
    assert QUERY_PROFILES["normalization-pipeline"]["mode"] == "normalization_pipeline"
    assert QUERY_PROFILES["fallback-pipelines"]["mode"] == "fallback_pipelines"
    assert (
        QUERY_PROFILES[DUPLICATION_CLUSTER_MODE]["target_label"]
        == "duplication_cluster"
    )
    assert QUERY_PROFILES[PROMOTION_CANDIDATES_MODE]["mode"] == "promotion_candidates"
    assert (
        QUERY_PROFILES[DEAD_CODE_CANDIDATES_MODE]["target_label"]
        == "retirement_candidate"
    )
    assert QUERY_PROFILES[CURRENT_CYCLE_CODE_MODE]["mode"] == "current_cycle_code"
    assert (
        QUERY_PROFILES[OVERENGINEERED_CANDIDATES_MODE]["target_label"]
        == "complexity_candidate"
    )
    assert QUERY_PROFILES[REMOVABLE_COMPLEXITY_MODE]["mode"] == "removable_complexity"
    assert (
        QUERY_PROFILES[SIMPLIFICATION_BLOCKERS_MODE]["mode"]
        == "simplification_blockers"
    )


def test_ownership_statement_uses_target_label_and_directory_houses_edges() -> None:
    statement = _ownership_statement()

    assert "target_label = $target_label" in statement
    assert "(owner:directory_surface)-[houses:HOUSES]->(target)" in statement
    assert "(zone:repo_zone)-[:CONTAINS*1..8]->(owner)" in statement
    assert "parent_directory" not in statement


def test_neighbors_statement_uses_relation_filter_and_bidirectional_search() -> None:
    statement = _neighbors_statement()

    assert "target_label = $target_label" in statement
    assert "type(rel) IN $relation_types" in statement
    assert "MATCH (target)-[rel]->(neighbor)" in statement
    assert "MATCH (neighbor)-[rel]->(target)" in statement
    assert "direction" in statement


def test_docs_drift_statement_matches_doc_like_surfaces_and_describes_edges() -> None:
    statement = _docs_drift_statement()

    assert "MATCH (doc)-[rel:DESCRIBES]->(target)" in statement
    assert (
        "labels(doc) WHERE label IN ['doc_source_surface', 'doc_artifact', 'policy_surface']"
        in statement
    )
    assert "$name = 'all' OR doc.name = $name OR target.name = $name" in statement
    assert "coalesce(rel.evidence_kind, '') AS evidence_kind" in statement
    assert "coalesce(rel.section_title, '') AS section_title" in statement


def test_workflow_gates_statement_collects_gates_and_run_targets() -> None:
    statement = _workflow_gates_statement()

    assert "MATCH (workflow:workflow_surface)" in statement
    assert "(workflow)-[:CONTAINS]->(job:workflow_job_surface)" in statement
    assert "(job)-[:EXECUTES_GATE]->(gate:quality_gate)" in statement
    assert "(job)-[:RUNS_VIA]->(target)" in statement


def test_workflow_artifacts_statement_collects_actions_artifacts_and_secrets() -> None:
    statement = _workflow_artifacts_statement()

    assert "MATCH (workflow:workflow_surface)" in statement
    assert "(job)-[:USES_ACTION]->(action:workflow_action_surface)" in statement
    assert (
        "(job)-[artifact_rel:PUBLISHES_ARTIFACT|DEPENDS_ON]->(artifact:workflow_artifact_surface)"
        in statement
    )
    assert "(job)-[:REQUIRES_SECRET]->(secret:workflow_secret_surface)" in statement


def test_workflow_execution_statement_collects_calls_variants_and_outputs() -> None:
    statement = _workflow_execution_statement()

    assert "MATCH (workflow:workflow_surface)" in statement
    assert "[:CALLS_WORKFLOW]->(workflow_call:workflow_call_surface)" in statement
    assert "[:CALLS_WORKFLOW]->(job_call:workflow_call_surface)" in statement
    assert (
        "(job)-[:HAS_MATRIX_VARIANT]->(variant:workflow_matrix_variant_surface)"
        in statement
    )
    assert (
        "(workflow)-[:EMITS_OUTPUT]->(workflow_output:workflow_output_surface)"
        in statement
    )
    assert "(job)-[:EMITS_OUTPUT]->(job_output:workflow_output_surface)" in statement


def test_storage_lineage_statement_collects_producers_and_promotions() -> None:
    statement = _storage_lineage_statement()

    assert "MATCH (storage:storage_surface)" in statement
    assert "(producer)-[:WRITES_TO]->(storage)" in statement
    assert "(storage)-[:PROMOTES_TO]->(downstream:storage_surface)" in statement
    assert "(upstream:storage_surface)-[:PROMOTES_TO]->(storage)" in statement
    assert "(storage)-[:DEFINED_BY]->(config)" in statement
    assert "storage.storage_roles AS storage_roles" in statement
    assert "storage.partition_by AS partition_by" in statement
    assert "storage.versioning_mode AS versioning_mode" in statement


def test_field_lineage_statement_collects_schema_fields_and_lineage_edges() -> None:
    statement = _field_lineage_statement()

    assert "MATCH (field:schema_field_surface)" in statement
    assert "(storage:storage_surface)-[:HAS_SCHEMA_FIELD]->(field)" in statement
    assert "(field)-[:DERIVES_FIELD_FROM]->(upstream:schema_field_surface)" in statement
    assert (
        "(field)-[:PROMOTES_FIELD_TO]->(downstream:schema_field_surface)" in statement
    )


def test_schema_drift_statement_filters_field_level_drift() -> None:
    statement = _schema_drift_statement()

    assert "MATCH (field:schema_field_surface)" in statement
    assert "coalesce(field.drift_classification, '') <> ''" in statement
    assert "field.storage_ref = $name" in statement


def test_run_artifacts_statement_collects_artifacts_dependencies_and_support_links() -> (
    None
):
    statement = _run_artifacts_statement()

    assert "MATCH (run:run_instance_surface)" in statement
    assert (
        "$name = 'all' OR run.name = $name OR run.manifest_id = $name OR run.run_id = $name"
        in statement
    )
    assert (
        "(run)-[:REFERENCES_ARTIFACT]->(artifact:control_plane_artifact_surface)"
        in statement
    )
    assert "(run)-[:DEPENDS_ON]->(dependency)" in statement
    assert "(run)-[:DESCRIBED_IN]->(support)" in statement


def test_runtime_state_statement_collects_runtime_states_and_locks() -> None:
    statement = _runtime_state_statement()
    locks_statement = _runtime_state_statement(locks_only=True)

    assert "MATCH (state:runtime_state_surface)" in statement
    assert "(owner)-[:HAS_RUNTIME_STATE]->(state)" in statement
    assert (
        "(state)-[:REFERENCES_ARTIFACT]->(artifact:control_plane_artifact_surface)"
        in statement
    )
    assert "state.state_kind = 'lock_state'" in locks_statement


def test_claim_trace_statement_collects_claims_and_targets() -> None:
    statement = _claim_trace_statement()

    assert "MATCH (doc)-[:ASSERTS]->(claim:doc_claim_surface)" in statement
    assert "(claim)-[:ASSERTS_ABOUT]->(target)" in statement
    assert "coalesce(claim.claim_text, '') AS claim_text" in statement
    assert "ORDER BY doc_name ASC, line_number ASC" in statement


def test_cli_semantics_statement_collects_options_and_side_effects() -> None:
    statement = _cli_semantics_statement()

    assert "MATCH (command:cli_command_surface)" in statement
    assert "(command)-[:ACCEPTS_OPTION]->(option:cli_option_surface)" in statement
    assert "(command)-[:SIDE_EFFECTS_ON]->(target)" in statement


def test_duplication_cluster_statement_uses_cluster_targets_members_and_tests() -> None:
    statement = _duplication_cluster_statement()

    assert "MATCH (cluster:duplication_cluster {name: $name})" in statement
    assert "(cluster)-[:CAN_PROMOTE_TO]->(target)" in statement
    assert "(cluster)-[:CONTAINS]->(direct_member)" in statement
    assert "cluster.surface_kind IN labels(fallback)" in statement
    assert (
        "coalesce(fallback.ast_shape_hash, '') = coalesce(cluster.ast_shape_hash, '')"
        in statement
    )
    assert "(cluster)-[:COVERED_BY_TEST]->(direct_test)" in statement
    assert "[:TESTS_PACKAGE_FAMILY]->(family:package_family" in statement
    assert "collect(DISTINCT" in statement


def test_normalization_pipeline_statement_surfaces_profile_and_fallback_metrics() -> (
    None
):
    statement = _normalization_pipeline_statement()

    assert "MATCH (pipeline:pipeline_surface {name: $name})" in statement
    assert (
        "pipeline.normalization_profile_registered AS normalization_profile_registered"
        in statement
    )
    assert (
        "pipeline.fallback_business_field_count AS fallback_business_field_count"
        in statement
    )
    assert "collect(DISTINCT module.name) AS normalization_modules" in statement


def test_fallback_pipelines_statement_orders_by_fallback_business_count() -> None:
    statement = _fallback_pipelines_statement()

    assert "coalesce(pipeline.fallback_business_field_count, 0) > 0" in statement
    assert "$name = 'all' OR pipeline.name = $name" in statement
    assert "ORDER BY pipeline.fallback_business_field_count DESC" in statement


def test_promotion_candidates_statement_filters_by_family_and_orders_by_score() -> None:
    statement = _promotion_candidates_statement()

    assert "MATCH (cluster:duplication_cluster)" in statement
    assert "$name = 'all' OR cluster.family_name = $name" in statement
    assert "(cluster)-[:CONTAINS]->(direct_member)" in statement
    assert "size(members) AS member_count" in statement
    assert "size(tests) AS test_count" in statement
    assert (
        "ORDER BY cluster.promotion_score DESC, cluster.duplicate_count DESC"
        in statement
    )


def test_dead_code_candidates_statement_filters_family_and_blockers() -> None:
    statement = _dead_code_candidates_statement()

    assert "MATCH (candidate:retirement_candidate)" in statement
    assert (
        "$name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name"
        in statement
    )
    assert "(candidate)-[:CANDIDATE_FOR_REMOVAL]->(target)" in statement
    assert (
        "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle"
        in statement
    )
    assert "ORDER BY candidate.deletion_score DESC" in statement


def test_current_cycle_code_statement_filters_family_and_targets() -> None:
    statement = _current_cycle_code_statement()

    assert "MATCH (target)" in statement
    assert "coalesce(target.current_cycle_status, '') <> ''" in statement
    assert (
        "$name = 'all' OR target.family_name = $name OR target.name = $name"
        in statement
    )
    assert "ORDER BY target.current_cycle_score DESC" in statement


def test_overengineered_candidates_statement_filters_family_and_complexity_scores() -> (
    None
):
    statement = _overengineered_candidates_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert (
        "$name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name"
        in statement
    )
    assert "(candidate)-[:CANDIDATE_FOR_SIMPLIFICATION]->(target)" in statement
    assert (
        "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle"
        in statement
    )
    assert "ORDER BY candidate.simplification_score DESC" in statement


def test_removable_complexity_statement_filters_classification() -> None:
    statement = _removable_complexity_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert "candidate.classification = 'removable_complexity'" in statement
    assert "(candidate)-[:CANDIDATE_FOR_REMOVAL]->(target)" in statement
    assert "ORDER BY candidate.removable_score DESC" in statement


def test_simplification_blockers_statement_collects_cycles_and_blockers() -> None:
    statement = _simplification_blockers_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert "[rel:JUSTIFIED_BY_RUNTIME|BLOCKED_BY_VARIANCE]" in statement
    assert (
        "[candidate.blocked_by_current_cycle_target_name] AS cycle_blockers"
        in statement
    )


def test_format_rows_renders_operator_summary() -> None:
    formatted = _format_rows(
        "owner-contract",
        CHEMBL_ACTIVITY_CONTRACT,
        [
            {
                "target_name": CHEMBL_ACTIVITY_CONTRACT,
                "target_label": CONTRACT_SURFACE,
                "owner_directory": "configs/contracts/chembl",
                "repo_zone": "configs",
                "provenance": "file_structure_inferred",
            }
        ],
    )

    assert f"Contract ownership path: `{CHEMBL_ACTIVITY_CONTRACT}`" in formatted
    assert "zone=configs | owner=configs/contracts/chembl" in formatted
    assert "provenance=file_structure_inferred" in formatted


def test_format_rows_renders_neighbors_summary() -> None:
    formatted = _format_rows(
        "neighbors-pipeline",
        CHEMBL_ACTIVITY_PIPELINE,
        [
            {
                "target_name": CHEMBL_ACTIVITY_PIPELINE,
                "target_label": PIPELINE_SURFACE,
                "direction": "outgoing",
                "relation_type": "DEPENDS_ON",
                "neighbor_name": CHEMBL_ACTIVITY_CONTRACT,
                "neighbor_labels": [CONTRACT_SURFACE],
            }
        ],
    )

    assert f"Pipeline semantic neighborhood: `{CHEMBL_ACTIVITY_PIPELINE}`" in formatted
    assert (
        f"direction=outgoing | relation=DEPENDS_ON | neighbor={CHEMBL_ACTIVITY_CONTRACT}"
        in formatted
    )
    assert f"labels={CONTRACT_SURFACE}" in formatted


def test_format_rows_renders_docs_drift_summary() -> None:
    formatted = _format_rows(
        "docs-drift",
        "all",
        [
            {
                "doc_name": "run manifest contract",
                "doc_labels": ["doc_source_surface"],
                "doc_source_path": RUN_MANIFEST_LEDGER_DOC_PATH,
                "target_name": RUN_MANIFEST_MODULE_PATH,
                "target_labels": [MODULE_SURFACE],
                "target_source_path": RUN_MANIFEST_MODULE_PATH,
                "doc_reference": RUN_MANIFEST_MODULE_PATH,
                "evidence_kind": "direct_path",
                "confidence": "high",
                "section_title": "Purpose",
                "section_anchor": "purpose",
                "line_number": 24,
            }
        ],
    )

    assert "Docs-to-code drift edges: `all`" in formatted
    assert "doc=run manifest contract | doc_labels=doc_source_surface" in formatted
    assert (
        f"target={RUN_MANIFEST_MODULE_PATH} | target_labels={MODULE_SURFACE}"
        in formatted
    )
    assert (
        f"ref={RUN_MANIFEST_MODULE_PATH} | evidence_kind=direct_path | confidence=high"
        in formatted
    )
    assert "section=Purpose | anchor=purpose | line=24" in formatted


def test_format_rows_renders_workflow_gates_summary() -> None:
    formatted = _format_rows(
        "workflow-gates",
        "tests",
        [
            {
                "workflow_name": "tests",
                "job_name": "tests::governance-preflight",
                "gates": ["pytest", "docs verification"],
                "run_targets": [
                    {"name": "scripts/docs/__main__.py", "labels": ["script_surface"]},
                    {"name": ".github/workflows/tests.yml", "labels": ["file_surface"]},
                ],
            }
        ],
    )

    assert "Workflow gates and executed targets: `tests`" in formatted
    assert "workflow=tests | job=tests::governance-preflight" in formatted
    assert "gate=pytest" in formatted
    assert "runs_via=scripts/docs/__main__.py | labels=script_surface" in formatted


def test_format_rows_renders_workflow_artifacts_summary() -> None:
    formatted = _format_rows(
        "workflow-artifacts",
        "tests",
        [
            {
                "workflow_name": "tests",
                "job_name": "tests::test-matrix",
                "actions": [
                    "actions/upload-artifact",
                    "./.github/actions/setup-python-uv",
                ],
                "artifacts": [
                    {
                        "name": "tests::coverage-data-${{ matrix.test-group.name }}",
                        "relation": "PUBLISHES_ARTIFACT",
                    },
                    {
                        "name": "tests::test-telemetry-${{ matrix.test-group.name }}",
                        "relation": "PUBLISHES_ARTIFACT",
                    },
                ],
                "secrets": ["GITHUB_TOKEN"],
            }
        ],
    )

    assert "Workflow actions, artifacts, and secrets: `tests`" in formatted
    assert "workflow=tests | job=tests::test-matrix" in formatted
    assert "action=actions/upload-artifact" in formatted
    assert (
        "artifact=tests::coverage-data-${{ matrix.test-group.name }} | relation=PUBLISHES_ARTIFACT"
        in formatted
    )
    assert "secret=GITHUB_TOKEN" in formatted


def test_format_rows_renders_workflow_execution_summary() -> None:
    formatted = _format_rows(
        "workflow-execution",
        "tests",
        [
            {
                "workflow_name": "tests",
                "workflow_concurrency_group": "tests-${{ github.ref }}",
                "job_name": "tests::test-matrix",
                "job_concurrency_group": "",
                "reusable_calls": [
                    {
                        "name": "tests::docs::./.github/workflows/reusable-setup",
                        "target_workflow": "reusable-setup",
                        "reusable_kind": "local_reusable_workflow",
                    }
                ],
                "matrix_variants": [
                    {
                        "name": "tests::test-matrix[python-version=3.13, suite=unit]",
                        "variant_axes": {"python-version": "3.13", "suite": "unit"},
                    }
                ],
                "workflow_outputs": [
                    {
                        "name": "tests::workflow_call_output::tests::venv-cache-key",
                        "scope": "workflow_call",
                        "expression": "cache-key",
                    }
                ],
                "job_outputs": [
                    {
                        "name": "tests::job_output::test-matrix::coverage-artifact",
                        "scope": "job",
                        "expression": "${{ steps.coverage.outputs.path }}",
                    }
                ],
            }
        ],
    )

    assert "Workflow execution semantics: `tests`" in formatted
    assert (
        "workflow=tests | job=tests::test-matrix | workflow_concurrency=tests-${{ github.ref }}"
        in formatted
    )
    assert (
        "call=tests::docs::./.github/workflows/reusable-setup"
        " | target_workflow=reusable-setup | kind=local_reusable_workflow" in formatted
    )
    assert (
        "matrix=tests::test-matrix[python-version=3.13, suite=unit]"
        " | axes=python-version=3.13,suite=unit" in formatted
    )
    assert (
        "workflow_output=tests::workflow_call_output::tests::venv-cache-key"
        " | scope=workflow_call | expression=cache-key" in formatted
    )
    assert (
        "job_output=tests::job_output::test-matrix::coverage-artifact"
        " | scope=job | expression=${{ steps.coverage.outputs.path }}" in formatted
    )


def test_format_rows_renders_storage_lineage_summary() -> None:
    formatted = _format_rows(
        STORAGE_LINEAGE_MODE,
        SILVER_CHEMBL_ACTIVITY,
        [
            {
                "storage_name": SILVER_CHEMBL_ACTIVITY,
                "layer": "silver",
                "storage_kind": "entity_layer_output",
                "storage_roles": ["composite_seed_input", "entity_layer_output"],
                "storage_format": "delta",
                "config_version": "1.0.0",
                "quality_version": "1.1.0",
                "schema_present": True,
                "partition_by": ["assay_type"],
                "sort_by": ["entity_id", "activity_id"],
                "versioning_mode": "scd2",
                "version_column": "_version",
                "producers": [
                    {"name": CHEMBL_ACTIVITY_PIPELINE, "labels": [PIPELINE_SURFACE]},
                    {"name": CHEMBL_ACTIVITY_PIPELINE, "labels": ["entity_config"]},
                ],
                "upstream_surfaces": ["bronze/chembl/activity"],
                "downstream_surfaces": ["gold/chembl/activity"],
                "defining_configs": [CHEMBL_ACTIVITY_CONFIG_PATH],
            }
        ],
    )

    assert f"Storage lineage path: `{SILVER_CHEMBL_ACTIVITY}`" in formatted
    assert (
        f"storage={SILVER_CHEMBL_ACTIVITY} | layer=silver | storage_kind=entity_layer_output | format=delta "
        "| roles=composite_seed_input,entity_layer_output | schema_present=True"
    ) in formatted
    assert (
        "config_version=1.0.0 | quality_version=1.1.0 | partition_by=assay_type"
        in formatted
    )
    assert (
        "sort_by=entity_id,activity_id | versioning_mode=scd2 | version_column=_version"
        in formatted
    )
    assert (
        f"producer={CHEMBL_ACTIVITY_PIPELINE} | labels={PIPELINE_SURFACE}" in formatted
    )
    assert "upstream=bronze/chembl/activity" in formatted
    assert "downstream=gold/chembl/activity" in formatted
    assert f"defined_by={CHEMBL_ACTIVITY_CONFIG_PATH}" in formatted


def test_format_rows_renders_field_lineage_summary() -> None:
    formatted = _format_rows(
        "field-lineage",
        SILVER_CHEMBL_ACTIVITY,
        [
            {
                "field_surface_name": f"{SILVER_CHEMBL_ACTIVITY}::activity_id",
                "field_name": "activity_id",
                "field_group": "business",
                "storage_ref": SILVER_CHEMBL_ACTIVITY,
                "contract_ref": CHEMBL_ACTIVITY_CONTRACT,
                "required_in_quality": True,
                "validation_types": ["required"],
                "drift_classification": "projected_to_gold",
                "storage_surfaces": [SILVER_CHEMBL_ACTIVITY],
                "contracts": [CHEMBL_ACTIVITY_CONTRACT],
                "upstream_fields": ["bronze/chembl/activity::activity_id"],
                "downstream_fields": ["gold/chembl/activity::activity_id"],
            }
        ],
    )

    assert f"Field lineage path: `{SILVER_CHEMBL_ACTIVITY}`" in formatted
    assert (
        f"storage={SILVER_CHEMBL_ACTIVITY} | field=activity_id"
        " | group=business | drift=projected_to_gold | required=True" in formatted
    )
    assert "validations=required" in formatted
    assert "upstream=bronze/chembl/activity::activity_id" in formatted
    assert "downstream=gold/chembl/activity::activity_id" in formatted
    assert f"contract={CHEMBL_ACTIVITY_CONTRACT}" in formatted


def test_format_rows_renders_schema_drift_summary() -> None:
    formatted = _format_rows(
        "schema-drift",
        SILVER_CHEMBL_ASSAY,
        [
            {
                "field_surface_name": f"{SILVER_CHEMBL_ASSAY}::_dq_failed",
                "field_name": "_dq_failed",
                "field_group": "dq",
                "storage_ref": SILVER_CHEMBL_ASSAY,
                "contract_ref": "chembl.assay",
                "drift_classification": "silver_only",
                "required_in_quality": False,
                "validation_types": [],
                "storage_surfaces": [SILVER_CHEMBL_ASSAY],
            }
        ],
    )

    assert f"Schema drift evidence: `{SILVER_CHEMBL_ASSAY}`" in formatted
    assert (
        f"storage={SILVER_CHEMBL_ASSAY} | field=_dq_failed | drift=silver_only | required=False"
        in formatted
    )


def test_format_rows_renders_run_artifacts_summary() -> None:
    formatted = _format_rows(
        "run-artifacts",
        MANIFEST_CHAIN_SMOKE,
        [
            {
                "run_instance_name": MANIFEST_CHAIN_SMOKE,
                "lifecycle_status": "success",
                "manifest_id": MANIFEST_CHAIN_SMOKE,
                "run_id": "00000000-0000-0000-0000-000000000302",
                "contract_ref": "run-manifest",
                "contract_version": "1.0.0",
                "effective_config_artifact_id": "effective_config_artifact::json",
                "lineage_fragment_id": "lineage::fragment",
                "artifacts": [
                    {
                        "name": "run_ledger::jsonl",
                        "labels": ["control_plane_artifact_surface"],
                        "artifact_family": "run_ledger",
                    }
                ],
                "dependencies": [
                    {"name": CHEMBL_ACTIVITY_PIPELINE, "labels": [PIPELINE_SURFACE]}
                ],
                "support_links": [
                    {
                        "name": "tests/unit/application/services/test_run_manifest_inspection_service.py",
                        "labels": ["test_artifact"],
                    }
                ],
            }
        ],
    )

    assert f"Run instance artifact chain: `{MANIFEST_CHAIN_SMOKE}`" in formatted
    assert (
        f"run_instance={MANIFEST_CHAIN_SMOKE} | lifecycle_status=success | manifest_id={MANIFEST_CHAIN_SMOKE} "
        "| run_id=00000000-0000-0000-0000-000000000302"
    ) in formatted
    assert "contract_ref=run-manifest | contract_version=1.0.0" in formatted
    assert (
        "effective_config_artifact_id=effective_config_artifact::json | lineage_fragment_id=lineage::fragment"
        in formatted
    )
    assert (
        "artifact=run_ledger::jsonl | labels=control_plane_artifact_surface | artifact_family=run_ledger"
        in formatted
    )
    assert (
        f"depends_on={CHEMBL_ACTIVITY_PIPELINE} | labels={PIPELINE_SURFACE}"
        in formatted
    )
    assert (
        "support=tests/unit/application/services/test_run_manifest_inspection_service.py | labels=test_artifact"
        in formatted
    )


def test_format_rows_renders_runtime_state_summary() -> None:
    formatted = _format_rows(
        "runtime-state",
        "all",
        [
            {
                "runtime_state_name": "manifest-chain-2::retry-window",
                "state_kind": "retry_state",
                "state_status": "retrying",
                "manifest_id": "manifest-chain-2",
                "retry_count": 1,
                "lock_key": "",
                "owners": [
                    {"name": "manifest-chain-2", "labels": ["run_instance_surface"]}
                ],
                "dependencies": [
                    {"name": CHEMBL_ACTIVITY_PIPELINE, "labels": [PIPELINE_SURFACE]}
                ],
                "artifacts": [
                    {
                        "name": "run_ledger::jsonl",
                        "labels": ["control_plane_artifact_surface"],
                        "artifact_family": "run_ledger",
                    }
                ],
            }
        ],
    )

    assert "Runtime state summary: `all`" in formatted
    assert (
        "state=manifest-chain-2::retry-window | kind=retry_state"
        " | status=retrying | manifest_id=manifest-chain-2 | retry_count=1" in formatted
    )
    assert "owner=manifest-chain-2 | labels=run_instance_surface" in formatted
    assert (
        f"dependency={CHEMBL_ACTIVITY_PIPELINE} | labels={PIPELINE_SURFACE}"
        in formatted
    )
    assert (
        "artifact=run_ledger::jsonl | labels=control_plane_artifact_surface | artifact_family=run_ledger"
        in formatted
    )


def test_format_rows_renders_claim_trace_summary() -> None:
    formatted = _format_rows(
        "claim-trace",
        "all",
        [
            {
                "doc_name": "run manifest contract",
                "claim_name": RUN_MANIFEST_LEDGER_DOC_CLAIM,
                "claim_text": "activity_id is required",
                "modality": "required",
                "section_title": "Field Requirements",
                "section_anchor": "field-requirements",
                "line_number": 24,
                "targets": [
                    {
                        "name": RUN_MANIFEST_MODULE_PATH,
                        "labels": [MODULE_SURFACE],
                    }
                ],
            }
        ],
    )

    assert "Claim-level documentation traceability: `all`" in formatted
    assert (
        f"doc=run manifest contract | claim={RUN_MANIFEST_LEDGER_DOC_CLAIM} | modality=required"
        in formatted
    )
    assert "text=activity_id is required" in formatted
    assert f"target={RUN_MANIFEST_MODULE_PATH} | labels={MODULE_SURFACE}" in formatted


def test_format_rows_renders_cli_semantics_summary() -> None:
    formatted = _format_rows(
        "cli-semantics",
        "bioetl run",
        [
            {
                "command_name": "bioetl run",
                "side_effect_class": "mutating",
                "options": ["--limit", "--pipeline"],
                "gates": ["pytest"],
                "side_effect_targets": [
                    {"name": SILVER_CHEMBL_ACTIVITY, "labels": ["storage_surface"]}
                ],
            }
        ],
    )

    assert "CLI options and side-effect semantics: `bioetl run`" in formatted
    assert "command=bioetl run | side_effect_class=mutating" in formatted
    assert "option=--limit" in formatted
    assert "gate=pytest" in formatted
    assert (
        f"side_effect_target={SILVER_CHEMBL_ACTIVITY} | labels=storage_surface"
        in formatted
    )


def test_format_rows_renders_duplication_cluster_summary() -> None:
    formatted = _format_rows(
        "duplication-cluster",
        f"{ADAPTER_LAYER}:method_surface:de487f71c608",
        [
            {
                "cluster_name": f"{ADAPTER_LAYER}:method_surface:de487f71c608",
                "family_name": ADAPTER_LAYER,
                "surface_kind": "method_surface",
                "duplicate_count": 4,
                "promotion_score": 0.99,
                "promotion_target": "src/bioetl/infrastructure/adapters/base.py",
                "promotion_target_labels": [MODULE_SURFACE],
                "members": [
                    {
                        "name": "src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count",
                        "labels": ["method_surface"],
                    }
                ],
                "tests": [
                    "tests/unit/infrastructure/adapters/test_pubmed_health.py",
                ],
            }
        ],
    )

    assert (
        f"Duplication cluster: `{ADAPTER_LAYER}:method_surface:de487f71c608`"
        in formatted
    )
    assert (
        f"family={ADAPTER_LAYER} | surface_kind=method_surface | duplicates=4 | promotion_score=0.99"
        in formatted
    )
    assert (
        f"promotion_target=src/bioetl/infrastructure/adapters/base.py"
        f" | labels={MODULE_SURFACE}" in formatted
    )
    assert (
        "member=src.bioetl.infrastructure.adapters.pubmed"
        "._health.PubMedHealthMixin.request_count | labels=method_surface" in formatted
    )
    assert (
        "covered_by_test=tests/unit/infrastructure/adapters/test_pubmed_health.py"
        in formatted
    )


def test_format_rows_renders_pipeline_normalization_evidence() -> None:
    formatted = _format_rows(
        "normalization-pipeline",
        CHEMBL_ACTIVITY_PIPELINE,
        [
            {
                "pipeline_name": CHEMBL_ACTIVITY_PIPELINE,
                "normalization_profile_registered": True,
                "normalization_profile_module_path": "src/bioetl/domain/normalization/profiles/chembl_activity.py",
                "profile_field_count": 12,
                "fallback_field_count": 1,
                "fallback_business_field_count": 1,
                "fallback_technical_passthrough_field_count": 0,
                "normalization_modules": [
                    RECORD_NORMALIZATION_PROCESSOR_PATH,
                    "src/bioetl/domain/normalization/profiles/chembl_activity.py",
                ],
            }
        ],
    )

    assert f"Pipeline normalization evidence: `{CHEMBL_ACTIVITY_PIPELINE}`" in formatted
    assert (
        "profile_registered=True | profile_fields=12 | fallback_fields=1 | fallback_business=1 | fallback_technical=0"
        in formatted
    )
    assert (
        "profile_module=src/bioetl/domain/normalization/profiles/chembl_activity.py"
        in formatted
    )
    assert (
        "normalization_module=src/bioetl/domain/normalization/profiles/chembl_activity.py"
        in formatted
    )


def test_format_rows_renders_fallback_pipeline_summary() -> None:
    formatted = _format_rows(
        "fallback-pipelines",
        "all",
        [
            {
                "pipeline_name": "chembl_assay_parameters",
                "normalization_profile_registered": False,
                "profile_field_count": 0,
                "fallback_field_count": 22,
                "fallback_business_field_count": 22,
            }
        ],
    )

    assert "Fallback-heavy pipelines: `all`" in formatted
    assert (
        "pipeline=chembl_assay_parameters | fallback_business=22"
        " | fallback_total=22 | profile_registered=False | profile_fields=0"
        in formatted
    )


def test_format_rows_renders_promotion_candidates_summary() -> None:
    formatted = _format_rows(
        "promotion-candidates",
        ADAPTER_LAYER,
        [
            {
                "cluster_name": f"{ADAPTER_LAYER}:method_surface:d1c4b44398a1",
                "family_name": ADAPTER_LAYER,
                "surface_kind": "method_surface",
                "duplicate_count": 27,
                "promotion_score": 0.99,
                "promotion_target": "src/bioetl/infrastructure/adapters/base.py",
                "member_count": 27,
                "test_count": 80,
            }
        ],
    )

    assert f"Promotion candidates: `{ADAPTER_LAYER}`" in formatted
    assert (
        f"cluster={ADAPTER_LAYER}:method_surface:d1c4b44398a1 | family={ADAPTER_LAYER}"
        in formatted
    )
    assert "duplicates=27 | members=27 | tests=80 | promotion_score=0.99" in formatted
    assert "target=src/bioetl/infrastructure/adapters/base.py" in formatted


def test_format_rows_renders_dead_code_candidates_summary() -> None:
    formatted = _format_rows(
        DEAD_CODE_CANDIDATES_MODE,
        ADAPTER_LAYER,
        [
            {
                "candidate_name": "module_surface:src/bioetl/infrastructure/adapters/pubchem/client.py",
                "family_name": ADAPTER_LAYER,
                "target_label": MODULE_SURFACE,
                "target_name": "src/bioetl/infrastructure/adapters/pubchem/client.py",
                "deletion_score": 8,
                "deletion_confidence": "high",
                "recent_age_days": 420,
                "only_test_referenced": True,
                "deprecation_markers": ["deprecated", "legacy"],
                RUNTIME_ANCHOR_COUNT: 0,
                CONFIG_ANCHOR_COUNT: 0,
                DOC_ANCHOR_COUNT: 0,
                TEST_ANCHOR_COUNT: 3,
                "blocked_by_cycle": "",
            }
        ],
    )

    assert f"Dead code candidates: `{ADAPTER_LAYER}`" in formatted
    assert (
        f"target=src/bioetl/infrastructure/adapters/pubchem/client.py | label={MODULE_SURFACE} | family={ADAPTER_LAYER}"
        in formatted
    )
    assert "deletion_score=8 | confidence=high | recent_age_days=420" in formatted
    assert "deprecation_markers=deprecated,legacy" in formatted


def test_format_rows_renders_current_cycle_code_summary() -> None:
    formatted = _format_rows(
        CURRENT_CYCLE_CODE_MODE,
        ADAPTER_LAYER,
        [
            {
                "cycle_name": "module_surface:src/bioetl/infrastructure/adapters/common/new_runtime.py",
                "family_name": ADAPTER_LAYER,
                "target_label": MODULE_SURFACE,
                "target_name": "src/bioetl/infrastructure/adapters/common/new_runtime.py",
                "cycle_status": "current_cycle",
                "cycle_score": 5,
                "recent_age_days": 3,
                "wip_markers": ["todo", "temporary"],
                RUNTIME_ANCHOR_COUNT: 0,
                CONFIG_ANCHOR_COUNT: 0,
                DOC_ANCHOR_COUNT: 1,
                TEST_ANCHOR_COUNT: 1,
            }
        ],
    )

    assert f"Current-cycle code surfaces: `{ADAPTER_LAYER}`" in formatted
    assert (
        f"target=src/bioetl/infrastructure/adapters/common/new_runtime.py"
        f" | label={MODULE_SURFACE} | family={ADAPTER_LAYER}" in formatted
    )
    assert "cycle_status=current_cycle | cycle_score=5 | recent_age_days=3" in formatted
    assert "wip_markers=todo,temporary" in formatted


def test_format_rows_renders_overengineered_candidates_summary() -> None:
    formatted = _format_rows(
        OVERENGINEERED_CANDIDATES_MODE,
        COMPOSITE_LAYER,
        [
            {
                "candidate_name": "module_surface:src/bioetl/application/composite/runner_pkg/runner.py",
                "family_name": COMPOSITE_LAYER,
                "target_label": MODULE_SURFACE,
                "target_name": "src/bioetl/application/composite/runner_pkg/runner.py",
                "classification": "overengineered_stale",
                "complexity_score": 6,
                "simplification_score": 6,
                "removable_score": 8,
                "branch_count": 7,
                "nesting_depth": 4,
                "helper_call_count": 3,
                "indirection_markers": ["compat", "runner"],
                "stateful_markers": ["runner"],
                RUNTIME_ANCHOR_COUNT: 0,
                CONFIG_ANCHOR_COUNT: 0,
                DOC_ANCHOR_COUNT: 0,
                TEST_ANCHOR_COUNT: 0,
                "blocked_by_cycle": "",
            }
        ],
    )

    assert f"Overengineered candidates: `{COMPOSITE_LAYER}`" in formatted
    assert (
        f"target=src/bioetl/application/composite/runner_pkg/runner.py"
        f" | label={MODULE_SURFACE} | family={COMPOSITE_LAYER}" in formatted
    )
    assert (
        "classification=overengineered_stale | complexity_score=6"
        " | simplification_score=6 | removable_score=8" in formatted
    )
    assert "indirection_markers=compat,runner" in formatted


def test_format_rows_renders_removable_complexity_summary() -> None:
    formatted = _format_rows(
        REMOVABLE_COMPLEXITY_MODE,
        COMPOSITE_LAYER,
        [
            {
                "candidate_name": "module_surface:src/bioetl/application/composite/merger.py",
                "family_name": COMPOSITE_LAYER,
                "target_label": MODULE_SURFACE,
                "target_name": "src/bioetl/application/composite/merger.py",
                "removable_score": 9,
                "removal_confidence": "high",
                "deprecation_markers": ["compat", "legacy"],
                RUNTIME_ANCHOR_COUNT: 0,
                CONFIG_ANCHOR_COUNT: 0,
                DOC_ANCHOR_COUNT: 0,
                TEST_ANCHOR_COUNT: 0,
            }
        ],
    )

    assert f"Removable complexity candidates: `{COMPOSITE_LAYER}`" in formatted
    assert (
        f"target=src/bioetl/application/composite/merger.py | label={MODULE_SURFACE} | family={COMPOSITE_LAYER}"
        in formatted
    )
    assert "removable_score=9 | removal_confidence=high" in formatted
    assert "deprecation_markers=compat,legacy" in formatted


def test_format_rows_renders_simplification_blockers_summary() -> None:
    formatted = _format_rows(
        SIMPLIFICATION_BLOCKERS_MODE,
        ADAPTER_LAYER,
        [
            {
                "candidate_name": (
                    "method_surface:src.bioetl.infrastructure.adapters"
                    ".pubmed._health.PubMedHealthMixin.request_count"
                ),
                "family_name": ADAPTER_LAYER,
                "target_label": "method_surface",
                "target_name": "src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count",
                "classification": "overengineered_active",
                RUNTIME_ANCHOR_COUNT: 2,
                CONFIG_ANCHOR_COUNT: 1,
                DOC_ANCHOR_COUNT: 0,
                TEST_ANCHOR_COUNT: 3,
                "cycle_blockers": [
                    "method_surface:src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count"
                ],
                "blockers": [
                    {
                        "name": "pubmed",
                        "labels": ["provider_surface"],
                        "relation": "BLOCKED_BY_VARIANCE",
                    }
                ],
            }
        ],
    )

    assert f"Simplification blockers: `{ADAPTER_LAYER}`" in formatted
    assert (
        f"target=src.bioetl.infrastructure.adapters.pubmed"
        f"._health.PubMedHealthMixin.request_count | label=method_surface | family={ADAPTER_LAYER}"
        in formatted
    )
    assert (
        "cycle_blocker=method_surface:src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count"
        in formatted
    )
    assert (
        "blocker=pubmed | relation=BLOCKED_BY_VARIANCE | labels=provider_surface"
        in formatted
    )


def test_format_rows_handles_missing_results() -> None:
    formatted = _format_rows("owner-alert", "BioETLPipelineRunFailed", [])

    assert (
        formatted
        == "Alert ownership path: no ownership path found for `BioETLPipelineRunFailed`."
    )


def test_format_rows_handles_missing_neighbors() -> None:
    formatted = _format_rows("neighbors-alert", "BioETLPipelineRunFailed", [])

    assert (
        formatted
        == "Alert semantic neighborhood: no semantic neighbors found for `BioETLPipelineRunFailed`."
    )


def test_format_rows_handles_missing_docs_drift() -> None:
    formatted = _format_rows("docs-drift", "missing-doc", [])

    assert (
        formatted
        == "Docs-to-code drift edges: no docs-to-code drift edges found for `missing-doc`."
    )


def test_format_rows_handles_missing_workflow_gates() -> None:
    formatted = _format_rows("workflow-gates", "missing-workflow", [])

    assert (
        formatted
        == "Workflow gates and executed targets: no workflow gate coverage found for `missing-workflow`."
    )


def test_format_rows_handles_missing_storage_lineage() -> None:
    formatted = _format_rows(STORAGE_LINEAGE_MODE, "missing-storage", [])

    assert (
        formatted
        == "Storage lineage path: no storage lineage found for `missing-storage`."
    )


def test_format_rows_handles_missing_duplication_cluster() -> None:
    formatted = _format_rows(DUPLICATION_CLUSTER_MODE, "missing-cluster", [])

    assert (
        formatted
        == "Duplication cluster: no duplication cluster found for `missing-cluster`."
    )


def test_format_rows_handles_missing_promotion_candidates() -> None:
    formatted = _format_rows(PROMOTION_CANDIDATES_MODE, MISSING_FAMILY, [])

    assert (
        formatted
        == f"Promotion candidates: no promotion candidates found for `{MISSING_FAMILY}`."
    )


def test_format_rows_handles_missing_dead_code_candidates() -> None:
    formatted = _format_rows(DEAD_CODE_CANDIDATES_MODE, MISSING_FAMILY, [])

    assert (
        formatted
        == f"Dead code candidates: no dead code candidates found for `{MISSING_FAMILY}`."
    )


def test_format_rows_handles_missing_current_cycle_code() -> None:
    formatted = _format_rows(CURRENT_CYCLE_CODE_MODE, MISSING_FAMILY, [])

    assert (
        formatted
        == f"Current-cycle code surfaces: no current-cycle code surfaces found for `{MISSING_FAMILY}`."
    )


def test_format_rows_handles_missing_overengineered_candidates() -> None:
    formatted = _format_rows(OVERENGINEERED_CANDIDATES_MODE, MISSING_FAMILY, [])

    assert (
        formatted
        == f"Overengineered candidates: no overengineered candidates found for `{MISSING_FAMILY}`."
    )


def test_format_rows_handles_missing_removable_complexity() -> None:
    formatted = _format_rows("removable-complexity", MISSING_FAMILY, [])

    assert (
        formatted
        == f"Removable complexity candidates: no removable complexity candidates found for `{MISSING_FAMILY}`."
    )


def test_format_rows_handles_missing_simplification_blockers() -> None:
    formatted = _format_rows("simplification-blockers", MISSING_FAMILY, [])

    assert (
        formatted
        == f"Simplification blockers: no simplification blockers found for `{MISSING_FAMILY}`."
    )
