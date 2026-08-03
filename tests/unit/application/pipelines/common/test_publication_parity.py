# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Golden Snapshot tests for Publication Transformers.

This module enforces 100% Data Parity for PubMed and CrossRef transformers
before, during, and after the Extraction Blocks refactoring.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")

# Directory for saving Golden Snapshots
# tests/fixtures/snapshots/publication_transformers/
SNAPSHOTS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "fixtures"
    / "snapshots"
    / "publication_transformers"
)


@pytest.fixture
def crossref_bronze_record() -> dict[str, Any]:
    """Mock CrossRef JSON Bronze record.

    This fixture provides a representative sample of CrossRef raw payload.
    """
    return {
        "DOI": "10.1038/s41586-020-2649-2",
        "title": ["AlphaFold2 predicts protein structures"],
        "author": [
            {
                "given": "John",
                "family": "Jumper",
                "affiliation": [{"name": "DeepMind"}],
            },
            {"given": "Demis", "family": "Hassabis", "affiliation": []},
        ],
        "published-online": {"date-parts": [[2020, 8, 15]]},
        "publisher": "Nature Publishing Group",
        "container-title": ["Nature"],
    }


@pytest.fixture
def pubmed_bronze_record() -> dict[str, Any]:
    """Mock PubMed Bronze record using the current `_raw_xml` contract."""
    return {
        "_raw_xml": """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>32800000</PMID>
    <Article>
      <ArticleTitle>A highly accurate protein structure prediction</ArticleTitle>
      <Journal>
        <Title>Nature</Title>
      </Journal>
      <AuthorList>
        <Author>
          <LastName>Jumper</LastName>
          <ForeName>John</ForeName>
          <AffiliationInfo>
            <Affiliation>DeepMind, London, UK</Affiliation>
          </AffiliationInfo>
        </Author>
      </AuthorList>
    </Article>
  </MedlineCitation>
</PubmedArticle>
""",
    }


def assert_snapshot_match(snapshot_name: str, actual_data: dict[str, Any]) -> None:
    """Compare actual data against a saved golden JSON snapshot.

    Set UPDATE_SNAPSHOTS=1 environment variable to regenerate snapshots.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = SNAPSHOTS_DIR / f"{snapshot_name}.json"

    # We serialize and deserialize to ensure normal JSON types (e.g. no tuples)
    actual_json = json.dumps(actual_data, indent=2, sort_keys=True)
    normalized_actual = json.loads(actual_json)

    update_snapshots = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"

    if update_snapshots or not snapshot_path.exists():
        snapshot_path.write_text(actual_json, encoding="utf-8")
        pytest.skip(
            f"Snapshot created/updated for {snapshot_name}. Re-run tests to verify."
        )

    expected_data = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert normalized_actual == expected_data, f"Data parity failed for {snapshot_name}"


@pytest.fixture
def mock_context() -> PipelineContext:
    mock_logger = MagicMock()
    return PipelineContext(
        run_id=deterministic_run_uuid_from_callsite("test_publication_parity"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_crossref_transformer_parity(
    crossref_bronze_record: dict[str, Any], mock_context: PipelineContext
) -> None:
    """Test CrossRef transformer data parity."""
    transformer = CrossRefPublicationTransformer(
        provider="crossref",
        dependencies=build_test_transformer_dependencies(),
    )

    silver_record = await transformer.transform(
        mock_context, crossref_bronze_record, index=0
    )
    assert silver_record is not None, "Transformer returned None"

    # Strip non-deterministic lineage fields
    silver_record.pop("_run_id", None)
    silver_record.pop("_ingestion_ts", None)

    assert_snapshot_match(
        "crossref_publication_silver",
        cast(dict[str, Any], dict(silver_record)),
    )


@pytest.mark.asyncio
async def test_pubmed_transformer_parity(
    pubmed_bronze_record: dict[str, Any], mock_context: PipelineContext
) -> None:
    """Test PubMed transformer data parity."""
    transformer = PubMedPublicationTransformer(
        provider="pubmed",
        dependencies=build_test_transformer_dependencies(),
    )

    silver_record = await transformer.transform(
        mock_context, pubmed_bronze_record, index=0
    )
    assert silver_record is not None, "Transformer returned None"

    # Strip non-deterministic lineage fields
    silver_record.pop("_run_id", None)
    silver_record.pop("_ingestion_ts", None)

    assert_snapshot_match(
        "pubmed_publication_silver",
        cast(dict[str, Any], dict(silver_record)),
    )
