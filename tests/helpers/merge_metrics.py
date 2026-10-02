"""Typed merge-metrics fixture shared by reproducibility contract tests."""

from unittest.mock import MagicMock

from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.domain.composite import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


class _MergeMetricsMixinHarness(MergeMetricsRecorderMixin):
    """Concrete harness exposing the merge-metrics contract methods."""


def make_merge_metrics_mixin() -> MergeMetricsRecorderMixin:
    """Build a merge-metrics host with explicit config and logger dependencies."""
    config = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/reproducibility",
        output_gold_path="gold/reproducibility",
    )
    return _MergeMetricsMixinHarness(config=config, logger=MagicMock())
