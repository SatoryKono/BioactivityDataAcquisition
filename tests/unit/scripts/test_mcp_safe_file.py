"""Exercise actual Windows handle confinement and deterministic path swaps."""

import os
import subprocess

import pytest

from scripts.ai.mcp.safe_file import read_confined

pytestmark = [pytest.mark.unit, pytest.mark.skipif(os.name != "nt", reason="Windows file handles")]


@pytest.fixture
def files(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    document = root / "README.md"
    document.write_bytes(b"allowed content")
    foreign = tmp_path / "allowed-other"
    foreign.mkdir()
    secret = foreign / "README.md"
    secret.write_bytes(b"foreign sentinel")
    return root, document, secret


def test_read_and_allow_deny_allow(files):
    root, document, secret = files
    assert read_confined(root, str(document)) == b"allowed content"
    with pytest.raises(PermissionError):
        read_confined(root, str(secret))
    assert read_confined(root, str(document)) == b"allowed content"


def test_traversal_rejected_before_open(files):
    root, _, secret = files
    with pytest.raises(PermissionError):
        read_confined(root, str(root / ".." / secret.parent.name / secret.name))


def test_hardlink_rejected(files):
    root, _, secret = files
    link = root / "hardlink.md"
    os.link(secret, link)
    with pytest.raises(PermissionError, match="Hard links"):
        read_confined(root, str(link))


def test_junction_escape_rejected(files):
    root, _, secret = files
    junction = root / "junction"
    # Native PowerShell only; no cross-shell enumeration or destructive command.
    command = "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:BIOETL_TEST_JUNCTION -Target $env:BIOETL_TEST_TARGET | Out-Null"
    env = {**os.environ, "BIOETL_TEST_JUNCTION": str(junction), "BIOETL_TEST_TARGET": str(secret.parent)}
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, "Junction fixture creation failed"
    try:
        with pytest.raises(PermissionError):
            read_confined(root, str(junction / secret.name))
    finally:
        junction.rmdir()  # Remove only the fixture link, never its target.


def test_path_swap_after_open_cannot_expose_foreign_bytes(files):
    root, document, secret = files
    attempted = []
    def swap():
        with pytest.raises(PermissionError):
            document.unlink()
        with pytest.raises(PermissionError):
            os.replace(secret, document)
        attempted.append(True)
    assert read_confined(root, str(document), after_open=swap) == b"allowed content"
    assert attempted and secret.read_bytes() == b"foreign sentinel"


def test_converter_snapshot_survives_original_replacement(files, tmp_path):
    root, document, secret = files
    snapshot = tmp_path / "private-snapshot.md"
    snapshot.write_bytes(read_confined(root, str(document)))
    os.replace(secret, document)
    assert snapshot.read_bytes() == b"allowed content"
    assert document.read_bytes() == b"foreign sentinel"


def test_size_bound_and_ads_denied(files):
    root, document, _ = files
    with pytest.raises(PermissionError):
        read_confined(root, str(document), limit=2)
    with pytest.raises(PermissionError):
        read_confined(root, str(document) + ":stream")
