"""Stream A remaining 1–2 line INF leftovers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.infrastructure.config.dq_contract_config_loader import (
    DQContractConfigLoader,
)
from bioetl.infrastructure.config.pipeline_config_api import _load_base_config
from bioetl.infrastructure.quality.architecture_debt_reduction import _project_root
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    AuthoritativeContentHashPolicyConfig,
)

pytestmark = pytest.mark.unit


def test_project_root_resolves() -> None:
    root = _project_root()
    assert (root / "src" / "bioetl").is_dir()


def test_field_ordering_success_path() -> None:
    assert AuthoritativeContentHashPolicyConfig.validate_field_ordering(
        {"id": "asc", "name": "desc"}
    ) == {"id": "asc", "name": "desc"}


def test_dq_registry_valueerror_reraise(tmp_path: Path) -> None:
    loader = DQContractConfigLoader(tmp_path)

    def _raise(_path: Path) -> object:
        raise ValueError("unexpected registry shape")

    with (
        patch(
            "bioetl.infrastructure.config.dq_contract_config_loader.load_contract_registry_entries",
            _raise,
        ),
        pytest.raises(ValueError, match="unexpected registry shape"),
    ):
        loader._lookup_registry_entry("chembl.activity")


def test_pipeline_base_config_resolve_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("x: 1\n", encoding="utf-8")
    base = tmp_path / "base" / "pipeline.yaml"
    base.parent.mkdir(parents=True)
    base.write_text("schema_version: 1\n", encoding="utf-8")
    original = Path.resolve

    def boom(self: Path) -> Path:
        if self.name == "pipeline.yaml":
            raise OSError("cannot resolve")
        return original(self)

    monkeypatch.setattr(Path, "resolve", boom)
    loaded = _load_base_config(config_path)
    assert isinstance(loaded, dict)


def test_encoders_orjson_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib
    import sys

    import bioetl.infrastructure.serialization.encoders as encoders

    saved = sys.modules.get("orjson")
    real_import = __import__

    def blocked(name: str, *args: object, **kwargs: object) -> object:
        if name == "orjson":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked)
    sys.modules.pop("orjson", None)
    try:
        reloaded = importlib.reload(encoders)
        assert reloaded.orjson_available is False
    finally:
        monkeypatch.undo()
        if saved is not None:
            sys.modules["orjson"] = saved
        importlib.reload(encoders)
