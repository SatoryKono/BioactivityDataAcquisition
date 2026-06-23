"""Dedicated unit tests for ConflictResolverService."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


def _build_merge_config(
    *,
    conflict_resolution: ConflictResolution = ConflictResolution.SEED_PRIORITY,
    preserve_all_sources: bool = False,
) -> MergeConfig:
    field_priorities: dict[str, tuple[str, ...]] = {}
    if conflict_resolution is ConflictResolution.EXPLICIT_RULES:
        field_priorities = {"title": ("seed", "crossref")}
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=conflict_resolution,
        output_silver_path="silver/composite/publication",
        output_gold_path="gold/publication_enriched",
        field_priorities=field_priorities,
        preserve_all_sources=preserve_all_sources,
    )


def _build_enrichers() -> tuple[EnricherConfig, ...]:
    return (EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),)


@pytest.fixture
def logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def coalesce_policy() -> MagicMock:
    return MagicMock()


def _build_service(
    logger: MagicMock,
    coalesce_policy: MagicMock,
    *,
    conflict_resolution: ConflictResolution = ConflictResolution.SEED_PRIORITY,
    preserve_all_sources: bool = False,
) -> ConflictResolverService:
    return ConflictResolverService(
        merge_config=_build_merge_config(
            conflict_resolution=conflict_resolution,
            preserve_all_sources=preserve_all_sources,
        ),
        logger=logger,
        coalesce_policy=coalesce_policy,
    )


@pytest.mark.unit
def test_find_next_suffix_returns_next_single_letter(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)

    suffix = service.find_next_suffix("title", {"title.A"})

    assert suffix == "B"


@pytest.mark.unit
def test_find_next_suffix_rolls_to_double_letter(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)
    occupied = {f"title.{char}" for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}

    suffix = service.find_next_suffix("title", occupied)

    assert suffix == "AA"


@pytest.mark.unit
def test_find_next_suffix_raises_when_suffix_space_exhausted(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    occupied = {f"title.{char}" for char in chars}
    occupied.update({f"title.{a}{b}" for a in chars for b in chars})

    with pytest.raises(ValueError, match="Exhausted all suffixes"):
        service.find_next_suffix("title", occupied)


@pytest.mark.unit
def test_detect_and_resolve_conflicts_returns_original_when_no_conflicts(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)
    seed_df = pl.DataFrame({"seed_id": ["s1"], "seed_title": ["t1"]})
    enricher_df = pl.DataFrame({"doi": ["10.1/a"], "crossref_title": ["ct1"]})

    left, right = service.detect_and_resolve_conflicts(
        seed_df,
        enricher_df,
        join_keys={"doi"},
    )

    assert left is seed_df
    assert right is enricher_df
    logger.warning.assert_not_called()


@pytest.mark.unit
def test_detect_and_resolve_conflicts_ignores_join_keys(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)
    seed_df = pl.DataFrame({"id": ["1"], "title": ["Seed"]})
    enricher_df = pl.DataFrame({"id": ["1"], "title": ["Enricher"]})

    _left, renamed = service.detect_and_resolve_conflicts(
        seed_df,
        enricher_df,
        join_keys={"id"},
    )

    assert "id" in renamed.columns
    assert "title.A" in renamed.columns
    assert "title" not in renamed.columns


@pytest.mark.unit
def test_detect_and_resolve_conflicts_logs_rename_map(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(logger, coalesce_policy)
    seed_df = pl.DataFrame({"title": ["Seed"], "title.A": ["Seed A"]})
    enricher_df = pl.DataFrame({"title": ["Enricher"]})

    _left, renamed = service.detect_and_resolve_conflicts(
        seed_df,
        enricher_df,
        join_keys=set(),
    )

    assert "title.B" in renamed.columns
    logger.warning.assert_called_once()
    args, kwargs = logger.warning.call_args
    assert args[0] == "Column name conflicts detected after prefixing"
    assert kwargs["resolution"] == "Renaming enricher columns: {'title': 'title.B'}"
    assert kwargs["conflicts"] == ["title"]


@pytest.mark.unit
def test_resolve_conflicts_skips_when_preserve_all_sources_enabled(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        preserve_all_sources=True,
    )
    df = pl.DataFrame(
        {
            "chembl.publication.title": ["Seed"],
            "crossref.publication.title": ["Enricher"],
            "_internal": ["ignore"],
        }
    )

    result = service.resolve_conflicts(df, {}, _build_enrichers(), "chembl_publication")

    assert result is df
    logger.info.assert_called_once_with(
        "Skipping conflict resolution - preserve_all_sources=True",
        qualified_columns=2,
    )
    coalesce_policy.coalesce_prefer_seed.assert_not_called()


@pytest.mark.unit
def test_resolve_conflicts_dispatches_seed_priority(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
    )
    df = pl.DataFrame({"title": ["x"]})
    enrichers = _build_enrichers()
    expected = pl.DataFrame({"title": ["seed"]})
    coalesce_policy.coalesce_prefer_seed.return_value = expected

    result = service.resolve_conflicts(df, {}, enrichers, "chembl_publication")

    assert result is expected
    coalesce_policy.coalesce_prefer_seed.assert_called_once_with(
        df,
        enrichers,
        "chembl_publication",
    )


@pytest.mark.unit
def test_resolve_conflicts_dispatches_enricher_priority(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        conflict_resolution=ConflictResolution.ENRICHER_PRIORITY,
    )
    df = pl.DataFrame({"title": ["x"]})
    enrichers = _build_enrichers()
    expected = pl.DataFrame({"title": ["enricher"]})
    coalesce_policy.coalesce_prefer_enricher.return_value = expected

    result = service.resolve_conflicts(df, {}, enrichers, "chembl_publication")

    assert result is expected
    coalesce_policy.coalesce_prefer_enricher.assert_called_once_with(
        df,
        enrichers,
        "chembl_publication",
    )


@pytest.mark.unit
def test_resolve_conflicts_dispatches_coalesce_policy(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        conflict_resolution=ConflictResolution.COALESCE,
    )
    df = pl.DataFrame({"title": ["x"]})
    enrichers = _build_enrichers()
    expected = pl.DataFrame({"title": ["coalesced"]})
    coalesce_policy.coalesce_first_non_null.return_value = expected

    result = service.resolve_conflicts(df, {}, enrichers, "chembl_publication")

    assert result is expected
    coalesce_policy.coalesce_first_non_null.assert_called_once_with(
        df,
        enrichers,
        "chembl_publication",
    )


@pytest.mark.unit
def test_resolve_conflicts_dispatches_explicit_rules(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        conflict_resolution=ConflictResolution.EXPLICIT_RULES,
    )
    df = pl.DataFrame({"title": ["x"]})
    enrichers = _build_enrichers()
    expected = pl.DataFrame({"title": ["explicit"]})
    coalesce_policy.apply_explicit_rules.return_value = expected

    result = service.resolve_conflicts(df, {}, enrichers, "chembl_publication")

    assert result is expected
    coalesce_policy.apply_explicit_rules.assert_called_once_with(
        df,
        enrichers,
        {"title": ("seed", "crossref")},
        "chembl_publication",
    )


@pytest.mark.unit
def test_resolve_conflicts_dispatches_latest_timestamp_policy(
    logger: MagicMock, coalesce_policy: MagicMock
) -> None:
    service = _build_service(
        logger,
        coalesce_policy,
        conflict_resolution=ConflictResolution.LATEST_TIMESTAMP,
    )
    df = pl.DataFrame({"title": ["x"]})
    enrichers = _build_enrichers()
    expected = pl.DataFrame({"title": ["latest"]})
    coalesce_policy.coalesce_prefer_latest_timestamp.return_value = expected

    result = service.resolve_conflicts(df, {}, enrichers, "chembl_publication")

    assert result is expected
    coalesce_policy.coalesce_prefer_latest_timestamp.assert_called_once_with(
        df,
        enrichers,
        "chembl_publication",
    )
