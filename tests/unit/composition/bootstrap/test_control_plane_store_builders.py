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
"""Tests for composition-owned control-plane file-store builders."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap import control_plane_store_builders as builders

pytestmark = pytest.mark.unit


def test_run_manifest_store_builder_uses_control_plane_root_and_metrics() -> None:
    settings = SimpleNamespace(data_dir=Path("/tmp/bioetl"))
    metrics = MagicMock()

    with (
        patch.object(
            builders,
            "control_plane_root",
            return_value=Path("/tmp/bioetl/control/run_manifest"),
        ) as root_fn,
        patch.object(builders, "FileRunManifestStore") as store_cls,
    ):
        result = builders.create_run_manifest_store(settings=settings, metrics=metrics)

    root_fn.assert_called_once_with(settings, "run_manifest")
    store_cls.assert_called_once_with(
        base_path=Path("/tmp/bioetl/control/run_manifest"),
        metrics=metrics,
    )
    assert result is store_cls.return_value


def test_run_ledger_store_builder_uses_control_plane_root_and_metrics() -> None:
    settings = SimpleNamespace(data_dir=Path("/tmp/bioetl"))
    metrics = MagicMock()

    with (
        patch.object(
            builders,
            "control_plane_root",
            return_value=Path("/tmp/bioetl/control/run_ledger"),
        ) as root_fn,
        patch.object(builders, "FileRunLedgerStore") as store_cls,
    ):
        result = builders.create_run_ledger_store(settings=settings, metrics=metrics)

    root_fn.assert_called_once_with(settings, "run_ledger")
    store_cls.assert_called_once_with(
        base_path=Path("/tmp/bioetl/control/run_ledger"),
        metrics=metrics,
    )
    assert result is store_cls.return_value


@pytest.mark.parametrize(
    ("builder_name", "store_name", "root_name"),
    [
        (
            "create_effective_config_artifact_store",
            "FileEffectiveConfigArtifactStore",
            "effective_config",
        ),
        (
            "create_historical_replay_closure_store",
            "FileHistoricalReplayClosureStore",
            "historical_replay_closure",
        ),
        (
            "create_historical_replay_universe_store",
            "FileHistoricalReplayUniverseStore",
            "historical_replay_universe",
        ),
    ],
)
def test_control_plane_store_builders_use_owner_root(
    builder_name: str,
    store_name: str,
    root_name: str,
) -> None:
    settings = SimpleNamespace(data_dir=Path("/tmp/bioetl"))
    base_path = Path("/tmp/bioetl/control") / root_name

    with (
        patch.object(builders, "control_plane_root", return_value=base_path) as root_fn,
        patch.object(builders, store_name) as store_cls,
    ):
        result = getattr(builders, builder_name)(settings=settings)

    root_fn.assert_called_once_with(settings, root_name)
    store_cls.assert_called_once_with(base_path=base_path)
    assert result is store_cls.return_value
