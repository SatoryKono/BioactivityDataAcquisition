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
"""CLI/main-path unit tests for the observability metric inventory report."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace
from urllib.error import URLError

import pytest

from scripts.engineering.qa import report_observability_metric_inventory as inventory

pytestmark = pytest.mark.repo_backed

def test_main_check_exits_nonzero_for_metric_drift(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "collect_metric_inventory",
        lambda _repo_root: {
            "registered_without_runtime": ["bioetl_dead_total"],
            "runtime_without_registry": [],
            "dead_metrics": [],
            "documented_without_registry": [],
            "rules_without_registry": [],
            "runtime_cardinality_review_required": [],
        },
    )

    exit_code = inventory.main(
        [
            "--check",
            "--json",
            "--repo-root",
            str(tmp_path),
            "--allowlist",
            "missing.yaml",
        ]
    )
    assert exit_code == 1


def test_main_check_allows_explicit_baseline(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "collect_metric_inventory",
        lambda _repo_root: {
            "registered_without_runtime": ["bioetl_allowed_total"],
            "runtime_without_registry": [],
            "dead_metrics": [],
            "documented_without_registry": [],
            "rules_without_registry": [],
            "runtime_cardinality_review_required": [],
        },
    )
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "allowed:\n  registered_without_runtime:\n    - bioetl_allowed_total\n",
        encoding="utf-8",
    )

    exit_code = inventory.main(
        [
            "--check",
            "--json",
            "--repo-root",
            str(tmp_path),
            "--allowlist",
            str(allowlist),
        ]
    )
    assert exit_code == 0


def test_main_write_evidence_writes_replayable_json_artifact(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "collect_metric_inventory",
        lambda _repo_root: {
            "declared_metrics": ["bioetl_example_total"],
            "emitted_metrics": ["bioetl_example_total"],
            "dashboarded_metrics": [],
            "alerted_metrics": [],
            "unused_declared_metrics": [],
            "emitted_without_declaration": [],
            "dashboarded_without_declaration": [],
            "alerted_without_declaration": [],
            "dashboarded_without_emission": [],
            "alerted_without_emission": [],
            "runtime_cardinality_review_required": [],
            "declared_risky_label_review_required": [],
            "runtime_label_contract_violations": [],
            "runtime_label_contract_unresolved": [],
            "live_metrics": ["bioetl_example_total"],
            "direct_live_metrics": ["bioetl_example_total"],
            "helper_backed_live_metrics": [],
            "registered_without_runtime": [],
            "runtime_without_registry": [],
            "registry_only_metrics": [],
            "dead_metrics": [],
            "documented_without_registry": [],
            "rules_without_registry": [],
            "documented_without_runtime": [],
            "documented_only_metrics": [],
            "ruled_without_runtime": [],
            "compatibility_alias_candidates": [],
            "runtime_emitters": {},
            "helper_backed_emitters": {},
            "docs_mentions": {},
            "rules_mentions": {},
            "alias_emitters": {},
        },
    )
    evidence_path = tmp_path / "evidence" / "observability-runtime-cardinality.json"

    exit_code = inventory.main(
        [
            "--repo-root",
            str(tmp_path),
            "--write-evidence",
            str(evidence_path),
        ]
    )

    assert exit_code == 0
    assert evidence_path.exists()
    payload = evidence_path.read_text(encoding="utf-8")
    assert '"declared_metrics"' in payload
    assert "bioetl_example_total" in payload


def test_build_runtime_cardinality_review_summary_degrades_without_prometheus_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(inventory._PROMETHEUS_BASE_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(inventory._PROMETHEUS_BEARER_TOKEN_ENV_VAR, raising=False)
    monkeypatch.setattr(
        inventory,
        "_load_runtime_cardinality_thresholds",
        lambda _repo_root: {"bioetl_hotspot_total": 42},
    )

    summary = inventory._build_runtime_cardinality_review_summary(
        {
            "runtime_cardinality_reviewed": ["bioetl_hotspot_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
        },
        repo_root=tmp_path,
        prometheus_base_url=None,
    )

    assert summary["status"] == "degraded"
    assert summary["mode"] == "static_only"
    assert summary["prometheus_base_url_source"] == "unconfigured"
    assert summary["live_observed_series"] == {}
    assert summary["query_errors"] == {}


def test_build_runtime_cardinality_review_summary_uses_local_fallback_for_pr_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(inventory._PROMETHEUS_BASE_URL_ENV_VAR, raising=False)
    monkeypatch.setattr(
        inventory,
        "_load_runtime_cardinality_thresholds",
        lambda _repo_root: {"bioetl_hotspot_total": 42},
    )

    summary = inventory._build_runtime_cardinality_review_summary(
        {
            "runtime_cardinality_reviewed": ["bioetl_hotspot_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
            "runtime_cardinality_observed_series": {"bioetl_hotspot_total": 12},
        },
        repo_root=tmp_path,
        prometheus_base_url=None,
        allow_local_cardinality_fallback=True,
    )

    assert summary["status"] == "passed"
    assert summary["mode"] == "local_cardinality_fallback"
    assert summary["local_observed_series"] == {"bioetl_hotspot_total": 12}
    assert summary["local_threshold_violations"] == []


def test_build_runtime_cardinality_review_summary_passes_with_live_prometheus_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "_load_runtime_cardinality_thresholds",
        lambda _repo_root: {"bioetl_hotspot_total": 42},
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_hotspot_total": frozenset({"pipeline"})},
    )
    monkeypatch.setattr(
        inventory,
        "_query_prometheus_scalar",
        lambda **_kwargs: 12,
    )
    monkeypatch.setattr(
        inventory,
        "_query_prometheus_label_values",
        lambda **_kwargs: {"pipeline": ["chembl_activity", "pubchem_compound"]},
    )

    summary = inventory._build_runtime_cardinality_review_summary(
        {
            "runtime_cardinality_reviewed": ["bioetl_hotspot_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
        },
        repo_root=tmp_path,
        prometheus_base_url="http://prometheus.example",
    )

    assert summary["status"] == "passed"
    assert summary["mode"] == "live_review"
    assert summary["live_observed_series"] == {"bioetl_hotspot_total": 12}
    assert summary["live_threshold_violations"] == []
    assert summary["query_errors"] == {}
    assert summary["label_keys"] == {"bioetl_hotspot_total": ["pipeline"]}
    assert summary["observed_label_values"] == {
        "bioetl_hotspot_total": {"pipeline": ["chembl_activity", "pubchem_compound"]}
    }


def test_build_runtime_cardinality_review_summary_fails_on_live_threshold_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "_load_runtime_cardinality_thresholds",
        lambda _repo_root: {"bioetl_hotspot_total": 3},
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_hotspot_total": frozenset()},
    )
    monkeypatch.setattr(
        inventory,
        "_query_prometheus_scalar",
        lambda **_kwargs: 5,
    )
    monkeypatch.setattr(
        inventory,
        "_query_prometheus_label_values",
        lambda **_kwargs: {},
    )

    summary = inventory._build_runtime_cardinality_review_summary(
        {
            "runtime_cardinality_reviewed": ["bioetl_hotspot_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
        },
        repo_root=tmp_path,
        prometheus_base_url="http://prometheus.example",
    )

    assert summary["status"] == "failed"
    assert summary["live_threshold_violations"] == [
        "bioetl_hotspot_total observed_series_count=5 approved_max_series=3"
    ]


def test_query_prometheus_scalar_parses_vector_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self, *_args: object, **_kwargs: object) -> bytes:
            return b'{"status":"success","data":{"resultType":"vector","result":[{"metric":{},"value":[0,"7"]}]}}'

    monkeypatch.setattr(inventory, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    observed = inventory._query_prometheus_scalar(
        prometheus_base_url="http://prometheus.example",
        query="count(test_metric)",
        bearer_token="",
    )

    assert observed == 7


def test_query_prometheus_label_values_records_watch_list_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self, *_args: object, **_kwargs: object) -> bytes:
            return (
                b'{"status":"success","data":{"resultType":"vector","result":['
                b'{"metric":{"__name__":"bioetl_hotspot_total","pipeline":"b",'
                b'"status":"ok"},"value":[0,"1"]},'
                b'{"metric":{"__name__":"bioetl_hotspot_total","pipeline":"a",'
                b'"status":"ok"},"value":[0,"1"]}]}}'
            )

    monkeypatch.setattr(inventory, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    observed = inventory._query_prometheus_label_values(
        prometheus_base_url="http://prometheus.example",
        metric_name="bioetl_hotspot_total",
        label_names=frozenset({"pipeline", "status"}),
        bearer_token="",
    )

    assert observed == {"pipeline": ["a", "b"], "status": ["ok"]}


@pytest.mark.parametrize(
    ("label_names", "expected"),
    [
        (
            frozenset({"pipeline", "run_type"}),
            "count(count by (pipeline, run_type) "
            '({__name__=~"^bioetl_hotspot_total'
            '(?:_bucket|_sum|_count|_created)?$"}))',
        ),
        (
            frozenset(),
            "count(count without (__name__) "
            '({__name__=~"^bioetl_hotspot_total'
            '(?:_bucket|_sum|_count|_created)?$"}))',
        ),
    ],
)
def test_prometheus_cardinality_query_preserves_strict_absent_series_semantics(
    label_names: frozenset[str], expected: str
) -> None:
    assert (
        inventory._prometheus_cardinality_query(
            "bioetl_hotspot_total", label_names=label_names, allow_absent_zero=False
        )
        == expected
    )


@pytest.mark.parametrize(
    ("label_names", "expected"),
    [
        (
            frozenset({"pipeline", "run_type"}),
            "count(count by (pipeline, run_type) "
            '({__name__=~"^bioetl_hotspot_total'
            '(?:_bucket|_sum|_count|_created)?$"})) or vector(0)',
        ),
        (
            frozenset(),
            "count(count without (__name__) "
            '({__name__=~"^bioetl_hotspot_total'
            '(?:_bucket|_sum|_count|_created)?$"})) or vector(0)',
        ),
    ],
)
def test_prometheus_cardinality_query_treats_absent_series_as_zero_when_enabled(
    label_names: frozenset[str], expected: str
) -> None:
    assert (
        inventory._prometheus_cardinality_query(
            "bioetl_hotspot_total", label_names=label_names, allow_absent_zero=True
        )
        == expected
    )


def test_query_prometheus_scalar_raises_runtime_error_for_url_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_url_error(*_args: object, **_kwargs: object) -> None:
        raise URLError("connection refused")

    monkeypatch.setattr(inventory, "urlopen", raise_url_error)

    with pytest.raises(RuntimeError, match="connection refused"):
        inventory._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example",
            query="count(test_metric)",
            bearer_token="",
        )


def test_main_writes_runtime_cardinality_review_artifacts_and_step_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "collect_metric_inventory",
        lambda _repo_root: {
            "declared_metrics": ["bioetl_example_total"],
            "emitted_metrics": ["bioetl_example_total"],
            "dashboarded_metrics": [],
            "alerted_metrics": [],
            "unused_declared_metrics": [],
            "emitted_without_declaration": [],
            "dashboarded_without_declaration": [],
            "alerted_without_declaration": [],
            "dashboarded_without_emission": [],
            "alerted_without_emission": [],
            "runtime_cardinality_reviewed": ["bioetl_example_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
            "declared_risky_label_review_required": [],
            "runtime_label_contract_violations": [],
            "runtime_label_contract_unresolved": [],
            "live_metrics": ["bioetl_example_total"],
            "direct_live_metrics": ["bioetl_example_total"],
            "helper_backed_live_metrics": [],
            "registered_without_runtime": [],
            "runtime_without_registry": [],
            "registry_only_metrics": [],
            "dead_metrics": [],
            "documented_without_registry": [],
            "rules_without_registry": [],
            "documented_without_runtime": [],
            "documented_only_metrics": [],
            "ruled_without_runtime": [],
            "compatibility_alias_candidates": [],
            "runtime_emitters": {},
            "helper_backed_emitters": {},
            "docs_mentions": {},
            "rules_mentions": {},
            "alias_emitters": {},
        },
    )
    monkeypatch.setattr(
        inventory,
        "_build_runtime_cardinality_review_summary",
        lambda *_args, **_kwargs: {
            "status": "degraded",
            "mode": "static_only",
            "prometheus_base_url_source": "unconfigured",
            "reviewed_metrics": ["bioetl_example_total"],
            "review_required_metrics": [],
            "degraded_reasons": ["missing BIOETL_OBSERVABILITY_PROMETHEUS_URL"],
            "live_threshold_violations": [],
            "query_errors": {},
        },
    )

    evidence_path = tmp_path / "evidence.json"
    review_path = tmp_path / "review.json"
    summary_path = tmp_path / "summary.md"

    exit_code = inventory.main(
        [
            "--repo-root",
            str(tmp_path),
            "--write-evidence",
            str(evidence_path),
            "--review-json-out",
            str(review_path),
            "--summary-out",
            str(summary_path),
        ]
    )

    assert exit_code == 0
    assert evidence_path.exists()
    assert review_path.exists()
    assert summary_path.exists()
    assert "Observability Runtime Cardinality Review" in summary_path.read_text(
        encoding="utf-8"
    )


def test_main_can_fail_fast_when_runtime_cardinality_review_degrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "collect_metric_inventory",
        lambda _repo_root: {
            "declared_metrics": ["bioetl_example_total"],
            "emitted_metrics": ["bioetl_example_total"],
            "dashboarded_metrics": [],
            "alerted_metrics": [],
            "unused_declared_metrics": [],
            "emitted_without_declaration": [],
            "dashboarded_without_declaration": [],
            "alerted_without_declaration": [],
            "dashboarded_without_emission": [],
            "alerted_without_emission": [],
            "runtime_cardinality_reviewed": ["bioetl_example_total"],
            "runtime_cardinality_review_required": [],
            "runtime_cardinality_threshold_violations": [],
            "declared_risky_label_review_required": [],
            "runtime_label_contract_violations": [],
            "runtime_label_contract_unresolved": [],
            "live_metrics": ["bioetl_example_total"],
            "direct_live_metrics": ["bioetl_example_total"],
            "helper_backed_live_metrics": [],
            "registered_without_runtime": [],
            "runtime_without_registry": [],
            "registry_only_metrics": [],
            "dead_metrics": [],
            "documented_without_registry": [],
            "rules_without_registry": [],
            "documented_without_runtime": [],
            "documented_only_metrics": [],
            "ruled_without_runtime": [],
            "compatibility_alias_candidates": [],
            "runtime_emitters": {},
            "helper_backed_emitters": {},
            "docs_mentions": {},
            "rules_mentions": {},
            "alias_emitters": {},
        },
    )
    monkeypatch.setattr(
        inventory,
        "_build_runtime_cardinality_review_summary",
        lambda *_args, **_kwargs: {
            "status": "degraded",
            "mode": "static_only",
            "prometheus_base_url_source": "unconfigured",
            "reviewed_metrics": ["bioetl_example_total"],
            "review_required_metrics": [],
            "degraded_reasons": ["missing BIOETL_OBSERVABILITY_PROMETHEUS_URL"],
            "live_threshold_violations": [],
            "query_errors": {},
        },
    )

    review_path = tmp_path / "review.json"

    exit_code = inventory.main(
        [
            "--repo-root",
            str(tmp_path),
            "--review-json-out",
            str(review_path),
            "--fail-on-degraded-live-review",
        ]
    )

    assert exit_code == 1
    assert review_path.exists()


def test_main_builds_cardinality_review_before_writing_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provenance must be captured before --write-evidence dirties the tree (#9145)."""
    from scripts.engineering.qa import observability_metric_inventory_cli as cli

    order: list[str] = []
    fake_report = {
        "declared_metrics": ["bioetl_example_total"],
        "emitted_metrics": ["bioetl_example_total"],
        "dashboarded_metrics": [],
        "alerted_metrics": [],
        "unused_declared_metrics": [],
        "emitted_without_declaration": [],
        "dashboarded_without_declaration": [],
        "alerted_without_declaration": [],
        "dashboarded_without_emission": [],
        "alerted_without_emission": [],
        "runtime_cardinality_reviewed": ["bioetl_example_total"],
        "runtime_cardinality_review_required": [],
        "runtime_cardinality_threshold_violations": [],
        "declared_risky_label_review_required": [],
        "runtime_label_contract_violations": [],
        "runtime_label_contract_unresolved": [],
        "live_metrics": ["bioetl_example_total"],
        "direct_live_metrics": ["bioetl_example_total"],
        "helper_backed_live_metrics": [],
        "registered_without_runtime": [],
        "runtime_without_registry": [],
        "registry_only_metrics": [],
        "dead_metrics": [],
        "documented_without_registry": [],
        "rules_without_registry": [],
        "documented_without_runtime": [],
        "documented_only_metrics": [],
        "ruled_without_runtime": [],
        "compatibility_alias_candidates": [],
        "runtime_emitters": {},
        "helper_backed_emitters": {},
        "docs_mentions": {},
        "rules_mentions": {},
        "alias_emitters": {},
    }
    monkeypatch.setattr(
        inventory, "collect_metric_inventory", lambda _repo_root: fake_report
    )

    def fake_build(*_args: object, **_kwargs: object) -> dict[str, object]:
        order.append("build_review")
        return {
            "status": "passed",
            "mode": "local_cardinality_fallback",
            "prometheus_base_url_source": "unconfigured",
            "reviewed_metrics": ["bioetl_example_total"],
            "review_required_metrics": [],
            "degraded_reasons": [],
            "live_threshold_violations": [],
            "query_errors": {},
        }

    def fake_write_evidence(*_args: object, **_kwargs: object) -> None:
        order.append("write_evidence")

    monkeypatch.setattr(
        inventory, "_build_runtime_cardinality_review_summary", fake_build
    )
    monkeypatch.setattr(cli, "_write_evidence_report", fake_write_evidence)

    evidence_path = tmp_path / "evidence.json"
    review_path = tmp_path / "review.json"
    exit_code = inventory.main(
        [
            "--repo-root",
            str(tmp_path),
            "--write-evidence",
            str(evidence_path),
            "--review-json-out",
            str(review_path),
        ]
    )
    assert exit_code == 0
    assert order == ["build_review", "write_evidence"]
    assert review_path.exists()


def test_direct_module_entrypoint_json_bootstraps_without_circular_import() -> None:
    """#8774: `python -m scripts.engineering.qa.report_observability_metric_inventory`."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_observability_metric_inventory",
            "--repo-root",
            str(inventory._REPO_ROOT),
            "--json",
        ],
        cwd=inventory._REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
