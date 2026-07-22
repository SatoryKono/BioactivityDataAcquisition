"""Branch coverage for writable run-manifest control-plane paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders import (
    _run_manifest_control_plane_paths as subject,
)

pytestmark = pytest.mark.unit


def test_control_plane_root_uses_explicit_data_dir(tmp_path: Path) -> None:
    settings = SimpleNamespace(data_dir=tmp_path)

    assert subject.control_plane_root(settings, "manifests") == (
        tmp_path / "output/control/manifests"
    )


def test_resolve_data_root_uses_local_data_when_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subject.os, "access", lambda _path, _mode: True)

    assert subject._resolve_data_root(SimpleNamespace(data_dir=None)) == Path("data")
    assert (tmp_path / "data").is_dir()


@pytest.mark.parametrize("failure_mode", ["mkdir", "access"])
def test_resolve_data_root_falls_back_when_local_data_is_unusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    fallback = tmp_path / "private"
    monkeypatch.setattr(subject, "_private_fallback_data_root", lambda: fallback)
    if failure_mode == "mkdir":
        (tmp_path / "data").write_text("not-a-directory", encoding="utf-8")
    else:
        monkeypatch.setattr(subject.os, "access", lambda _path, _mode: False)

    assert subject._resolve_data_root(SimpleNamespace(data_dir=None)) == fallback


def test_private_fallback_uses_uid_scoped_temp_when_home_cache_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preferred = tmp_path / "home/.cache/bioetl-data"
    fallback = tmp_path / "tmp/bioetl-data-42"
    calls: list[Path] = []

    def prepare(path: Path) -> Path:
        calls.append(path)
        if path == preferred:
            raise OSError("read-only home")
        return path

    monkeypatch.setattr(subject.Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(subject.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(subject.os, "getuid", lambda: 42, raising=False)
    monkeypatch.setattr(subject, "_prepare_private_runtime_dir", prepare)

    assert subject._private_fallback_data_root() == fallback
    assert calls == [preferred, fallback]


def test_prepare_private_runtime_dir_creates_private_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested/private"

    assert subject._prepare_private_runtime_dir(target) == target
    assert target.is_dir()
