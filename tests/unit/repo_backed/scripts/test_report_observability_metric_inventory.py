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
"""Unit tests for the observability metric inventory report."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.engineering.qa import observability_metric_inventory_scan as inventory_scan
from scripts.engineering.qa import report_observability_metric_inventory as inventory

# Repo-backed lane: two entrypoint tests spawn the module via subprocess with
# cwd=repo_root over the real checkout (see governance
# repo_backed_unit_test_exceptions in configs/quality/test_governance_audit.yaml).
pytestmark = pytest.mark.repo_backed


def test_direct_module_entrypoint_help_bootstraps_without_circular_import() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_observability_metric_inventory",
            "--help",
        ],
        cwd=inventory._REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "observability metric inventory" in result.stdout


def test_hidden_windows_subprocess_kwargs_hide_console() -> None:
    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=5)
    fake_subprocess = SimpleNamespace(
        CREATE_NO_WINDOW=0x08000000,
        STARTF_USESHOWWINDOW=0x00000001,
        SW_HIDE=0,
        STARTUPINFO=lambda: startupinfo,
    )

    kwargs = inventory._hidden_windows_subprocess_kwargs(
        os_name="nt",
        subprocess_module=fake_subprocess,
    )

    assert kwargs.get("creationflags") == 0x08000000
    assert kwargs.get("startupinfo") is startupinfo
    assert startupinfo.dwFlags == 0x00000001
    assert startupinfo.wShowWindow == 0


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


def test_collect_metric_inventory_normalizes_prometheus_counter_exposition_name(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_example_total"}),
    )

    runtime_dir = tmp_path / "src" / "bioetl" / "application"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "emitters.py").write_text(
        'metrics.increment_counter("bioetl_example", labels={})',
        encoding="utf-8",
    )
    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text(
        "bioetl_example_total\n",
        encoding="utf-8",
    )
    rules_dir = tmp_path / "grafana" / "prometheus-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rules.yml").write_text(
        "expr: increase(bioetl_example_total[5m])\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["emitted_metrics"] == ["bioetl_example_total"]
    assert report["live_metrics"] == ["bioetl_example_total"]
    assert report["dashboarded_without_emission"] == []
    assert report["alerted_without_emission"] == []
    assert report["runtime_without_registry"] == []


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


def test_scan_canonical_metric_mentions_prefers_bounded_git_grep(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    (tmp_path / ".git").mkdir()
    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    metric_doc = docs_dir / "metrics.md"
    metric_doc.write_text("unused", encoding="utf-8")

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"unexpected direct read: {self}")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == inventory._METRIC_MENTION_GREP_TIMEOUT_SECONDS
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "docs/03-guides/metrics.md:7:"
                "bioetl_git_grep_total bioetl_git_grep_total\n"
            ),
            stderr="",
        )

    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(Path, "read_text", fail_read_text)
        scoped_patch.setattr(inventory.subprocess, "run", fake_run)

        assert inventory._scan_canonical_metric_mentions([metric_doc], tmp_path) == {
            "bioetl_git_grep_total": ["docs/03-guides/metrics.md"]
        }


def test_scan_canonical_metric_mentions_falls_back_to_rg_before_direct_reads(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    (tmp_path / ".git").mkdir()
    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    metric_doc = docs_dir / "metrics.md"
    metric_doc.write_text("unused", encoding="utf-8")

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"unexpected direct read: {self}")

    def fake_run(
        args: list[str],
        *unused_args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == inventory._METRIC_MENTION_GREP_TIMEOUT_SECONDS
        if args[0] == "git":
            raise OSError("git unavailable")
        assert args[0] == "rg"
        assert kwargs["cwd"] == tmp_path
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="docs/03-guides/metrics.md:7:bioetl_rg_total\n",
            stderr="",
        )

    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(Path, "read_text", fail_read_text)
        scoped_patch.setattr(inventory.subprocess, "run", fake_run)

        assert inventory._scan_canonical_metric_mentions([metric_doc], tmp_path) == {
            "bioetl_rg_total": ["docs/03-guides/metrics.md"]
        }


def test_scan_canonical_metric_mentions_falls_back_to_direct_reads_in_git_checkout(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    (tmp_path / ".git").mkdir()
    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    metric_doc = docs_dir / "metrics.md"
    metric_doc.write_text("bioetl_direct_read_total\n", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("bounded scanner unavailable")

    monkeypatch.setattr(inventory.subprocess, "run", fake_run)

    assert inventory._scan_canonical_metric_mentions([metric_doc], tmp_path) == {
        "bioetl_direct_read_total": ["docs/03-guides/metrics.md"]
    }


def test_scan_canonical_metric_mentions_falls_back_to_direct_reads_after_timeouts(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    (tmp_path / ".git").mkdir()
    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    metric_doc = docs_dir / "metrics.md"
    metric_doc.write_text("bioetl_timeout_fallback_total\n", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(inventory.subprocess, "run", fake_run)

    assert inventory._scan_canonical_metric_mentions([metric_doc], tmp_path) == {
        "bioetl_timeout_fallback_total": ["docs/03-guides/metrics.md"]
    }


def test_iter_text_files_prefers_git_discovery_before_path_stat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory._TEXT_FILE_DISCOVERY_CACHE.clear()
    scan_root = inventory._REPO_ROOT / "src" / "bioetl"
    discovered = [scan_root / "example.py"]

    monkeypatch.setattr(
        inventory,
        "_iter_text_files_with_git_ls_files",
        lambda root: discovered if root == scan_root else None,
    )

    def fail_exists(self: Path) -> bool:
        raise AssertionError(f"unexpected stat-backed exists call: {self}")

    monkeypatch.setattr(Path, "exists", fail_exists)
    try:
        assert inventory._iter_text_files(scan_root) == discovered
    finally:
        inventory._TEXT_FILE_DISCOVERY_CACHE.clear()


def test_iter_text_files_with_git_ls_files_filters_text_suffixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_root = inventory._REPO_ROOT / "src" / "bioetl"

    def fake_run_text_discovery_command(
        command: list[str],
        *,
        timeout: float,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        tracked_command = [
            "git",
            "-C",
            inventory._REPO_ROOT.as_posix(),
            "ls-files",
            "--",
            "src/bioetl",
        ]
        untracked_command = [
            "git",
            "-C",
            inventory._REPO_ROOT.as_posix(),
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "src/bioetl",
        ]
        assert timeout == inventory._TEXT_DISCOVERY_TIMEOUT_SECONDS
        if command == tracked_command:
            stdout = (
                "src/bioetl/example.py\nsrc/bioetl/notes.txt\nsrc/bioetl/config.yaml\n"
            )
        elif command == untracked_command:
            stdout = "src/bioetl/untracked.py\nsrc/bioetl/scratch.txt\n"
        else:
            raise AssertionError(f"unexpected command: {command}")
        return (
            subprocess.CompletedProcess(args=command, returncode=0),
            stdout,
        )

    monkeypatch.setattr(
        inventory_scan,
        "_run_text_discovery_command",
        fake_run_text_discovery_command,
    )

    assert inventory._iter_text_files_with_git_ls_files(scan_root) == [
        inventory._REPO_ROOT / "src/bioetl/config.yaml",
        inventory._REPO_ROOT / "src/bioetl/example.py",
        inventory._REPO_ROOT / "src/bioetl/untracked.py",
    ]


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
                'metadata = {"checkpoint_saved_at_epoch_seconds": 1234}',
                'metadata.setdefault("checkpoint_saved_at_epoch_seconds", 5678)',
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


def test_collect_metric_inventory_marks_thresholded_cardinality_metrics_reviewed(
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

    config_dir = tmp_path / "configs" / "quality"
    config_dir.mkdir(parents=True)
    (config_dir / "observability_metric_inventory_allowlist.yaml").write_text(
        "\n".join(
            [
                "allowed:",
                "  runtime_cardinality_review_required:",
                "    - metric: bioetl_hotspot_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Reviewed bounded multi-emitter fanout"',
                "      review_date: '2026-09-30'",
                "      approved_max_series: 42",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["runtime_cardinality_review_candidates"] == ["bioetl_hotspot_total"]
    assert report["runtime_cardinality_reviewed"] == ["bioetl_hotspot_total"]
    assert report["runtime_cardinality_review_required"] == []
    evidence = report["runtime_cardinality_evidence"]
    assert isinstance(evidence, dict)
    assert "approved_max_series=42" in evidence["bioetl_hotspot_total"]


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


def test_collect_metric_inventory_marks_allowlisted_risky_labels_reviewed(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_reviewed_total"}),
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_reviewed_total": frozenset({"pipeline", "table"})},
    )

    config_dir = tmp_path / "configs" / "quality"
    config_dir.mkdir(parents=True)
    (config_dir / "observability_metric_inventory_allowlist.yaml").write_text(
        "\n".join(
            [
                "allowed:",
                "  declared_risky_label_review_required:",
                "    - metric: bioetl_reviewed_total",
                '      owner: "@bioetl-observability"',
                '      reason: "Reviewed bounded table label"',
                "      review_date: '2026-09-30'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["declared_risky_label_review_candidates"] == ["bioetl_reviewed_total"]
    assert report["declared_risky_label_reviewed"] == ["bioetl_reviewed_total"]
    assert report["declared_risky_label_review_required"] == []


def test_collect_metric_inventory_uses_declared_label_contracts_for_risky_labels(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_NAMES",
        frozenset({"bioetl_reviewed_total"}),
    )
    monkeypatch.setattr(
        inventory,
        "REGISTERED_PROMETHEUS_METRIC_LABELS",
        {"bioetl_reviewed_total": frozenset({"pipeline", "table"})},
    )

    config_dir = tmp_path / "configs" / "quality"
    config_dir.mkdir(parents=True)
    (config_dir / "observability_metric_declarations.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "policy_scope: observability_metric_declarations",
                "declared_label_contract_metrics:",
                "  - bioetl_reviewed_total",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["declared_risky_label_review_candidates"] == ["bioetl_reviewed_total"]
    assert report["declared_risky_label_contract_reviewed"] == ["bioetl_reviewed_total"]
    assert report["declared_risky_label_reviewed"] == ["bioetl_reviewed_total"]
    assert report["declared_risky_label_review_required"] == []


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


def test_iter_candidate_paths_with_git_grep_includes_no_color_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _iter_candidate_paths_with_git_grep passes --no-color to prevent ANSI-suffixed paths."""
    scan_root = inventory_scan._REPO_ROOT / "src" / "bioetl"
    captured_commands: list[list[str]] = []

    def fake_run_text_discovery_command(
        command: list[str],
        *,
        timeout: float,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        captured_commands.append(command)
        assert timeout == inventory_scan._TEXT_DISCOVERY_TIMEOUT_SECONDS
        return (
            subprocess.CompletedProcess(args=command, returncode=0),
            "src/bioetl/example_module.py\n",
        )

    monkeypatch.setattr(
        inventory_scan,
        "_run_text_discovery_command",
        fake_run_text_discovery_command,
    )

    paths = inventory_scan._iter_candidate_paths_with_git_grep(
        scan_root,
        markers=("increment_counter",),
        excluded_parts=(),
    )

    assert len(captured_commands) == 1
    assert "--no-color" in captured_commands[0]
    assert paths == [inventory_scan._REPO_ROOT / "src/bioetl/example_module.py"]
