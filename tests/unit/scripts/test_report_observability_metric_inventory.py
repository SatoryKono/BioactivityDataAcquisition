"""Unit tests for the observability metric inventory report."""

from __future__ import annotations

from pathlib import Path

from scripts.qa import report_observability_metric_inventory as inventory


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

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "bioetl_live_counter_total\nbioetl_doc_only_total\nbioetl_unknown_total\n",
        encoding="utf-8",
    )

    rules_dir = tmp_path / "grafana" / "prometheus-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rules.yml").write_text(
        "expr: increase(bioetl_live_counter_total[5m]) or increase(bioetl_rule_only_total[5m])\n",
        encoding="utf-8",
    )

    report = inventory.collect_metric_inventory(tmp_path)

    assert report["live_metrics"] == ["bioetl_live_counter_total"]
    assert report["registered_without_runtime"] == [
        "bioetl_doc_only_total",
        "bioetl_rule_only_total",
    ]
    assert report["documented_without_registry"] == ["bioetl_unknown_total"]
    assert report["documented_without_runtime"] == ["bioetl_doc_only_total"]
    assert report["ruled_without_runtime"] == ["bioetl_rule_only_total"]
    assert report["compatibility_alias_candidates"] == ["legacy_alias_total"]
    runtime_emitters = report["runtime_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert runtime_emitters["bioetl_live_counter_total"] == [
        "src/bioetl/application/emitters.py"
    ]

