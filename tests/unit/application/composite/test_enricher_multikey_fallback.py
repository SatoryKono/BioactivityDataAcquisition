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
"""Multi-key enricher fallback and optional join-strategy coverage."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_execution import JoinHow, RequiredJoinKeyError
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from tests.unit.application.composite.merge_test_support import (
    build_join_planner_service,
)

_STRATEGIES = {
    "left": MergeStrategy.LEFT_OUTER,
    "inner": MergeStrategy.INNER,
    "full": MergeStrategy.UNION,
}


def _planner(join_how: JoinHow):
    logger = MagicMock()
    merge_config = MergeConfig(
        strategy=_STRATEGIES[join_how],
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/test",
        output_gold_path="gold/test_merged",
    )
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    order_service = ColumnOrderService(logger)
    return build_join_planner_service(
        merge_config=merge_config,
        logger=logger,
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        conflict_resolver=ConflictResolverService(
            merge_config=merge_config,
            logger=logger,
            coalesce_policy=CoalescePolicyService(logger, order_service=order_service),
        ),
        join_type_resolver=lambda: join_how,
    )


async def _apply(
    join_how: JoinHow,
    *,
    seed_df: pl.DataFrame,
    enricher_df: pl.DataFrame,
    join_keys: tuple[str, ...],
    required: bool = False,
) -> pl.DataFrame:
    planner = _planner(join_how)
    enricher = EnricherConfig(
        pipeline="crossref_publication",
        join_keys=join_keys,
        required=required,
    )
    return await planner.apply_joins(
        seed_df=seed_df,
        enricher_dfs={"crossref_publication": enricher_df},
        enrichers=[enricher],
        seed_pipeline="chembl_publication",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deduplicate_enricher_pure_duplicates() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed Title"]}),
        enricher_df=pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/a"],
                "title": ["CrossRef Title", "CrossRef Title"],
                "citation_count": [42, 42],
            }
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 1
    assert result["crossref.publication.citation_count"][0] == 42
    assert "__bioetl_seed_row_id" not in result.columns
    assert "__bioetl_join_matched" not in result.columns


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multikey_primary_collision_does_not_fan_out() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame(
            {"doi": ["10.1/a", "10.1/b"], "title": ["Seed A", "Seed B"]}
        ),
        enricher_df=pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/a"],
                "title": ["Title A", "Title B"],
                "citation_count": [1, 2],
            }
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 2
    matched = result.filter(pl.col("doi") == "10.1/a")
    assert matched.height == 1
    assert matched["crossref.publication.citation_count"][0] == "1|2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_title_matches_when_doi_misses() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame({"doi": ["10.1/missing"], "title": ["Shared Title"]}),
        enricher_df=pl.DataFrame(
            {"doi": ["10.9/other"], "title": ["Shared Title"], "citation_count": [7]}
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 1
    assert result["crossref.publication.citation_count"][0] == 7


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_preserves_seed_order_across_keys() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame(
            {"doi": ["10.1/a", "10.1/missing"], "title": ["Seed A", "Shared Title"]}
        ),
        enricher_df=pl.DataFrame(
            {
                "doi": ["10.1/a", "10.9/other"],
                "title": ["Other Title", "Shared Title"],
                "citation_count": [3, 9],
            }
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 2
    assert result["doi"].to_list() == ["10.1/a", "10.1/missing"]
    assert result["crossref.publication.citation_count"].to_list() == [3, 9]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_required_enricher_missing_key_fails_closed() -> None:
    with pytest.raises(RequiredJoinKeyError, match="doi"):
        await _apply(
            "left",
            seed_df=pl.DataFrame({"title": ["Seed Title"]}),
            enricher_df=pl.DataFrame({"doi": ["10.1/a"], "citation_count": [1]}),
            join_keys=("doi",),
            required=True,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optional_inner_unmatched_seed_is_dropped() -> None:
    result = await _apply(
        "inner",
        seed_df=pl.DataFrame({"doi": ["10.1/a", "10.1/missing"]}),
        enricher_df=pl.DataFrame({"doi": ["10.1/a"], "citation_count": [5]}),
        join_keys=("doi",),
    )

    assert result.height == 1
    assert result["doi"].to_list() == ["10.1/a"]
    assert result["crossref.publication.citation_count"][0] == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optional_full_keeps_unmatched_enricher_rows() -> None:
    result = await _apply(
        "full",
        seed_df=pl.DataFrame({"doi": ["10.1/a"]}),
        enricher_df=pl.DataFrame(
            {"doi": ["10.1/a", "10.9/extra"], "citation_count": [1, 8]}
        ),
        join_keys=("doi",),
    )

    assert result.height == 2
    assert 8 in result["crossref.publication.citation_count"].to_list()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_concat_accepts_dedup_dtype_change() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/missing"],
                "title": ["Seed A", "Editorial"],
            }
        ),
        enricher_df=pl.DataFrame(
            {
                "doi": ["10.1/a", "10.9/x", "10.9/y"],
                "title": ["Other Title", "Editorial", "Editorial"],
                "citation_count": [3, 1, 2],
            }
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 2
    assert result["doi"].to_list() == ["10.1/a", "10.1/missing"]
    citations = result["crossref.publication.citation_count"].to_list()
    assert str(citations[0]) == "3"
    assert citations[1] == "1|2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_zero_match_fallback_keeps_enricher_schema() -> None:
    result = await _apply(
        "left",
        seed_df=pl.DataFrame({"doi": ["10.1/missing"], "title": ["Other"]}),
        enricher_df=pl.DataFrame(
            {"doi": ["10.9/x"], "title": ["Editorial"], "citation_count": [4]}
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 1
    assert result["crossref.publication.citation_count"][0] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optional_inner_multikey_drops_unmatched_seed() -> None:
    result = await _apply(
        "inner",
        seed_df=pl.DataFrame(
            {"doi": ["10.1/a", "10.1/missing"], "title": ["Seed A", "Nowhere"]}
        ),
        enricher_df=pl.DataFrame(
            {"doi": ["10.1/a"], "title": ["Other"], "citation_count": [6]}
        ),
        join_keys=("doi", "title"),
    )

    assert result.height == 1
    assert result["doi"].to_list() == ["10.1/a"]
    assert result["crossref.publication.citation_count"][0] == 6
