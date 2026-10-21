"""Incomplete replay clocks and missing join keys cannot produce executable plans."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.application.composite.helpers.replay_context import freeze_merge_request
from bioetl.application.composite.join_planner_helpers import (
    build_enricher_join_metadata,
)

pytestmark = pytest.mark.unit


def test_missing_frozen_clock_cannot_create_replay_request():
    with pytest.raises(ValueError, match="timestamp_missing"):
        freeze_merge_request(SimpleNamespace(metadata_timestamp=None))


def test_empty_join_identity_cannot_resolve_an_enricher_plan():
    resolver = Mock()
    with pytest.raises(ValueError, match="join_keys must not be empty"):
        build_enricher_join_metadata(
            join_keys=(),
            primary_join_key="id",
            enricher_pipeline="provider_entity",
            seed_pipeline="seed_entity",
            merged_columns=["id"],
            resolve_join_key_names=resolver,
        )
    resolver.assert_not_called()
