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

    assert report["declared_metrics"] == [
        "bioetl_doc_only_total",
        "bioetl_live_counter_total",
        "bioetl_rule_only_total",
    ]
    assert report["emitted_metrics"] == ["bioetl_live_counter_total"]
    assert report["dashboarded_metrics"] == [
        "bioetl_doc_only_total",
        "bioetl_live_counter_total",
    ]
    assert report["alerted_metrics"] == [
        "bioetl_live_counter_total",
        "bioetl_rule_only_total",
    ]
    assert report["unused_declared_metrics"] == [
        "bioetl_doc_only_total",
        "bioetl_rule_only_total",
    ]
    assert report["emitted_without_declaration"] == []
    assert report["dashboarded_without_declaration"] == ["bioetl_unknown_total"]
    assert report["alerted_without_declaration"] == []
    assert report["dashboarded_without_emission"] == ["bioetl_doc_only_total"]
    assert report["alerted_without_emission"] == ["bioetl_rule_only_total"]
    assert report["runtime_cardinality_review_required"] == []
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


def test_metric_inventory_filters_non_metric_alias_noise(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_live_counter_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        "\n".join(
            [
                'metrics.increment_counter("bioetl_live_counter_total", labels={})',
                'emit_metric(metrics, "legacy_alias_total")',
                'emit_metric(metrics, "Legacy alias with spaces")',
                'emit_metric(metrics, "")',
                'emit_metric(metrics, "status/detail")',
                'emit_metric(metrics, "record_count")',
                'emit_metric(metrics, "dq_status")',
                'emit_metric(metrics, "write_duration_ms")',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["compatibility_alias_candidates"] == ["legacy_alias_total"]
    assert report["alias_emitters"] == {
        "legacy_alias_total": ["src/bioetl/application/emitters.py"]
    }


def test_collect_metric_inventory_detects_direct_keyword_name_emitters(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_publication_raw_vocab_unknown_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application" / "pipelines" / "common"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "publication_vocab_observability.py").write_text(
        "\n".join(
            [
                'PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL = "bioetl_publication_raw_vocab_unknown_total"',
                "",
                "def emit(metrics):",
                "    metrics.increment_counter(",
                "        name=PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL,",
                "        value=1,",
                "        labels={'pipeline': 'p', 'provider': 'x', 'field': 'y', 'handling': 'z'},",
                "    )",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == ["bioetl_publication_raw_vocab_unknown_total"]
    assert report["direct_live_metrics"] == [
        "bioetl_publication_raw_vocab_unknown_total"
    ]
    assert report["registered_without_runtime"] == []


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


def test_collect_metric_inventory_resolves_cross_file_class_metric_constants(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_postrun_phase_events_total",
                "bioetl_postrun_phase_duration_seconds",
            }
        ),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application" / "postrun"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "service.py").write_text(
        "\n".join(
            [
                "class PostrunService:",
                '    METRIC_POSTRUN_PHASE_EVENTS_TOTAL = "bioetl_postrun_phase_events_total"',
                '    METRIC_POSTRUN_PHASE_DURATION_SECONDS = "bioetl_postrun_phase_duration_seconds"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (runtime_dir / "_support.py").write_text(
        "\n".join(
            [
                "class PostrunServiceSupportMixin:",
                "    def emit(self, metrics):",
                "        metrics.increment_counter(self.METRIC_POSTRUN_PHASE_EVENTS_TOTAL, labels={})",
                "        metrics.observe_histogram(self.METRIC_POSTRUN_PHASE_DURATION_SECONDS, value=1.0, labels={})",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["direct_live_metrics"] == [
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_postrun_phase_events_total",
    ]
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters["bioetl_postrun_phase_events_total"] == [
        "src/bioetl/application/postrun/_support.py"
    ]
    assert runtime_emitters["bioetl_postrun_phase_duration_seconds"] == [
        "src/bioetl/application/postrun/_support.py"
    ]
    assert report["registered_without_runtime"] == []


def test_collect_metric_inventory_resolves_helper_metric_keyword_bindings(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_postrun_phase_events_total",
                "bioetl_postrun_phase_duration_seconds",
            }
        ),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application" / "core" / "postrun"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "service.py").write_text(
        "\n".join(
            [
                "class PostrunService:",
                '    METRIC_POSTRUN_PHASE_EVENTS_TOTAL = "bioetl_postrun_phase_events_total"',
                '    METRIC_POSTRUN_PHASE_DURATION_SECONDS = "bioetl_postrun_phase_duration_seconds"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (runtime_dir / "_service_support.py").write_text(
        "\n".join(
            [
                "class PostrunServiceSupportMixin:",
                "    def emit(self):",
                "        emit_postrun_phase_observability(",
                "            phase_events_metric=self.METRIC_POSTRUN_PHASE_EVENTS_TOTAL,",
                "            phase_duration_metric=self.METRIC_POSTRUN_PHASE_DURATION_SECONDS,",
                "        )",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["helper_backed_live_metrics"] == [
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_postrun_phase_events_total",
    ]
    helper_emitters = report["helper_backed_emitters"]
    assert isinstance(helper_emitters, dict)
    assert helper_emitters["bioetl_postrun_phase_events_total"] == [
        "src/bioetl/application/core/postrun/_service_support.py"
    ]
    assert helper_emitters["bioetl_postrun_phase_duration_seconds"] == [
        "src/bioetl/application/core/postrun/_service_support.py"
    ]
    assert report["registered_without_runtime"] == []


def test_collect_metric_inventory_records_static_prometheus_collector_emitters(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_metrics_publication_events_total"}),
    )

    metrics_dir = tmp_path / "src" / "bioetl" / "infrastructure" / "observability"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "server.py").write_text(
        "METRICS_PUBLICATION_EVENTS_TOTAL.labels(status='success').inc()\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["direct_live_metrics"] == ["bioetl_metrics_publication_events_total"]
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters["bioetl_metrics_publication_events_total"] == [
        "src/bioetl/infrastructure/observability/server.py"
    ]
    assert report["registered_without_runtime"] == []


def test_collect_metric_inventory_detects_direct_prometheus_collectors(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_gold_write_attempts_total",
                "bioetl_gold_write_duration_seconds",
                "bioetl_gold_write_outcomes_total",
            }
        ),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "infrastructure" / "storage" / "gold"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "writer.py").write_text(
        "\n".join(
            [
                "from bioetl.infrastructure.observability.metrics import (",
                "    GOLD_WRITE_ATTEMPTS_TOTAL,",
                "    GOLD_WRITE_DURATION_SECONDS,",
                "    GOLD_WRITE_OUTCOMES_TOTAL,",
                ")",
                "",
                "def emit(duration: float) -> None:",
                "    GOLD_WRITE_ATTEMPTS_TOTAL.labels(",
                "        pipeline='p', table='t', mode='append'",
                "    ).inc()",
                "    GOLD_WRITE_OUTCOMES_TOTAL.labels(",
                "        pipeline='p', table='t', mode='append', status='success'",
                "    ).inc()",
                "    GOLD_WRITE_DURATION_SECONDS.labels(",
                "        pipeline='p', table='t', mode='append', status='success'",
                "    ).observe(duration)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == [
        "bioetl_gold_write_attempts_total",
        "bioetl_gold_write_duration_seconds",
        "bioetl_gold_write_outcomes_total",
    ]
    assert report["registered_without_runtime"] == []
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters["bioetl_gold_write_attempts_total"] == [
        "src/bioetl/infrastructure/storage/gold/writer.py"
    ]
    assert runtime_emitters["bioetl_gold_write_outcomes_total"] == [
        "src/bioetl/infrastructure/storage/gold/writer.py"
    ]
    assert runtime_emitters["bioetl_gold_write_duration_seconds"] == [
        "src/bioetl/infrastructure/storage/gold/writer.py"
    ]


def test_resolve_imported_string_bindings_skips_non_constant_imports(
    monkeypatch: object,
) -> None:
    tree = inventory.ast.parse("from bioetl.domain.types import RunID\n")

    def _unexpected_module_lookup(*args: object, **kwargs: object) -> object:
        raise AssertionError("non-constant imports should not trigger module reads")

    monkeypatch.setattr(
        inventory,
        "_module_string_bindings",
        _unexpected_module_lookup,
    )

    resolved = inventory._resolve_imported_string_bindings(
        tree,
        repo_root=Path("/tmp/repo"),
        cache={},
    )

    assert resolved == {}


def test_collect_metric_inventory_honors_declared_recording_rule_metrics(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_live_counter_total"}),
    )
    monkeypatch.setattr(
        inventory,
        "_DEFAULT_DECLARED_METRIC_DEFINITIONS",
        Path("configs/quality/observability_metric_declarations.yaml"),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        'metrics.increment_counter("bioetl_live_counter_total", labels={})\n',
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text(
        "bioetl_live_counter_total\nbioetl_runtime_current_status\n",
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
                "      - record: bioetl_runtime_current_status",
                "        expr: max(bioetl_live_counter_total)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config_dir = tmp_path / "configs" / "quality"
    config_dir.mkdir(parents=True)
    (config_dir / "observability_metric_declarations.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "policy_scope: observability_metric_declarations",
                "recording_rule_metrics:",
                "  - bioetl_runtime_current_status",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert "bioetl_runtime_current_status" in report["declared_metrics"]
    assert report["documented_without_registry"] == []
    assert report["rules_without_registry"] == []
    assert report["registered_without_runtime"] == []
    assert report["dead_metrics"] == []


def test_collect_metric_inventory_flags_multi_emitter_cardinality_review_candidates(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_hotspot_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    for idx in range(3):
        (runtime_dir / f"emitters_{idx}.py").write_text(
            'metrics.increment_counter("bioetl_hotspot_total", labels={})\n',
            encoding="utf-8",
        )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["runtime_cardinality_review_required"] == ["bioetl_hotspot_total"]


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


def test_collect_metric_inventory_detects_direct_label_contract_violations(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_registered_total"}),
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_registered_total": frozenset({"pipeline", "run_type"})},
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        'metrics.increment_counter("bioetl_registered_total", 1, {"pipeline": "p", "extra": "x"})\n',
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    violations = report["runtime_label_contract_violations"]
    assert isinstance(violations, list)
    assert len(violations) == 1
    assert (
        "bioetl_registered_total @ src/bioetl/application/emitters.py:1"
        in (violations[0])
    )
    assert "missing=['run_type']" in violations[0]
    assert "extra=['extra']" in violations[0]


def test_collect_metric_inventory_accepts_matching_direct_label_contracts(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_registered_total"}),
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_registered_total": frozenset({"pipeline", "run_type"})},
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        "\n".join(
            [
                'metrics.increment_counter("bioetl_registered_total", 1, labels={',
                '    "pipeline": "p",',
                '    "run_type": "incremental",',
                "})",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["runtime_label_contract_violations"] == []


def test_collect_metric_inventory_flags_declared_risky_label_review_candidates(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset(
            {
                "bioetl_reviewed_total",
                "bioetl_plain_total",
            }
        ),
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {
            "bioetl_reviewed_total": frozenset({"pipeline", "table"}),
            "bioetl_plain_total": frozenset({"pipeline", "status"}),
        },
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["declared_risky_label_review_required"] == ["bioetl_reviewed_total"]


def test_validate_metric_inventory_reports_unallowed_drift() -> None:
    report = {
        "registered_without_runtime": ["bioetl_allowed_total", "bioetl_dead_total"],
        "runtime_without_registry": ["bioetl_runtime_gap_total"],
        "dead_metrics": [],
        "documented_without_registry": ["bioetl_doc_gap_total"],
        "rules_without_registry": [],
        "runtime_cardinality_review_required": ["bioetl_hotspot_total"],
        "declared_risky_label_review_required": ["bioetl_table_total"],
        "runtime_label_contract_violations": ["bioetl_bad_total @ src/x.py:1"],
        "runtime_label_contract_unresolved": ["bioetl_unknown_total @ src/y.py:1"],
    }

    violations = inventory.validate_metric_inventory(
        report,
        allowlist={
            "registered_without_runtime": {"bioetl_allowed_total"},
            "runtime_cardinality_review_required": set(),
            "declared_risky_label_review_required": set(),
        },
    )

    assert violations == {
        "declared_risky_label_review_required": ["bioetl_table_total"],
        "documented_without_registry": ["bioetl_doc_gap_total"],
        "registered_without_runtime": ["bioetl_dead_total"],
        "runtime_without_registry": ["bioetl_runtime_gap_total"],
        "runtime_cardinality_review_required": ["bioetl_hotspot_total"],
        "runtime_label_contract_violations": ["bioetl_bad_total @ src/x.py:1"],
        "runtime_label_contract_unresolved": ["bioetl_unknown_total @ src/y.py:1"],
    }


def test_validate_metric_inventory_allows_unresolved_label_contracts_by_metric_name() -> (
    None
):
    report = {
        "runtime_label_contract_unresolved": [
            "bioetl_unknown_total @ src/y.py:1",
            "bioetl_unknown_total @ src/z.py:2",
        ]
    }

    violations = inventory.validate_metric_inventory(
        report,
        allowlist={
            "runtime_label_contract_unresolved": {"bioetl_unknown_total"},
        },
    )

    assert violations == {}


def test_filter_declared_label_contract_metrics_suppresses_declared_rows() -> None:
    filtered = inventory._filter_declared_label_contract_metrics(
        [
            "bioetl_known_total @ src/a.py:1",
            "bioetl_other_total @ src/b.py:2",
        ],
        {"bioetl_known_total"},
    )

    assert filtered == ["bioetl_other_total @ src/b.py:2"]


def test_load_declared_metric_definitions_supports_label_contract_metrics(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "configs/quality"
    config_dir.mkdir(parents=True)
    (config_dir / "observability_metric_declarations.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "policy_scope: observability_metric_declarations",
                "recording_rule_metrics:",
                "  - bioetl_recording_rule_total",
                "declared_label_contract_metrics:",
                "  - bioetl_known_total",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = inventory._load_declared_metric_definitions(tmp_path)

    assert loaded["recording_rule_metrics"] == {"bioetl_recording_rule_total"}
    assert loaded["declared_label_contract_metrics"] == {"bioetl_known_total"}


def test_load_drift_allowlist_supports_metadata_entries_for_risky_labels(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "\n".join(
            [
                "allowed:",
                "  declared_risky_label_review_required:",
                "    - metric: bioetl_table_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Reviewed table-scoped metric with bounded storage surface"',
                "      review_date: '2026-09-30'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = inventory._load_drift_allowlist(allowlist)

    assert loaded["declared_risky_label_review_required"] == {"bioetl_table_total"}


def test_load_drift_allowlist_supports_metadata_entries_for_cardinality_reviews(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "\n".join(
            [
                "allowed:",
                "  runtime_cardinality_review_required:",
                "    - metric: bioetl_hotspot_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Static multi-emitter fanout is expected for this family"',
                "      review_date: '2026-09-30'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = inventory._load_drift_allowlist(allowlist)

    assert loaded["runtime_cardinality_review_required"] == {"bioetl_hotspot_total"}


def test_load_drift_allowlist_rejects_metadata_free_cardinality_entries(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "\n".join(
            [
                "allowed:",
                "  runtime_cardinality_review_required:",
                "    - bioetl_hotspot_total",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        inventory._load_drift_allowlist(allowlist)
    except ValueError as exc:
        assert "metric/owner/reason/review_date" in str(exc)
    else:  # pragma: no cover - defensive branch for clearer failure output
        raise AssertionError(
            "runtime_cardinality_review_required must reject string-only allowlist entries"
        )


def test_load_drift_allowlist_rejects_expired_cardinality_review_dates(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "\n".join(
            [
                "allowed:",
                "  runtime_cardinality_review_required:",
                "    - metric: bioetl_hotspot_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Static multi-emitter fanout is expected for this family"',
                "      review_date: '2000-01-01'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        inventory._load_drift_allowlist(allowlist)
    except ValueError as exc:
        assert "expired review_date" in str(exc)
    else:  # pragma: no cover - defensive branch for clearer failure output
        raise AssertionError(
            "runtime_cardinality_review_required must reject expired lifecycle entries"
        )


def test_load_drift_allowlist_rejects_non_iso_review_dates(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "\n".join(
            [
                "allowed:",
                "  runtime_cardinality_review_required:",
                "    - metric: bioetl_hotspot_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Static multi-emitter fanout is expected for this family"',
                "      review_date: '09/30/2026'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        inventory._load_drift_allowlist(allowlist)
    except ValueError as exc:
        assert "invalid review_date" in str(exc)
    else:  # pragma: no cover - defensive branch for clearer failure output
        raise AssertionError(
            "runtime_cardinality_review_required must reject non-ISO review_date values"
        )


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
