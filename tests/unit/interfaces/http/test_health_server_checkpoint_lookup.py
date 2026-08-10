"""Pure tests for run-bounded checkpoint lookup semantics."""

from __future__ import annotations

import pytest

from bioetl.interfaces.http._health_server_checkpoint_lookup import (
    load_checkpoint_freshness_evidence,
)
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

pytestmark = pytest.mark.unit


class _CheckpointPort:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def load(self, pipeline: str) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"latest:{pipeline}")
        return ("other-run", {"manifest_id": "other-manifest"})

    async def load_for_manifest_id(
        self,
        manifest_id: str,
    ) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"manifest:{manifest_id}")
        return None

    async def load_for_run(
        self,
        pipeline: str,
        run_id: object,
    ) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"run:{pipeline}:{run_id}")
        return None


class _Host:
    def __init__(self, port: _CheckpointPort) -> None:
        self._checkpoint_port = port

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool:
        return value in {None, "$__all"}


@pytest.mark.asyncio
async def test_selected_run_not_found_never_falls_back_to_latest_checkpoint() -> None:
    port = _CheckpointPort()
    scope = _IdentityScope(
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_id="00000000-0000-0000-0000-000000008490",
        resolved_manifest=None,
        resolved_via="selected_run_id_not_found",
    )

    evidence = await load_checkpoint_freshness_evidence(
        _Host(port),  # type: ignore[arg-type]
        scope=scope,
        target_pipeline="chembl_activity",
    )

    assert evidence == (None, "selected_run_id_not_found", None, False)
    assert port.calls == []
