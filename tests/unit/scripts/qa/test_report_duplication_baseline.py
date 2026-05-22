from __future__ import annotations

import re

from scripts.engineering.qa.report_duplication_baseline import _build_payload
from scripts.engineering.qa.report_duplication_baseline import _build_trend_summary
from scripts.engineering.qa.report_duplication_baseline import (
    _filter_clusters_by_module_patterns,
)
from scripts.engineering.qa.report_duplication_baseline import (
    _parse_pylint_duplicate_output,
)
from scripts.engineering.qa.report_duplication_baseline import _render_markdown
from scripts.engineering.qa.report_duplication_baseline import _top_duplicate_pairs
from scripts.engineering.qa.report_duplication_baseline import DuplicateCluster
from scripts.engineering.qa.report_duplication_baseline import DuplicateModuleRef
from scripts.engineering.qa.report_duplication_baseline import TargetDuplicationReport


def test_parse_pylint_duplicate_output_extracts_clusters() -> None:
    stdout = """
************* Module bioetl.application.foo
src\\bioetl\\application\\foo.py:10:0: R0801: Similar lines in 2 files
==bioetl.application.foo:[10:20]
==bioetl.application.bar:[30:40]
some duplicate text
src\\bioetl\\application\\baz.py:21:0: R0801: Similar lines in 2 files
==bioetl.application.baz:[21:28]
==bioetl.application.qux:[50:57]
""".strip()

    clusters = _parse_pylint_duplicate_output(stdout)

    assert len(clusters) == 2
    assert clusters[0].path == r"src\bioetl\application\foo.py"
    assert clusters[0].line == 10
    assert [m.module for m in clusters[0].modules] == [
        "bioetl.application.foo",
        "bioetl.application.bar",
    ]
    assert clusters[1].path == r"src\bioetl\application\baz.py"
    assert clusters[1].line == 21


def test_render_markdown_includes_targets_and_interpretation_note() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/application",
        returncode=8,
        duplicate_count=1,
        clusters=(
            DuplicateCluster(
                path="src/bioetl/application/foo.py",
                line=10,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.application.foo",
                        start_line=10,
                        end_line=20,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.application.bar",
                        start_line=30,
                        end_line=40,
                    ),
                ),
            ),
        ),
    )

    markdown = _render_markdown([report])

    assert "# Duplication Baseline Report" in markdown
    assert "mode: report-only" in markdown
    assert "facades, export barrels, and compatibility shims" in markdown
    assert "`src/bioetl/application`" in markdown
    assert "`src/bioetl/application/foo.py:10`" in markdown


def test_filter_clusters_by_module_patterns_excludes_normalized_modules() -> None:
    clusters = [
        DuplicateCluster(
            path="src/bioetl/application/core/transformer_runtime/__init__.py",
            line=1,
            modules=(
                DuplicateModuleRef(
                    module="bioetl.application.core.transformer_runtime.__init__",
                    start_line=1,
                    end_line=10,
                ),
                DuplicateModuleRef(
                    module="bioetl.application.core.transformer_runtime.state",
                    start_line=10,
                    end_line=20,
                ),
            ),
        ),
        DuplicateCluster(
            path="src/bioetl/application/core/base_transformer.py",
            line=20,
            modules=(
                DuplicateModuleRef(
                    module="bioetl.application.core.base_transformer",
                    start_line=20,
                    end_line=30,
                ),
                DuplicateModuleRef(
                    module="bioetl.application.core.batch_transformer_state",
                    start_line=40,
                    end_line=50,
                ),
            ),
        ),
    ]

    filtered = _filter_clusters_by_module_patterns(
        clusters,
        exclude_module_patterns=(re.compile(r"\.__init__$"),),
    )

    assert len(filtered) == 1
    assert filtered[0].path == "src/bioetl/application/core/base_transformer.py"


def test_render_markdown_surfaces_raw_counts_when_normalized() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/application/core",
        returncode=8,
        duplicate_count=1,
        clusters=(
            DuplicateCluster(
                path="src/bioetl/application/core/foo.py",
                line=10,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.application.core.foo",
                        start_line=10,
                        end_line=20,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.application.core.bar",
                        start_line=30,
                        end_line=40,
                    ),
                ),
            ),
        ),
        raw_duplicate_count=2,
    )

    markdown = _render_markdown(
        [report],
        exclude_module_patterns=(r"\.__init__$",),
    )

    assert "normalized_view: enabled" in markdown
    assert "total_raw_duplicate_clusters: 2" in markdown
    assert "excluded duplicate clusters: 1" in markdown


def test_build_trend_summary_compares_against_previous_snapshot() -> None:
    history_records = [
        {
            "snapshot_date": "2026-03-23",
            "summary": {"total_duplicate_clusters": 5},
            "targets": [
                {"target": "src/bioetl/application/core", "duplicate_count": 3},
                {
                    "target": "src/bioetl/composition/factories/pipeline",
                    "duplicate_count": 2,
                },
            ],
        }
    ]

    trend = _build_trend_summary(
        history_records=history_records,
        current_targets=[
            {"target": "src/bioetl/application/core", "duplicate_count": 4},
            {
                "target": "src/bioetl/composition/factories/pipeline",
                "duplicate_count": 1,
            },
        ],
        snapshot_date="2026-03-24",
        total_duplicate_clusters=5,
    )

    assert trend["status"] == "compared_to_previous"
    assert trend["previous_snapshot_date"] == "2026-03-23"
    assert trend["total_duplicate_cluster_delta"] == 0
    rows = trend["targets"]
    assert rows[0]["delta_duplicate_count"] == 1
    assert rows[1]["delta_duplicate_count"] == -1


def test_build_trend_summary_ignores_same_day_rerun_entries() -> None:
    history_records = [
        {
            "snapshot_date": "2026-03-23",
            "summary": {"total_duplicate_clusters": 5},
            "targets": [
                {"target": "src/bioetl/application/core", "duplicate_count": 3},
            ],
        },
        {
            "snapshot_date": "2026-03-24",
            "summary": {"total_duplicate_clusters": 4},
            "targets": [
                {"target": "src/bioetl/application/core", "duplicate_count": 4},
            ],
        },
    ]

    trend = _build_trend_summary(
        history_records=history_records,
        current_targets=[
            {"target": "src/bioetl/application/core", "duplicate_count": 4},
        ],
        snapshot_date="2026-03-24",
        total_duplicate_clusters=4,
    )

    assert trend["status"] == "compared_to_previous"
    assert trend["previous_snapshot_date"] == "2026-03-23"
    assert trend["total_duplicate_cluster_delta"] == -1


def test_render_markdown_includes_trend_section_when_available() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/application/core",
        returncode=8,
        duplicate_count=1,
        clusters=(),
        raw_duplicate_count=1,
    )

    markdown = _render_markdown(
        [report],
        trend_summary={
            "status": "compared_to_previous",
            "previous_snapshot_date": "2026-03-23",
            "total_duplicate_cluster_delta": 0,
            "targets": [
                {
                    "target": "src/bioetl/application/core",
                    "current_duplicate_count": 1,
                    "previous_duplicate_count": 1,
                    "delta_duplicate_count": 0,
                }
            ],
        },
    )

    assert "## Trend vs Previous Snapshot" in markdown
    assert "previous snapshot: `2026-03-23`" in markdown
    assert "| `src/bioetl/application/core` | 1 | 1 | +0 |" in markdown


def test_render_markdown_handles_missing_total_delta_in_trend_summary() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/application/services/control_plane",
        returncode=8,
        duplicate_count=12,
        clusters=(),
        raw_duplicate_count=12,
    )

    markdown = _render_markdown(
        [report],
        trend_summary={
            "status": "compared_to_previous",
            "previous_snapshot_date": "2026-03-24",
            "total_duplicate_cluster_delta": None,
            "targets": [
                {
                    "target": "src/bioetl/application/services/control_plane",
                    "current_duplicate_count": 12,
                    "previous_duplicate_count": None,
                    "delta_duplicate_count": None,
                }
            ],
        },
    )

    assert "total_duplicate_cluster_delta_vs_previous: n/a" in markdown
    assert (
        "| `src/bioetl/application/services/control_plane` | 12 | n/a | n/a |"
        in markdown
    )


def test_top_duplicate_pairs_ranks_repeated_pairs() -> None:
    clusters = (
        DuplicateCluster(
            path="a.py",
            line=1,
            modules=(
                DuplicateModuleRef(module="pkg.alpha", start_line=1, end_line=5),
                DuplicateModuleRef(module="pkg.beta", start_line=1, end_line=5),
            ),
        ),
        DuplicateCluster(
            path="b.py",
            line=2,
            modules=(
                DuplicateModuleRef(module="pkg.beta", start_line=10, end_line=15),
                DuplicateModuleRef(module="pkg.alpha", start_line=20, end_line=25),
            ),
        ),
        DuplicateCluster(
            path="c.py",
            line=3,
            modules=(
                DuplicateModuleRef(module="pkg.gamma", start_line=1, end_line=5),
                DuplicateModuleRef(module="pkg.delta", start_line=1, end_line=5),
            ),
        ),
    )

    ranked = _top_duplicate_pairs(clusters)

    assert ranked[0]["modules"] == ["pkg.alpha", "pkg.beta"]
    assert ranked[0]["duplicate_clusters"] == 2
    assert ranked[1]["modules"] == ["pkg.delta", "pkg.gamma"]
    assert ranked[1]["duplicate_clusters"] == 1


def test_build_payload_includes_top_pairs() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/composition/factories/pipeline",
        returncode=8,
        duplicate_count=2,
        raw_duplicate_count=2,
        clusters=(
            DuplicateCluster(
                path="x.py",
                line=1,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.assembler",
                        start_line=1,
                        end_line=5,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.factory_method_helpers",
                        start_line=10,
                        end_line=15,
                    ),
                ),
            ),
            DuplicateCluster(
                path="y.py",
                line=2,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.factory_method_helpers",
                        start_line=20,
                        end_line=25,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.assembler",
                        start_line=30,
                        end_line=35,
                    ),
                ),
            ),
        ),
    )

    payload = _build_payload(
        [report],
        snapshot_date="2026-03-24",
        exclude_module_patterns=[],
        trend_summary={"status": "no_prior_snapshot"},
    )

    top_pairs = payload["targets"][0]["top_pairs"]
    assert top_pairs[0]["modules"] == [
        "bioetl.composition.factories.pipeline.assembler",
        "bioetl.composition.factories.pipeline.factory_method_helpers",
    ]
    assert top_pairs[0]["duplicate_clusters"] == 2


def test_render_markdown_includes_top_recurring_pairs_table() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/composition/factories/pipeline",
        returncode=8,
        duplicate_count=1,
        raw_duplicate_count=1,
        clusters=(
            DuplicateCluster(
                path="x.py",
                line=1,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.assembler",
                        start_line=1,
                        end_line=5,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.composition.factories.pipeline.factory_method_helpers",
                        start_line=10,
                        end_line=15,
                    ),
                ),
            ),
        ),
    )

    markdown = _render_markdown([report])

    assert "| Top recurring module pairs | Duplicate clusters |" in markdown
    assert (
        "`bioetl.composition.factories.pipeline.assembler` <-> "
        "`bioetl.composition.factories.pipeline.factory_method_helpers`"
    ) in markdown
