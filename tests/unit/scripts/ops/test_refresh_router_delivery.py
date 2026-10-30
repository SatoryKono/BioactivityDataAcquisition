"""Real release admission must reject incomplete or changed image filesystems."""

from copy import deepcopy
import io
import os
from pathlib import Path
import tarfile

import pytest

from scripts.ops.observability.grafana import refresh_router_delivery as release
from scripts.ops.__main__ import main as ops_main

pytestmark = pytest.mark.unit
REFERENCE = "satorykono/bioetl-grafana-router7-canvas@sha256:" + "d" * 64
CONFIG = "sha256:" + "c" * 64


def row(content=None, mode=0o644, uid=0):
    return [
        "5" if content is None else "0",
        mode,
        uid,
        0,
        "",
        0,
        0,
        None if content is None else release.sha(content),
        {},
    ]


def context(tmp_path: Path, *, omit=None, extra=None):
    path = tmp_path / "context.tar"
    entries = {
        "Dockerfile.host": b"audited recipe",
        "host-build/app.js": b"frontend",
        "bioetl-scenes-app/module.js": b"scenes",
        "bioetl-scenes-app/module.js.map": b"map",
        "bioetl-selectorshell-panel/module.js": b"selectors",
    }
    if omit:
        entries.pop(omit)
    if extra:
        entries[extra] = b"unexpected"
    with tarfile.open(path, "w") as archive:
        for name, content in entries.items():
            entry = tarfile.TarInfo(name)
            entry.mode, entry.size = 0o644, len(content)
            archive.addfile(entry, io.BytesIO(content))
    return path


@pytest.fixture
def physical():
    base_files = {
        "etc/retained": row(b"base"),
        "usr/share/grafana/public": row(mode=0o755, uid=472),
        "usr/share/grafana/data": row(mode=0o775, uid=472),
        release.FRONTEND + "/old.js": row(b"old"),
    }
    artifacts = {release.FRONTEND + "/app.js": row(b"frontend", mode=0o444)}
    for plugin in release.PLUGINS:
        artifacts[f"{release.PLUGIN_ROOT}/{plugin}/module.js"] = row(
            plugin.encode(), mode=0o444
        )
    # Explicit expected image data, independent of the recipe transformation helper.
    actual = {
        "etc/retained": row(b"base"),
        "usr/share/grafana/public": row(mode=0o755),
        "usr/share/grafana/data": row(mode=0o755),
        release.PLUGIN_ROOT: row(mode=0o755),
        **deepcopy(artifacts),
    }
    base = {
        "Config": {"User": "472", "Env": ["GF_VERSION=13.2.3"]},
        "Os": "linux",
        "Architecture": "amd64",
        "RootFS": {"Type": "layers", "Layers": ["sha256:" + "a" * 64]},
    }
    built = {
        **deepcopy(base),
        "Id": CONFIG,
        "Config": {**base["Config"], "User": "grafana"},
        "RootFS": {
            "Type": "layers",
            "Layers": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
        },
    }
    delivered = {**deepcopy(built), "RepoDigests": [REFERENCE]}
    return base, built, delivered, base_files, actual, artifacts


def test_context_hashes_complete_outputs_and_applies_readonly_copy_metadata(tmp_path):
    result = release.context_records(
        context(tmp_path), b"audited recipe", within=tmp_path
    )
    scene = result[f"{release.PLUGIN_ROOT}/bioetl-scenes-app/module.js"]
    assert scene[1:4] == [0o444, 0, 0]
    assert scene[7] == release.sha(b"scenes")
    assert result[f"{release.PLUGIN_ROOT}/bioetl-scenes-app/module.js.map"][
        7
    ] == release.sha(b"map")
    assert result[release.FRONTEND + "/app.js"][7] == release.sha(b"frontend")


def test_input_reads_are_bounded_regular_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "input"
    source.write_bytes(b"verified input")
    assert release.file_sha(source, within=workspace) == release.sha(b"verified input")
    (workspace / "nested").mkdir()
    assert release.file_sha(
        workspace / "nested" / ".." / "input", within=workspace
    ) == release.sha(b"verified input")
    outside = tmp_path / "outside"
    outside.write_bytes(b"private")
    with pytest.raises(ValueError):
        release.file_sha(outside, within=workspace)
    with pytest.raises(ValueError):
        release.context_records(outside, b"recipe", within=workspace)
    with pytest.raises(ValueError):
        release.file_sha(workspace, within=workspace)
    assert source.read_bytes() == b"verified input"
    assert outside.read_bytes() == b"private"


def test_linked_build_inputs_are_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"original")
    alias = tmp_path / "alias"
    os.link(source, alias)
    with pytest.raises(ValueError):
        release.file_sha(alias, within=tmp_path)
    with pytest.raises(ValueError):
        release.context_records(alias, b"recipe", within=tmp_path)
    assert source.read_bytes() == alias.read_bytes() == b"original"


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink regression runs in Linux CI")
@pytest.mark.parametrize("outside", [False, True])
def test_symlinked_build_input_is_never_followed(tmp_path, outside):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = (tmp_path if outside else workspace) / "source"
    target.write_bytes(b"original")
    link = workspace / "redirect"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        release.file_sha(link, within=workspace)
    with pytest.raises(ValueError):
        release.context_records(link, b"recipe", within=workspace)
    assert target.read_bytes() == b"original"


@pytest.mark.parametrize(
    "args",
    [
        ("--exec-path=/untrusted",),
        ("show", "--help"),
        ("show", "a" * 40 + ":../outside"),
        ("show", "a" * 40 + ":/absolute"),
        ("merge-base", "--is-ancestor", "--help", "HEAD"),
        ("ls-tree", "-rz", "--name-only", "a" * 40, "--", "--output=outside"),
    ],
)
def test_git_argument_injection_never_executes(tmp_path, monkeypatch, args):
    calls = []
    monkeypatch.setattr(
        release.subprocess, "check_output", lambda *a, **k: calls.append(a)
    )
    with pytest.raises(ValueError):
        release.git(tmp_path, *args)
    assert calls == []


def test_git_blob_read_uses_a_pinned_commit_and_option_terminator(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Fixture"], check=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "fixture@example.invalid"],
        check=True,
    )
    source = tmp_path / "source"
    source.write_bytes(b"pinned")
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", "source"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    ref = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    assert release.git(tmp_path, "show", ref + ":source") == b"pinned"


@pytest.mark.parametrize(
    "fault", ["missing-plugin", "foreign-path", "traversal", "wrong-recipe"]
)
def test_incomplete_or_foreign_context_is_rejected(tmp_path, fault):
    path = context(
        tmp_path,
        omit="bioetl-selectorshell-panel/module.js"
        if fault == "missing-plugin"
        else None,
        extra={"foreign-path": "other/secret", "traversal": "host-build/../escape"}.get(
            fault
        ),
    )
    with pytest.raises(ValueError):
        release.context_records(
            path,
            b"other recipe" if fault == "wrong-recipe" else b"audited recipe",
            within=tmp_path,
        )
    assert set(tmp_path.iterdir()) == {path}
    assert not (tmp_path / "escape").exists()


def test_complete_physical_match_is_accepted_without_changing_input_records(physical):
    base, built, delivered, files, actual, artifacts = physical
    original = deepcopy(files)
    result = release.verify_host(
        base, built, delivered, files, actual, deepcopy(actual), artifacts, REFERENCE
    )
    assert result["built_config_digest"] == CONFIG
    assert result["image"] == REFERENCE
    assert files == original
    assert release.FRONTEND + "/old.js" not in release.expected_host(files, artifacts)


@pytest.mark.parametrize(
    "fault",
    [
        "bytes",
        "mode",
        "owner",
        "missing",
        "foreign",
        "config",
        "layers",
        "unpublished",
        "pax-path",
        "security-xattr",
    ],
)
def test_any_physical_or_identity_mismatch_stops_admission(physical, fault):
    base, built, delivered, files, actual, artifacts = physical
    path = release.FRONTEND + "/app.js"
    if fault == "bytes":
        actual[path][7] = release.sha(b"different")
    elif fault == "mode":
        actual[path][1] = 0o666
    elif fault == "owner":
        actual[path][2] = 472
    elif fault == "missing":
        actual.pop(path)
    elif fault == "foreign":
        actual["etc/unreviewed"] = row(b"extra")
    elif fault == "config":
        built["Config"]["User"] = "root"
    elif fault == "layers":
        built["RootFS"]["Layers"][0] = "sha256:" + "e" * 64
    elif fault == "unpublished":
        delivered["RepoDigests"] = []
    elif fault == "pax-path":
        actual[path][8]["path"] = "etc/other"
    else:
        actual[path][8]["SCHILY.xattr.security.capability"] = "unreviewed"
    before = deepcopy(actual)
    with pytest.raises(ValueError):
        release.verify_host(
            base,
            built,
            delivered,
            files,
            actual,
            deepcopy(actual),
            artifacts,
            REFERENCE,
        )
    assert actual == before


def arguments():
    return [
        "--host-image",
        REFERENCE,
        "--managed-image",
        REFERENCE,
        "--built-host",
        CONFIG,
        "--built-managed",
        CONFIG,
        "--source-ref",
        "a" * 40,
        "--source-root",
        ".",
        "--context",
        "context.tar",
    ]


def test_check_never_writes_and_update_rejects_concurrent_edits(tmp_path, monkeypatch):
    path = tmp_path / "tracked"
    path.write_bytes(b"original")
    monkeypatch.setattr(release.native, "ROOT", tmp_path)
    monkeypatch.setattr(release, "materialize", lambda *_: {path: b"generated"})
    monkeypatch.setattr(release, "git", lambda *_: b"original")
    assert ops_main(["refresh-router-delivery", *arguments(), "--check"]) == 1
    assert path.read_bytes() == b"original"
    assert ops_main(["refresh-router-delivery", *arguments(), "--update"]) == 0
    assert path.read_bytes() == b"generated"
    assert ops_main(["refresh-router-delivery", *arguments(), "--check"]) == 0
    path.write_bytes(b"concurrent owner change")
    assert ops_main(["refresh-router-delivery", *arguments(), "--update"]) == 1
    assert path.read_bytes() == b"concurrent owner change"
