"""Frozen converter copying, owned staging cleanup, and exact output bounds."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ai.mcp import converter_snapshot as snapshots

pytestmark = pytest.mark.unit


@pytest.fixture
def package_site(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "package.py").write_bytes(b"VALUE = 'qualified'\n")
    distribution = SimpleNamespace(
        files=[Path("package.py")], locate_file=lambda path: site / path
    )
    monkeypatch.setattr(
        snapshots,
        "closure",
        lambda *args: ({"package": distribution}, {"package": set()}, {"package": "1"}),
    )
    return site, distribution


def test_repeated_snapshot_build_reuses_target_and_releases_its_own_staging(
    package_site, tmp_path
):
    site, _ = package_site
    destination = tmp_path / "versions"
    first = snapshots.build(destination, site)
    neighbor = destination / "neighbor"
    neighbor.mkdir()
    sentinel = neighbor / "preserved"
    sentinel.write_bytes(b"foreign cache")
    assert snapshots.build(destination, site) == first
    assert not list(destination.glob("building-*"))
    assert sentinel.read_bytes() == b"foreign cache"
    snapshots.verify(first)


def test_partial_build_failure_releases_only_its_current_staging(
    package_site, tmp_path, monkeypatch
):
    site, _ = package_site
    destination = tmp_path / "versions"
    existing = snapshots.build(destination, site)

    def partial(staging, *args):
        (staging / "partial.py").write_bytes(b"partial copy")
        raise OSError("copy interrupted")

    monkeypatch.setattr(snapshots, "_copy_distribution", partial)
    with pytest.raises(OSError, match="interrupted"):
        snapshots.build(destination, site)
    assert not list(destination.glob("building-*"))
    snapshots.verify(existing)


def test_metadata_link_is_rejected_before_resolving_its_target(
    package_site, tmp_path, monkeypatch
):
    site, distribution = package_site
    source = site / "package.py"
    original_link, original_resolve = Path.is_symlink, Path.resolve
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == source or original_link(path)
    )

    def resolve(path, *args, **kwargs):
        assert path != source, "metadata link resolved before it was rejected"
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError, match="reparse"):
        snapshots._copy_distribution(tmp_path / "staging", site, distribution)


def test_staging_cleanup_refuses_a_foreign_absolute_target(tmp_path):
    destination = tmp_path / "versions"
    destination.mkdir()
    foreign = tmp_path / "building-foreign"
    foreign.mkdir()
    sentinel = foreign / "preserved"
    sentinel.write_bytes(b"original")
    with pytest.raises(ValueError, match="escaped"):
        snapshots._discard_staging(foreign, destination)
    assert sentinel.read_bytes() == b"original"


@pytest.mark.parametrize(
    "size,expected_exit,kind",
    [
        (1024 * 1024, 0, "html"),
        (1024 * 1024 + 1, 1, "html"),
        (128, 1, "zip-as-html"),
        (128, 1, "unsupported"),
    ],
)
def test_isolated_worker_writes_exactly_the_checked_utf8_bytes(
    tmp_path, size, expected_exit, kind
):
    staging = tmp_path / "staging"
    site = staging / "site-packages"
    site.mkdir(parents=True)
    runner = Path(snapshots.__file__).with_name("converter_runner.py")
    (staging / runner.name).write_bytes(runner.read_bytes())
    package = site / "markitdown"
    package.mkdir()
    (package / "__init__.py").write_text(
        f"class Result:\n    text_content = 'x' * {size}\n"
        "class MarkItDown:\n"
        "    def __init__(self, **kwargs):\n"
        "        assert kwargs == {'enable_builtins': False, 'enable_plugins': False}\n"
        "        self.selected = []\n"
        "    def register_converter(self, value): self.selected.append(value)\n"
        "    def convert(self, path):\n"
        "        assert len(self.selected) == 1 and type(self.selected[0]).__name__ == 'HtmlConverter'\n"
        "        return Result()\n",
        encoding="utf-8",
    )
    (package / "converters.py").write_text(
        "\n".join(
            "class " + name + ": pass"
            for name in (
                "DocxConverter",
                "HtmlConverter",
                "PdfConverter",
                "PptxConverter",
                "XlsxConverter",
            )
        ),
        encoding="utf-8",
    )
    manifest = {
        "schema": 1,
        "files": {
            path.relative_to(staging).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in staging.rglob("*")
            if path.is_file()
        },
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    (staging / "converter.json").write_bytes(raw)
    converter = tmp_path / hashlib.sha256(raw).hexdigest()
    staging.rename(converter)
    home = tmp_path / "home"
    job = (
        home
        / "AppData/Local/pc-agent/mcp-shared/markdownify-bioetl-v1/profile/job-fixture"
    )
    job.mkdir(parents=True)
    source = job / ("input.zip" if kind == "unsupported" else "input.html")
    if kind == "zip-as-html":
        import zipfile

        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("nested.md", "synthetic archive content")
    else:
        source.write_bytes(b"synthetic input")
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    env.update(HOME=str(home), USERPROFILE=str(home))
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(converter / runner.name), str(source)],
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == expected_exit
    assert result.stdout == (b"x" * size if expected_exit == 0 else b"")
    if kind == "zip-as-html":
        assert b"HTML snapshot contains a ZIP archive" in result.stderr
    if kind == "unsupported":
        assert b"format is not permitted" in result.stderr


def test_parallel_publication_reuses_verified_target_and_discards_only_own_copy(
    package_site, tmp_path, monkeypatch
):
    import shutil

    site, _ = package_site
    destination = tmp_path / "versions"
    original = Path.rename

    def publish_elsewhere(path, target):
        if path.parent == destination and path.name.startswith("building-"):
            shutil.copytree(path, target)
            raise FileExistsError("another builder published this identity")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", publish_elsewhere)
    target = snapshots.build(destination, site)
    snapshots.verify(target)
    assert not list(destination.glob("building-*"))
