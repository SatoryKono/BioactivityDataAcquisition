"""Invalid saved snapshot entries cannot manufacture materialization evidence."""

import pytest

from bioetl.domain.control_plane.snapshot_materialization import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
    resolve_post_manifest_input_snapshot_materialization_mode,
)

pytestmark = pytest.mark.unit


def test_non_mapping_snapshots_are_ignored_without_overriding_valid_evidence():
    assert (
        resolve_post_manifest_input_snapshot_materialization_mode(
            [None, [], {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}]
        )
        == LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
    )
    assert resolve_post_manifest_input_snapshot_materialization_mode([None]) is None
