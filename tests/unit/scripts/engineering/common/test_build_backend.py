"""Source-only backend closure and adversarial archive boundaries."""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts.engineering.common import build_backend as backend

pytestmark = pytest.mark.unit


def test_docker_build_context_can_import_backend_without_engineering_packages(tmp_path):
    root = tmp_path / "build"
    target = root / "scripts/engineering/common/build_backend.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(Path(backend.__file__).read_bytes())
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys;sys.path.insert(0,sys.argv[1]);"
            "from scripts.engineering.common import build_backend as b;"
            "assert callable(b.build_wheel);assert callable(b.build_editable)",
            str(root),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("pkg/../escape", tarfile.REGTYPE),
        ("pkg\\escape", tarfile.REGTYPE),
        ("C:/escape", tarfile.REGTYPE),
        ("pkg/link", tarfile.SYMTYPE),
        ("pkg/link", tarfile.LNKTYPE),
        ("pkg/device", tarfile.CHRTYPE),
    ],
)
def test_rejects_unsafe_archive_entries_before_copy(name, kind):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        archive.addfile(tarfile.TarInfo("pkg"))
        member = tarfile.TarInfo(name)
        member.type = kind
        archive.addfile(member)
    stream.seek(0)
    with (
        tarfile.open(fileobj=stream) as archive,
        pytest.raises(ValueError, match="Unsafe"),
    ):
        backend._validated_members(archive)


def test_support_closure_includes_reference_search_roots_and_excludes_history():
    for name in [
        "Makefile",
        ".pre-commit-config.yaml",
        ".circleci/config.yml",
        ".zed/settings.json",
        ".codex/agents/CODEX-RUNTIME.md",
        "scripts/ops/launchers/codex/codex.bat",
        "scripts/diagrams/svg2png.mjs",
        "docs/02-architecture/diagrams/module.mmd",
    ]:
        assert backend._supported_path(name), name
    assert not backend._supported_path("docs/99-archive/old.md")
    assert not backend._supported_path(".env")
    assert not backend._supported_path("scripts/.env.secret")


def test_source_discovery_ignores_inherited_git_redirects(tmp_path, monkeypatch):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "Makefile"], check=True)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong-git-dir"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "wrong-index"))
    assert backend._support_paths(tmp_path) == ["Makefile"]


def test_sdist_repack_copies_only_validated_content_and_canonical_metadata(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "Makefile").write_text("all:\n", encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setattr(backend, "_support_paths", lambda _root: ["Makefile"])

    def upstream(directory, _config_settings):
        name = "pkg-1.tar.gz"
        with tarfile.open(Path(directory) / name, "w:gz") as archive:
            member = tarfile.TarInfo("pkg-1/PKG-INFO")
            member.size = 2
            member.mtime = 123456
            member.pax_headers = {"comment": "upstream metadata"}
            archive.addfile(member, io.BytesIO(b"OK"))
        return name

    monkeypatch.setattr(backend._backend, "build_sdist", upstream)
    out = tmp_path / "out"
    name = backend.build_sdist(str(out))
    with tarfile.open(out / name) as archive:
        member = archive.getmember("pkg-1/PKG-INFO")
        assert member.mtime == 0
        assert member.pax_headers == {}
        assert archive.extractfile(member).read() == b"OK"
        assert "pkg-1/Makefile" in archive.getnames()
        assert "pkg-1/quality-tooling-support.json" in archive.getnames()
