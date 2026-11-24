"""RF-003 (#13311): post-join classification ordering vs seed_priority / persist."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.helpers import (
    post_join_classification as post_join_mod,
)
from bioetl.application.composite.helpers.post_join_classification import (
    apply_post_join_target_classification,
    discard_post_join_classification,
    finalize_post_join_classification,
    publish_post_join_classification,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.contracts.gold.composite_bioassay import (
    CompositeTargetGoldSchema,
    CompositeTargetGoldSchemaV31,
)


@pytest.mark.unit
def test_enrich_gold_schema_v31_keeps_classification_fields() -> None:
    baseline = set(CompositeTargetGoldSchema.to_schema().columns)
    enrich = set(CompositeTargetGoldSchemaV31.to_schema().columns)
    assert set(TARGET_CLASSIFICATION_FIELDS).issubset(enrich)
    assert set(TARGET_CLASSIFICATION_FIELDS).isdisjoint(baseline)


@pytest.mark.unit
def test_projection_fields_match_domain_whitelist() -> None:
    assert post_join_mod._PROJECTION_FIELDS == TARGET_CLASSIFICATION_FIELDS


@pytest.mark.unit
def test_post_join_classification_noop_without_session() -> None:
    host = SimpleNamespace(_logger=MagicMock(), _target_classification_session=None)
    df = pl.DataFrame({"target_id": ["CHEMBL1"], "keywords": ["Kinase"]})
    outcome = apply_post_join_target_classification(
        host,
        merged_df=df,
        run_id="run-1",
        metadata_timestamp=datetime(2026, 11, 24, tzinfo=UTC),
    )
    assert outcome.classified_rows == 0
    assert outcome.merged_df.equals(df)


@pytest.mark.unit
def test_enrich_mode_writes_projection_after_join_features() -> None:
    session = MagicMock()
    session.mode = "enrich"
    session.enrich.side_effect = lambda context, index, business: {
        **business,
        "iuphar_class": "Enzyme",
        "iuphar_match_status": "matched",
        "effective_class": "Enzyme",
        "decision_status": "resolved",
        "target_class_profile_sha256": "a" * 64,
    }
    host = SimpleNamespace(_logger=MagicMock(), _target_classification_session=session)
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1"],
            "target_type": ["SINGLE PROTEIN"],
            "taxonomy_id": ["9606"],
            "organism": ["Homo sapiens"],
            "component_accessions": ["P12345"],
            "keywords": ["Kinase"],
            "target_protein_class_name_L1": ["Enzyme"],
            "iuphar_class": ["seed-should-lose"],
        }
    )
    outcome = apply_post_join_target_classification(
        host,
        merged_df=df,
        run_id="run-1",
        metadata_timestamp=datetime(2026, 11, 24, tzinfo=UTC),
    )
    assert outcome.classified_rows == 1
    assert outcome.merged_df["iuphar_class"].to_list() == ["Enzyme"]
    business = session.enrich.call_args.args[2]
    assert business["keywords"] == "Kinase"
    assert business["predicted_l1"] == "Enzyme"
    assert "seed-should-lose" not in str(business)


@pytest.mark.unit
def test_shadow_mode_keeps_dataframe_untouched() -> None:
    session = MagicMock()
    session.mode = "shadow"
    session.enrich.side_effect = lambda context, index, business: {
        **business,
        "iuphar_class": "Enzyme",
    }
    host = SimpleNamespace(_logger=MagicMock(), _target_classification_session=session)
    df = pl.DataFrame({"target_id": ["CHEMBL1"], "keywords": ["Kinase"]})
    outcome = apply_post_join_target_classification(
        host,
        merged_df=df,
        run_id="run-1",
        metadata_timestamp=datetime(2026, 11, 24, tzinfo=UTC),
    )
    assert outcome.merged_df.equals(df)
    assert outcome.classified_rows == 1


@pytest.mark.unit
def test_publish_finalize_and_discard_bound_to_session() -> None:
    session = MagicMock()
    host = SimpleNamespace(_logger=MagicMock(), _target_classification_session=session)
    ts = datetime(2026, 11, 24, tzinfo=UTC)
    publish_post_join_classification(
        host, run_id="run-1", metadata_timestamp=ts, indices=(0, 1)
    )
    assert session.publish.call_count == 2
    finalize_post_join_classification(host, run_id="run-1", metadata_timestamp=ts)
    session.finalize.assert_called_once()
    discard_post_join_classification(
        host, run_id="run-1", metadata_timestamp=ts, indices=(0,)
    )
    session.discard.assert_called_once()
    assert set(TARGET_CLASSIFICATION_FIELDS)
