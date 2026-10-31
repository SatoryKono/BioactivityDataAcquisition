"""A relocated signed installation is allowed; arbitrary PATH binaries are not."""

from types import SimpleNamespace

import pytest

from scripts.ops.observability.grafana import trusted_docker as trusted

pytestmark = pytest.mark.unit


@pytest.fixture
def installation(tmp_path, monkeypatch):
    candidate = tmp_path / "resources/bin/docker.exe"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"signature provider fixture")
    monkeypatch.setattr(trusted, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(trusted, "_windows_installation", lambda: tmp_path)
    return candidate


def test_registered_signed_relocated_install_is_used(installation, monkeypatch):
    monkeypatch.setattr(
        trusted,
        "_windows_signature",
        lambda _: {"Status": "Valid", "Subject": "CN=Docker Inc, O=Docker Inc"},
    )
    assert trusted.docker_path() == str(installation)


@pytest.mark.parametrize(
    "signature",
    [
        {"Status": "NotSigned", "Subject": None},
        {"Status": "UnknownError", "Subject": "CN=Docker Inc, O=Docker Inc"},
        {"Status": "Valid", "Subject": "CN=Other Publisher, O=Docker Inc"},
    ],
)
def test_invalid_signature_cannot_fall_back_to_path(
    installation, monkeypatch, signature
):
    monkeypatch.setattr(trusted, "_windows_signature", lambda _: signature)
    monkeypatch.setenv("PATH", str(installation.parent))
    before = installation.read_bytes()
    with pytest.raises(ValueError, match="valid Docker Inc signature"):
        trusted.docker_path()
    assert installation.read_bytes() == before


def test_missing_registered_executable_is_not_replaced_by_path(
    installation, monkeypatch
):
    installation.unlink()
    monkeypatch.setenv("PATH", str(installation.parent))
    with pytest.raises(ValueError, match="missing or redirected"):
        trusted.docker_path()
    assert not installation.exists()
