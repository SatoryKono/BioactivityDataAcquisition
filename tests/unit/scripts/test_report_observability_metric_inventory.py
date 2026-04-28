"""Unit tests for the observability metric inventory report."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.qa import report_observability_metric_inventory as inventory


def test_collect_metric_inventory_classifies_registry_runtime_and_docs(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_live_counter_total",
                "bioetl_doc_only_total",
                "bioetl_rule_only_total",
            }
        ),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        "\n".join(
            [
                'metrics.increment_counter("bioetl_live_counter_total", labels={})',
                'metrics.increment_counter("legacy_alias_total", labels={})',
            ]
        ),
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text(
        "bioetl_live_counter_total\nbioetl_doc_only_total\nbioetl_unknown_total\n",
        encoding="utf-8",
    )

    rules_dir = tmp_path / "grafana" / "prometheus-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rules.yml").write_text(
        "\n".join(
            [
                "groups:",
                "  - name: test",
                "    rules:",
                "      - record: test_rule",
                "        expr: increase(bioetl_live_counter_total[5m]) or increase(bioetl_rule_only_total[5m])",
            ]
        ),
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == ["bioetl_live_counter_total"]
    assert report["direct_live_metrics"] == ["bioetl_live_counter_total"]
    assert report["helper_backed_live_metrics"] == []
    assert report["registered_without_runtime"] == [
        "bioetl_doc_only_total",
        "bioetl_rule_only_total",
    ]
    assert report["runtime_without_registry"] == []
    assert report["registry_only_metrics"] == [
        "bioetl_doc_only_total",
        "bioetl_rule_only_total",
    ]
    assert report["dead_metrics"] == []
    assert report["documented_without_registry"] == ["bioetl_unknown_total"]
    assert report["documented_without_runtime"] == ["bioetl_doc_only_total"]
    assert report["documented_only_metrics"] == ["bioetl_doc_only_total"]
    assert report["ruled_without_runtime"] == ["bioetl_rule_only_total"]
    assert report["compatibility_alias_candidates"] == ["legacy_alias_total"]
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters["bioetl_live_counter_total"] == [
        "src/bioetl/application/emitters.py"
    ]


def test_filter_documented_metric_mentions_ignores_generated_series_and_group_names() -> (
    None
):
    filtered = inventory._filter_documented_metric_mentions(
        {
            "bioetl_dq_check_duration_ms_bucket": [
                "grafana/prometheus-rules/rules.yml"
            ],
            "bioetl_dq_check_duration_ms": ["docs/03-guides/metrics-monitoring.md"],
            "bioetl_dq_observability": ["grafana/prometheus-rules/rules.yml"],
            "bioetl_runtime_alert_condition_dq_soft_threshold_15m": [
                "grafana/prometheus-rules/rules.yml"
            ],
        },
        registered_metrics=frozenset({"bioetl_dq_check_duration_ms"}),
    )

    assert filtered == {
        "bioetl_dq_check_duration_ms": ["docs/03-guides/metrics-monitoring.md"]
    }


def test_collect_metric_inventory_detects_keyword_metric_name_emitters(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_circuit_breaker_trips_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "infrastructure" / "adapters"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "breaker.py").write_text(
        "\n".join(
            [
                'METRIC_CIRCUIT_BREAKER_TRIPS = "bioetl_circuit_breaker_trips_total"',
                "emit_counter_metric(metrics, metric_name=METRIC_CIRCUIT_BREAKER_TRIPS)",
            ]
        ),
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == ["bioetl_circuit_breaker_trips_total"]
    assert report["direct_live_metrics"] == []
    assert report["helper_backed_live_metrics"] == [
        "bioetl_circuit_breaker_trips_total"
    ]
    assert report["registered_without_runtime"] == []
    assert report["runtime_without_registry"] == []
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters == {}
    helper_emitters = report["helper_backed_emitters"]
    assert isinstance(helper_emitters, dict)
    assert helper_emitters["bioetl_circuit_breaker_trips_total"] == [
        "src/bioetl/infrastructure/adapters/breaker.py"
    ]


def test_collect_metric_inventory_tracks_helper_backed_emitters(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_direct_live_total",
                "bioetl_helper_live_total",
                "bioetl_dead_metric_total",
            }
        ),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        "\n".join(
            [
                'DIRECT_METRIC = "bioetl_direct_live_total"',
                'HELPER_METRIC = "bioetl_helper_live_total"',
                "metrics.increment_counter(DIRECT_METRIC, labels={})",
                "emit_metric(metrics, HELPER_METRIC)",
            ]
        ),
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text(
        "bioetl_dead_metric_total\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == [
        "bioetl_direct_live_total",
        "bioetl_helper_live_total",
    ]
    assert report["direct_live_metrics"] == ["bioetl_direct_live_total"]
    assert report["helper_backed_live_metrics"] == ["bioetl_helper_live_total"]
    assert report["registered_without_runtime"] == ["bioetl_dead_metric_total"]
    assert report["runtime_without_registry"] == []
    assert report["dead_metrics"] == []
    helper_emitters = report["helper_backed_emitters"]
    assert isinstance(helper_emitters, dict)
    assert helper_emitters["bioetl_helper_live_total"] == [
        "src/bioetl/application/emitters.py"
    ]


def test_collect_metric_inventory_detects_runtime_metric_without_registry(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_registered_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        "\n".join(
            [
                'metrics.increment_counter("bioetl_registered_total", labels={})',
                'metrics.increment_counter("bioetl_unregistered_total", labels={})',
            ]
        ),
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == ["bioetl_registered_total"]
    assert report["runtime_without_registry"] == ["bioetl_unregistered_total"]


def test_validate_metric_inventory_reports_unallowed_drift() -> None:
    report = {
        "registered_without_runtime": ["bioetl_allowed_total", "bioetl_dead_total"],
        "runtime_without_registry": ["bioetl_runtime_gap_total"],
        "dead_metrics": [],
        "documented_without_registry": ["bioetl_doc_gap_total"],
        "rules_without_registry": [],
    }

    violations = inventory.validate_metric_inventory(
        report,
        allowlist={"registered_without_runtime": {"bioetl_allowed_total"}},
    )

    assert violations == {
        "documented_without_registry": ["bioetl_doc_gap_total"],
        "registered_without_runtime": ["bioetl_dead_total"],
        "runtime_without_registry": ["bioetl_runtime_gap_total"],
    }


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
        },
    )

    try:
        inventory.main(
            [
                "--check",
                "--json",
                "--repo-root",
                str(tmp_path),
                "--allowlist",
                "missing.yaml",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("metric drift check should fail closed")


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
        },
    )
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "allowed:\n  registered_without_runtime:\n    - bioetl_allowed_total\n",
        encoding="utf-8",
    )

    inventory.main(
        [
            "--check",
            "--json",
            "--repo-root",
            str(tmp_path),
            "--allowlist",
            str(allowlist),
        ]
    )
