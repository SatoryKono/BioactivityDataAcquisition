"""Immutable dependency identity and fail-closed profile dispatch controls."""

import hashlib
import json

import pytest

from scripts.ai.mcp import memory_versions as versions

pytestmark = pytest.mark.unit


@pytest.fixture
def bundle(tmp_path):
    source = tmp_path / "building"
    (source / "runtime").mkdir(parents=True)
    (source / "runtime/dependency.py").write_bytes(b"VERSION = 'qualified'\n")
    manifest = {"schema": 2, "files": {"runtime/dependency.py": versions.sha(source / "runtime/dependency.py")}}
    raw = versions.canonical(manifest)
    (source / "bundle.json").write_bytes(raw)
    target = tmp_path / hashlib.sha256(raw).hexdigest()
    source.rename(target)
    return target


def test_dependency_drift_is_rejected(bundle):
    assert versions.verify(bundle)["schema"] == 2
    (bundle / "runtime/dependency.py").write_bytes(b"VERSION = 'changed'\n")
    with pytest.raises(ValueError, match="drift"):
        versions.verify(bundle)


def test_unlisted_executable_file_is_rejected(bundle):
    (bundle / "runtime/injected.py").write_bytes(b"print('unexpected')")
    with pytest.raises(ValueError, match="file set"):
        versions.verify(bundle)


def test_manifest_change_cannot_reuse_version_name(bundle):
    manifest = json.loads((bundle / "bundle.json").read_bytes())
    manifest["schema"] = 3
    (bundle / "bundle.json").write_bytes(versions.canonical(manifest))
    with pytest.raises(ValueError, match="identity"):
        versions.verify(bundle)


def test_pending_migration_never_falls_back_to_legacy(tmp_path):
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "migration-v2.json").write_text(json.dumps({"phase": "PREPARING"}), encoding="utf-8")
    (directory / "runtime-binding.json").write_text(json.dumps({"schema": 2, "state": "legacy"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="not committed"):
        versions.select_bundle(tmp_path, "profile")


def test_disabled_incompatible_profile_is_not_legacy_fallback(tmp_path):
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "runtime-binding.json").write_text(json.dumps({"schema": 2, "state": "disabled"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="disabled"):
        versions.select_bundle(tmp_path, "profile")


def test_wrong_version_binding_is_rejected(tmp_path, bundle, monkeypatch):
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "runtime-binding.json").write_text(json.dumps({"schema": 2, "state": "active", "bundle": str(bundle), "version": "other"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="version mismatch"):
        versions.select_bundle(tmp_path, "profile")


def test_selected_profile_does_not_modify_neighbor_binding(tmp_path, bundle, monkeypatch):
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    for name, binding in [("target", {"schema": 2, "state": "active", "bundle": str(bundle), "version": bundle.name}),
                          ("neighbor", {"schema": 2, "state": "legacy"})]:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "runtime-binding.json").write_text(json.dumps(binding), encoding="utf-8")
    neighbor = tmp_path / "neighbor/runtime-binding.json"
    before = neighbor.read_bytes()
    assert versions.select_bundle(tmp_path, "target") == bundle
    assert versions.select_bundle(tmp_path, "neighbor") is None
    assert neighbor.read_bytes() == before
