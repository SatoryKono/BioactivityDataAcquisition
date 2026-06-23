from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics import (
    snapshot_support,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_ledger import (
    collect_ledger_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_refs import (
    collect_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
    merge_ledger_input_snapshots_into_summary,
)


pytestmark = pytest.mark.unit


def test_snapshot_support_facade_preserves_compatibility_exports() -> None:
    assert snapshot_support.collect_input_snapshot_refs is collect_input_snapshot_refs
    assert (
        snapshot_support.collect_ledger_input_snapshot_refs
        is collect_ledger_input_snapshot_refs
    )
    assert (
        snapshot_support.resolve_post_manifest_input_snapshot_materialization_mode
        is resolve_post_manifest_input_snapshot_materialization_mode
    )
    assert (
        snapshot_support.merge_ledger_input_snapshots_into_summary
        is merge_ledger_input_snapshots_into_summary
    )
    assert snapshot_support._collect_input_snapshot_refs is collect_input_snapshot_refs
