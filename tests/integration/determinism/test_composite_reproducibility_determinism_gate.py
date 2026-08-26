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
"""Composite rebuild/resume determinism gate for control-plane replay matrix."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.infrastructure.config._base import Settings
from tests.helpers.clock import FixedClock
from tests.integration.ci.reproducibility_contract_support import (
    build_replay_matrix_composite_config,
    load_manifest_payload,
    write_composite_snapshot_envelope,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
]


def _stable_composite_manifest_fingerprint(manifest: dict[str, object]) -> str:
    payload = {
        "execution_fingerprint": manifest.get("execution_fingerprint"),
        "provider": manifest.get("provider"),
        "entity": manifest.get("entity"),
        "replay_capability": manifest.get("replay_capability"),
        "source_refs": manifest.get("source_refs"),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def test_composite_publication_rebuild_resume_determinism_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composite rebuild/resume matrix stays stable across repeated control-plane runs."""
    data_dir = tmp_path / "runtime"
    bronze_root = tmp_path / "cached-bronze"
    write_composite_snapshot_envelope(bronze_root)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        lambda: SimpleNamespace(
            git_commit="test-clean-composite-determinism",
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock-composite-determinism",
        ),
    )
    config = build_replay_matrix_composite_config()
    runtime = CompositeRuntimeConfig(
        resume=True,
        use_cached_bronze=True,
        cached_bronze_path=str(bronze_root),
        cached_bronze_date="2026-01-01",
    )

    manifests: list[dict[str, object]] = []
    for index in range(2):
        settings = Settings(
            data_dir=data_dir,
            pipeline={
                "control_plane": {
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": True,
                    "required_persistence_profile": "degraded_observable",
                    "checkpoint_compatibility_policy": "hard_fail",
                }
            },
        )
        infra_context = CompositeInfrastructureContext(
            run_id=str(UUID(f"00000000-0000-0000-0000-00000000063{index}")),
            settings=settings,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(), clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
        )
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )
        manifests.append(load_manifest_payload(data_dir, bundle.manifest_id))

    assert manifests[0]["run_id"] != manifests[1]["run_id"]
    assert _stable_composite_manifest_fingerprint(
        manifests[0]
    ) == _stable_composite_manifest_fingerprint(manifests[1])
