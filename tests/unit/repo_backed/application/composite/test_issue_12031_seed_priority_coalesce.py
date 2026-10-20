"""Polars acceptance for #12031 on the shipped activity, assay, and target configs.

The threshold fix already skips only singleton groups. This test loads those
three composite configs and runs the real conflict resolver on DataFrames.
It checks groups of two, three, and four compatible columns: seed priority,
null fallback, and removal of the qualified duplicates.
"""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.helpers.join_planner_identity import (
    parse_pipeline_name,
)
from bioetl.domain.composite.strategy import ConflictResolution
from bioetl.domain.ports.observability.logging import LoggerPort
from bioetl.infrastructure.config.composite_config_api import load_composite_config

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_COMPOSITES = ("activity", "assay", "target")
_GROUP_EXTRAS = {
    "pair": ("crossref",),
    "trio": ("crossref", "openalex"),
    "quad": ("crossref", "openalex", "pubmed"),
}


class _SilentLogger:
    """LoggerPort stand-in that records nothing."""

    def bind(self, **kwargs: object) -> _SilentLogger:
        del kwargs
        return self

    def info(self, _event: str, **kwargs: object) -> None:
        del kwargs

    def warning(self, _event: str, **kwargs: object) -> None:
        del kwargs

    def error(self, _event: str, **kwargs: object) -> None:
        del kwargs

    def debug(self, _event: str, **kwargs: object) -> None:
        del kwargs

    def exception(self, _event: str, **kwargs: object) -> None:
        del kwargs


def _qualified(provider: str, entity: str, field: str) -> str:
    return f"{provider}.{entity}.{field}"


def _frame(provider: str, entity: str) -> pl.DataFrame:
    """Build one frame with compatible groups of size 2, 3, and 4.

    Row 0 keeps a non-null seed. Row 1 leaves the seed null so coalescing
    must fall through to the first non-seed column in lexicographic order.
    """
    columns: dict[str, list[str | None]] = {
        _qualified(provider, entity, "singleton"): ["kept", "kept"],
    }
    for field, extras in _GROUP_EXTRAS.items():
        columns[_qualified(provider, entity, field)] = ["seed-value", None]
        for extra in extras:
            columns[_qualified(extra, entity, field)] = [
                f"{extra}-other",
                f"{extra}-fallback",
            ]
    return pl.DataFrame(columns)


@pytest.mark.parametrize("composite_name", _COMPOSITES)
def test_shipped_composite_coalesces_small_groups(composite_name: str) -> None:
    config = load_composite_config(composite_name)
    assert config.merge.conflict_resolution is ConflictResolution.SEED_PRIORITY
    assert config.merge.preserve_all_sources is False
    assert config.seed.pipeline.startswith("chembl_")

    provider, entity = parse_pipeline_name(config.seed.pipeline)
    frame = _frame(provider, entity)
    for field, extras in _GROUP_EXTRAS.items():
        group = [
            column for column in frame.columns if column.endswith(f".{entity}.{field}")
        ]
        assert len(group) == len(extras) + 1

    logger: LoggerPort = _SilentLogger()
    resolver = ConflictResolverService(
        config.merge,
        logger,
        CoalescePolicyService(logger),
    )
    result = resolver.resolve_conflicts(
        frame,
        {},
        config.enrichers,
        config.seed.pipeline,
    )

    expected_columns = [
        _qualified(provider, entity, "singleton"),
        *(_qualified(provider, entity, field) for field in _GROUP_EXTRAS),
    ]
    assert result.columns == expected_columns
    assert result[_qualified(provider, entity, "singleton")].to_list() == [
        "kept",
        "kept",
    ]
    for field in _GROUP_EXTRAS:
        assert result[_qualified(provider, entity, field)].to_list() == [
            "seed-value",
            "crossref-fallback",
        ]
        for extra in _GROUP_EXTRAS[field]:
            assert _qualified(extra, entity, field) not in result.columns
