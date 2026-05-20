"""Audit/runtime/transport support tests for Neo4j memory sync."""

from __future__ import annotations

from .common import *  # noqa: F401,F403

def test_live_managed_count_helpers_batch_labels_and_relations() -> None:
    class StubClient:
        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert context is not None
            assert parameters is not None
            if "UNWIND $labels AS label" in statement:
                return [
                    {"label": "retirement_candidate", "count": 4},
                    {"label": "complexity_candidate", "count": 2},
                ]
            if "UNWIND $relation_types AS relation_type" in statement:
                return [
                    {"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 3},
                    {"relation_type": "CANDIDATE_FOR_SIMPLIFICATION", "count": 1},
                ]
            raise AssertionError(f"Unexpected statement: {statement}")

    client = StubClient()

    label_counts = _live_managed_node_counts(
        client,  # type: ignore[arg-type]
        ("retirement_candidate", "complexity_candidate"),
        context=CONTEXT_FAST_AUDIT_LABEL,
    )
    relation_counts = _live_managed_relation_counts(
        client,  # type: ignore[arg-type]
        ("CANDIDATE_FOR_REMOVAL", "CANDIDATE_FOR_SIMPLIFICATION"),
        context="fast audit relation summary",
    )

    assert label_counts == {
        "retirement_candidate": 4,
        "complexity_candidate": 2,
    }
    assert relation_counts == {
        "CANDIDATE_FOR_REMOVAL": 3,
        "CANDIDATE_FOR_SIMPLIFICATION": 1,
    }


def test_git_last_commit_age_days_bulk_batches_history_lookup(monkeypatch) -> None:
    class Result:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    calls: list[list[str]] = []

    def _run(
        cmd: list[str],
        _check: bool,
        _capture_output: bool,
        _text: bool,
    ) -> Result:
        calls.append(cmd)
        return Result(
            "__TS__1712448000\nsrc/a.py\nsrc/b.py\n\n__TS__1712361600\nsrc/c.py\n",
        )

    monkeypatch.setattr("scripts.memory.sync.subprocess.run", _run)
    monkeypatch.setattr("scripts.memory.sync._resolve_git_executable", lambda: "git")

    cache: dict[str, int | None] = {}
    result = _git_last_commit_age_days_bulk(
        Path("/repo"),
        [PATH_SRC_A, PATH_SRC_B, PATH_SRC_C],
        date(2026, 4, 10),
        cache,
        chunk_size=10,
    )

    assert len(calls) == 1
    assert calls[0][-3:] == [PATH_SRC_A, PATH_SRC_B, PATH_SRC_C]
    assert result[PATH_SRC_A] is not None
    assert result[PATH_SRC_B] == result[PATH_SRC_A]
    assert result[PATH_SRC_C] is not None
    assert cache == result


def test_build_fast_analysis_audit_report_uses_bulk_count_queries(monkeypatch) -> None:
    class StubSnapshot:
        def stats(self) -> dict[str, object]:
            return {
                "node_count": 6,
                "relation_count": 4,
                "labels": {
                    "retirement_candidate": 4,
                    "complexity_candidate": 2,
                },
                "relation_types": {
                    "CANDIDATE_FOR_REMOVAL": 3,
                    "CANDIDATE_FOR_SIMPLIFICATION": 1,
                },
            }

    snapshot = StubSnapshot()
    query_calls: list[str] = []

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            query_calls.append(context or "")
            if "UNWIND $labels AS label" in statement:
                labels = (
                    list(parameters["labels"]) if isinstance(parameters, dict) else []
                )
                return [
                    {
                        "label": label,
                        "count": int(snapshot.stats()["labels"].get(label, 0)),
                    }
                    for label in labels
                ]
            if "UNWIND $relation_types AS relation_type" in statement:
                relation_types = (
                    list(parameters["relation_types"])
                    if isinstance(parameters, dict)
                    else []
                )
                return [
                    {
                        "relation_type": relation_type,
                        "count": int(
                            snapshot.stats()["relation_types"].get(relation_type, 0)
                        ),
                    }
                    for relation_type in relation_types
                ]
            raise AssertionError(f"Unexpected statement: {statement}")

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    monkeypatch.setattr(
        "scripts.memory.sync.resolve_neo4j_connection",
        lambda _root, _http_uri: (
            LOCALHOST_HTTP_URI,
            "neo4j",
            "test-password",
            "neo4j",
        ),
    )
    root = _repo_root()

    report = build_fast_analysis_audit_report(snapshot, root, LOCALHOST_HTTP_URI)  # type: ignore[arg-type]

    assert query_calls == [
        CONTEXT_FAST_AUDIT_LABEL,
        "fast audit relation summary",
    ]
    assert _critical_analysis_audit_issues(report) == []


def test_build_audit_report_uses_bulk_summary_queries(monkeypatch) -> None:
    snapshot = GraphSnapshot()
    retirement_candidate = snapshot.add_node("retirement_candidate", "retire-me.py")
    complexity_candidate = snapshot.add_node("complexity_candidate", "simplify-me.py")
    snapshot.add_relation(
        retirement_candidate,
        "CANDIDATE_FOR_REMOVAL",
        complexity_candidate,
    )
    query_calls: list[str] = []

    class StubClient:
        def __init__(
            self, base_uri: str, username: str, password: str, database: str
        ) -> None:
            self.base_uri = base_uri
            self.username = username
            self.password = password
            self.database = database

        def query(
            self,
            _statement: str,
            _parameters: dict[str, object] | None = None,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            del _statement, _parameters
            query_calls.append(context or "")
            if context == "full audit label summary":
                return [
                    {
                        "label": "complexity_candidate",
                        "total": 2,
                        "managed": 2,
                        "unmanaged": 0,
                    },
                    {
                        "label": "retirement_candidate",
                        "total": 5,
                        "managed": 4,
                        "unmanaged": 1,
                    },
                ]
            if context == "full audit relation summary":
                return [
                    {"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 3},
                    {"relation_type": "CANDIDATE_FOR_SIMPLIFICATION", "count": 1},
                ]
            if context == "full audit orphan summary":
                return [
                    {
                        "label": "retirement_candidate",
                        "count": 1,
                        "samples": ["stale-module.py"],
                    },
                    {"label": "complexity_candidate", "count": 0, "samples": []},
                ]
            if context == "full audit unmanaged summary":
                return [
                    {
                        "label": "retirement_candidate",
                        "count": 1,
                        "samples": ["legacy-module.py"],
                    },
                    {"label": "complexity_candidate", "count": 0, "samples": []},
                ]
            raise AssertionError(f"Unexpected query context: {context}")

    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, StubClient)
    monkeypatch.setattr(
        "scripts.memory.sync.resolve_neo4j_connection",
        lambda _root, _http_uri: (
            LOCALHOST_HTTP_URI,
            "neo4j",
            "test-password",
            "neo4j",
        ),
    )
    root = _repo_root()

    report = build_audit_report(snapshot, root, LOCALHOST_HTTP_URI)

    assert query_calls == [
        "full audit label summary",
        "full audit relation summary",
        "full audit orphan summary",
        "full audit unmanaged summary",
    ]
    assert report["live"]["managed_node_total"] == 6
    assert report["live"]["unmanaged_repo_node_total"] == 1
    assert report["live"]["managed_relation_total"] == 4


def test_verify_expected_group_counts_uses_sync_run_for_targeted_relation_checks() -> (
    None
):
    relation_groups = {
        "CANDIDATE_FOR_REMOVAL": [
            {"statement": "RETURN 1", "parameters": {}},
            {"statement": "RETURN 1", "parameters": {}},
        ]
    }
    seen_params: list[dict[str, object]] = []

    class StubClient:
        def query(
            self,
            statement: str,
            parameters: dict[str, object] | None = None,
            *,
            context: str | None = None,
        ) -> list[dict[str, object]]:
            assert parameters is not None
            seen_params.append(parameters)
            if context == "post-apply node group verification":
                return []
            if context == "post-apply relation group verification":
                assert "coalesce(r.sync_run, '') = $sync_run" in statement
                assert parameters["sync_run"] == "run-123"
                return [{"relation_type": "CANDIDATE_FOR_REMOVAL", "count": 2}]
            raise AssertionError(f"Unexpected query context: {context}")

    _verify_expected_group_counts(
        StubClient(),  # type: ignore[arg-type]
        {},
        relation_groups,
        strict_analysis=False,
        sync_run="run-123",
    )

    assert any(params.get("sync_run") == "run-123" for params in seen_params)


def test_sync_snapshot_uses_current_sync_run_for_prune_stale_verification(
    monkeypatch, tmp_path: Path
) -> None:
    snapshot = GraphSnapshot()
    snapshot.add_node("complexity_candidate", "candidate-1")
    captured_retry_sync_runs: list[str | None] = []
    captured_verify_sync_runs: list[str | None] = []

    class StubClient:
        def execute(self, _statements, *, _context=None) -> dict[str, object]:
            return {"results": [], "errors": []}

        def query(
            self,
            *args: object,
            context=None,
        ) -> list[dict[str, object]]:
            del args, context
            return []

    monkeypatch.setattr(
        "scripts.memory.sync.resolve_neo4j_connection",
        lambda _root, _http_uri: (
            LOCALHOST_HTTP_URI,
            "neo4j",
            "password",
            "neo4j",
        ),
    )
    monkeypatch.setattr(NEO4J_HTTP_CLIENT_PATH, lambda *_args, **_kwargs: StubClient())
    monkeypatch.setattr("scripts.memory.sync._sync_run_id", lambda: "run-123")

    def _retry(*_args, **kwargs) -> None:
        captured_retry_sync_runs.append(kwargs.get("sync_run"))

    def _verify(*_args, **kwargs) -> None:
        captured_verify_sync_runs.append(kwargs.get("sync_run"))

    monkeypatch.setattr("scripts.memory.sync._retry_critical_analysis_groups", _retry)
    monkeypatch.setattr("scripts.memory.sync._verify_expected_group_counts", _verify)

    sync_snapshot(
        snapshot,
        tmp_path,
        None,
        batch_size=10,
        prune_stale=True,
    )

    assert captured_retry_sync_runs == ["run-123"]
    assert captured_verify_sync_runs == ["run-123"]


def test_main_skips_global_post_apply_fast_audit_for_targeted_sync(
    monkeypatch, tmp_path: Path
) -> None:
    snapshot = GraphSnapshot()
    snapshot.add_node("retirement_candidate", "retire-me.py")
    called: dict[str, int] = {"sync_snapshot": 0, "build_fast_analysis_audit_report": 0}

    monkeypatch.setattr("scripts.memory.sync.build_snapshot", lambda _root: snapshot)
    monkeypatch.setattr(
        "scripts.memory.sync._filtered_snapshot",
        lambda current, **_kwargs: current,
    )

    def _sync_snapshot(*_args, **_kwargs) -> None:
        called["sync_snapshot"] += 1

    def _build_fast_analysis_audit_report(*_args, **_kwargs) -> dict[str, object]:
        called["build_fast_analysis_audit_report"] += 1
        return {}

    monkeypatch.setattr("scripts.memory.sync.sync_snapshot", _sync_snapshot)
    monkeypatch.setattr(
        "scripts.memory.sync.build_fast_analysis_audit_report",
        _build_fast_analysis_audit_report,
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--apply",
            "--only-retirement-layer",
        ]
    )

    assert exit_code == 0
    assert called["sync_snapshot"] == 1
    assert called["build_fast_analysis_audit_report"] == 0


def test_complexity_analysis_reuses_declared_surface_metrics_without_ast_parsing(
    monkeypatch,
) -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "BioETL")
    module = snapshot.add_node(
        "module_surface",
        PATH_COMPOSITE_EXAMPLE,
        family_name=FAMILY_APP_COMPOSITE,
        current_cycle_status="current_cycle",
        current_cycle_score=5,
        current_cycle_wip_markers=["wip"],
    )
    class_surface = snapshot.add_node(
        "class_surface",
        "src.bioetl.application.composite.example.ExampleService",
        source_path=PATH_COMPOSITE_EXAMPLE,
    )
    method_surface = snapshot.add_node(
        "method_surface",
        "src.bioetl.application.composite.example.ExampleService.merge",
        source_path=PATH_COMPOSITE_EXAMPLE,
        callable_name="merge",
        branch_count=6,
        nesting_depth=4,
        call_count=5,
        helper_call_count=4,
    )
    pipeline = snapshot.add_node("pipeline_surface", "example_pipeline")
    snapshot.add_relation(module, "DECLARES", class_surface)
    snapshot.add_relation(class_surface, "DECLARES", method_surface)
    snapshot.add_relation(method_surface, "DEPENDS_ON", pipeline)

    monkeypatch.setattr(
        "scripts.memory.sync._read_text",
        lambda _path: "merge helper compat policy",
    )

    def _fail_parse(path: Path) -> None:
        raise AssertionError(
            f"AST parsing should not be used for complexity aggregation: {path}"
        )

    monkeypatch.setattr("scripts.memory.sync._parse_python_ast", _fail_parse)

    _add_complexity_analysis_surfaces(
        snapshot,
        _repo_root(),
        project,
        "2026-04-10",
        {
            "duplication_analysis": {
                "enabled": True,
                "families": {
                    FAMILY_APP_COMPOSITE: {
                        "roots": ["src/bioetl/application/composite"],
                        "package_family": FAMILY_APP_COMPOSITE,
                    }
                },
            },
            "retirement_analysis": {
                "enabled": True,
                "families": [FAMILY_APP_COMPOSITE],
            },
            "complexity_analysis": {
                "enabled": True,
                "families": [FAMILY_APP_COMPOSITE],
                "complexity_score_threshold": 3,
                "removable_score_threshold": 20,
            },
        },
    )

    candidate_key = NodeKey(
        "complexity_candidate",
        "class_surface:src.bioetl.application.composite.example.ExampleService",
    )
    candidate = snapshot.nodes[candidate_key]
    assert candidate.properties["branch_count"] == 6
    assert candidate.properties["nesting_depth"] == 4
    assert candidate.properties["helper_call_count"] == 4


def test_neo4j_http_client_distinguishes_query_runtime_http_errors(monkeypatch) -> None:
    def _raise_http_error(_req: object, _timeout: int = 60) -> object:
        raise error.HTTPError(
            f"{LOCALHOST_HTTP_URI}/db/neo4j/tx/commit",
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"errors":[{"message":"Cypher failed"}]}'),
        )

    monkeypatch.setattr("scripts.memory.sync.request.urlopen", _raise_http_error)
    client = Neo4jHttpClient(LOCALHOST_HTTP_URI, "neo4j", "password", "neo4j")

    try:
        client.execute([], context=CONTEXT_FAST_AUDIT_LABEL)
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected RuntimeError")

    assert CONTEXT_FAST_AUDIT_LABEL in message
    assert "query/runtime error" in message
    assert "transport error" not in message


def test_neo4j_http_client_reports_all_transport_attempts(monkeypatch) -> None:
    responses = [
        error.URLError(TimeoutError("timed out")),
        error.URLError(ConnectionRefusedError(111, "Connection refused")),
    ]

    def _raise_transport_error(_req: object, _timeout: int = 60) -> object:
        raise responses.pop(0)

    monkeypatch.setattr("scripts.memory.sync.request.urlopen", _raise_transport_error)
    client = Neo4jHttpClient(
        HOST_DOCKER_INTERNAL_HTTP_URI, "neo4j", "password", "neo4j"
    )

    try:
        client.execute(
            [],
            context="normalization evidence batch 1/21 pipelines chembl_activity..chembl_activity",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected RuntimeError")

    assert (
        "normalization evidence batch 1/21 pipelines chembl_activity..chembl_activity"
        in message
    )
    assert "attempts:" in message
    assert f"{HOST_DOCKER_INTERNAL_HTTP_URI}/db/neo4j/tx/commit" in message
    assert f"{LOCALHOST_HTTP_URI}/db/neo4j/tx/commit" in message


