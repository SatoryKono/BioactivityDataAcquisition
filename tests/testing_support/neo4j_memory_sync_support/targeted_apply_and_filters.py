"""Targeted-apply and filtering support tests for Neo4j memory sync."""

from __future__ import annotations

from .common import *  # noqa: F401,F403


def test_normalization_evidence_statements_cover_registry_and_fallback_metrics() -> (
    None
):
    statements = _normalization_evidence_statements()
    chembl_activity = next(
        item
        for item in statements
        if item["parameters"]["pipeline_name"] == "chembl_activity"
    )
    assay_parameters = next(
        item
        for item in statements
        if item["parameters"]["pipeline_name"] == "chembl_assay_parameters"
    )

    chembl_params = chembl_activity["parameters"]
    assert chembl_params["normalization_profile_registered"] is True
    assert chembl_params["normalization_profile_module_path"] == (
        PATH_CHEMBL_ACTIVITY_PROFILE
    )
    assert chembl_params["profile_field_count"] > 0

    assay_params = assay_parameters["parameters"]
    assert assay_params["normalization_profile_registered"] is True
    assert assay_params["normalization_profile_module_path"] == (
        "src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py"
    )
    assert assay_params["profile_field_count"] > 0
    assert assay_params["fallback_business_field_count"] == 0
    assert assay_params["fallback_field_count"] == 0


def test_apply_normalization_evidence_only_executes_batched_statements(
    monkeypatch,
) -> None:
    executed_batches: list[list[dict[str, object]]] = []
    batch_contexts: list[str | None] = []
    stub_statements = [
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "chembl_activity"},
        },
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "pubmed_publication"},
        },
        {
            "statement": STMT_RETURN_1,
            "parameters": {"pipeline_name": "crossref_publication"},
        },
    ]

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def execute(
            self,
            statements: list[dict[str, object]],
            *,
            context: str | None = None,
        ) -> dict[str, object]:
            executed_batches.append(statements)
            batch_contexts.append(context)
            return {"results": [], "errors": []}

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    monkeypatch.setattr(
        f"{SYNC_CORE_MODULE_PATH}._normalization_evidence_statements",
        lambda: list(stub_statements),
    )
    monkeypatch.setattr(
        f"{SYNC_CORE_MODULE_PATH}.resolve_neo4j_connection",
        lambda _root, _http_uri: (
            HOST_DOCKER_INTERNAL_HTTP_URI,
            "neo4j",
            "test-password",
            "neo4j",
        ),
    )
    root = _repo_root()

    summary = apply_normalization_evidence_only(
        root,
        HOST_DOCKER_INTERNAL_HTTP_URI,
        batch_size=2,
    )

    assert summary["pipeline_count"] == len(stub_statements)
    assert summary["completed_statement_count"] == len(stub_statements)
    assert summary["batch_count"] == len(executed_batches)
    assert summary["batch_size"] == 2
    assert len(summary["batches"]) == len(executed_batches)
    assert executed_batches
    assert sum(len(batch) for batch in executed_batches) == len(stub_statements)
    assert batch_contexts
    assert batch_contexts[0] is not None
    assert "normalization evidence batch 1/" in str(batch_contexts[0])
    assert summary["batches"][0]["pipeline_start"] == "chembl_activity"
    assert summary["batches"][0]["pipeline_end"] == "pubmed_publication"


def test_targeted_apply_required_anchor_labels_identifies_missing_base_labels() -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    snapshot.add_relation(
        complexity_candidate, "CANDIDATE_FOR_SIMPLIFICATION", class_surface
    )

    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    assert _targeted_apply_required_anchor_labels(filtered) == ("class_surface",)


def test_only_label_filter_does_not_pull_external_analysis_anchors() -> None:
    snapshot = GraphSnapshot()
    function_surface = snapshot.add_node("function_surface", "pkg.normalize")
    duplication_cluster = snapshot.add_node(
        "duplication_cluster",
        "adapter_layer:function_surface:abc123",
    )
    complexity_candidate = snapshot.add_node(
        "complexity_candidate",
        "function_surface:pkg.normalize",
    )
    snapshot.add_relation(duplication_cluster, "CONTAINS", function_surface)
    snapshot.add_relation(
        function_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate
    )

    filtered = _filtered_snapshot(
        snapshot,
        only_labels=("duplication_cluster", "function_surface"),
    )

    assert _targeted_apply_required_anchor_labels(filtered) == ()
    assert _targeted_apply_external_anchor_keys(filtered) == ()
    assert (
        NodeKey("duplication_cluster", "adapter_layer:function_surface:abc123"),
        "CONTAINS",
        NodeKey("function_surface", "pkg.normalize"),
    ) in filtered.relations
    assert all(
        relation.relation_type != "HAS_COMPLEXITY_SIGNAL"
        for relation in filtered.relations.values()
    )


def test_targeted_apply_external_anchor_keys_identifies_missing_base_nodes() -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    snapshot.add_relation(
        complexity_candidate, "CANDIDATE_FOR_SIMPLIFICATION", class_surface
    )

    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    assert _targeted_apply_external_anchor_keys(filtered) == (
        NodeKey("class_surface", CLASS_PKG_EXAMPLE),
    )


def test_ensure_targeted_apply_prerequisites_raises_clear_error_when_anchor_graph_is_empty() -> (
    None
):
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    try:
        _ensure_targeted_apply_prerequisites(
            _TargetedApplyPrereqStubClient(),  # type: ignore[arg-type]
            filtered,
            mode_description="complexity-layer targeted sync",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected prerequisite failure for empty anchor graph")

    assert "Run a base sync first" in message
    assert "`class_surface`" in message


def test_missing_managed_anchor_keys_reports_specific_nodes() -> None:
    class StubClient:
        def query(
            self,
            _statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert context == CONTEXT_COMPLEXITY_PREREQ
            assert parameters is not None
            assert parameters["anchors"] == [
                {"label": "class_surface", "name": CLASS_PKG_EXAMPLE},
                {"label": "module_surface", "name": PATH_PKG_EXAMPLE},
            ]
            return [
                {"label": "class_surface", "name": CLASS_PKG_EXAMPLE, "count": 1},
                {"label": "module_surface", "name": PATH_PKG_EXAMPLE, "count": 0},
            ]

    missing = _missing_managed_anchor_keys(
        StubClient(),  # type: ignore[arg-type]
        (
            NodeKey("class_surface", CLASS_PKG_EXAMPLE),
            NodeKey("module_surface", PATH_PKG_EXAMPLE),
        ),
        context=CONTEXT_COMPLEXITY_PREREQ,
    )

    assert missing == (NodeKey("module_surface", PATH_PKG_EXAMPLE),)


def test_ensure_targeted_apply_prerequisites_raises_clear_error_when_specific_anchor_nodes_are_missing() -> (
    None
):
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    class_surface = snapshot.add_node("class_surface", CLASS_PKG_EXAMPLE)
    complexity_candidate = snapshot.add_node(
        "complexity_candidate", COMPLEXITY_PKG_EXAMPLE
    )
    snapshot.add_relation(project, "CONTAINS", complexity_candidate)
    snapshot.add_relation(class_surface, "HAS_COMPLEXITY_SIGNAL", complexity_candidate)
    filtered = _filtered_snapshot(snapshot, only_complexity_layer=True)

    class StubClient:
        def query(
            self,
            _statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert parameters is not None
            if context == "complexity-layer targeted sync prerequisite anchor check":
                return [{"label": "class_surface", "count": 1}]
            if context == CONTEXT_COMPLEXITY_PREREQ:
                return [
                    {"label": "class_surface", "name": CLASS_PKG_EXAMPLE, "count": 0}
                ]
            raise AssertionError(f"Unexpected context: {context}")

    try:
        _ensure_targeted_apply_prerequisites(
            StubClient(),  # type: ignore[arg-type]
            filtered,
            mode_description="complexity-layer targeted sync",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected prerequisite failure for missing anchor nodes")

    assert "Run a base sync first" in message
    assert "`class_surface:pkg.Example`" in message
