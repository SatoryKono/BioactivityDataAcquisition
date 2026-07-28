"""ARCH-CR-05: control-plane manifest package lazy export contract."""

from __future__ import annotations

import importlib

import pytest


def test_manifest_package_exports_resolve_and_unknown_raises() -> None:
    mod = importlib.import_module("bioetl.application.services.control_plane.manifest")
    assert hasattr(mod, "__all__")
    for name in mod.__all__:
        value = getattr(mod, name)
        assert value is not None
    with pytest.raises(AttributeError):
        mod.DefinitelyNotAnExport
