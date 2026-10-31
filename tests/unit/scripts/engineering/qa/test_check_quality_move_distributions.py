"""Adversarial content checks use actual archives, never mocked PASS receipts."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

import pytest

from scripts.engineering.qa import check_quality_move_distributions as target
from scripts.engineering.qa.check_quality_move_distributions import main, validate

pytestmark = pytest.mark.unit


def artifacts(tmp_path: Path, fault: str = "") -> tuple[Path, Path, Path]:
    targets = [f"scripts/engineering/quality/m{i}.py" for i in range(29)]
    targets.append("scripts/engineering/quality/__init__.py")
    manifest = tmp_path / "moves.csv"
    manifest.write_text("target_path\n" + "\n".join(targets) + "\n", encoding="utf-8")
    files = dict.fromkeys(targets, b"pass\n")
    files.update(
        {
            "scripts/__init__.py": b"",
            "scripts/engineering/__init__.py": b"",
            "configs/policy.json": b"{}",
        }
    )
    if fault == "29":
        del files[targets[0]]
    if fault == "31":
        files["scripts/engineering/quality/extra.py"] = b""
    if fault == "parent":
        del files["scripts/__init__.py"]
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    modes = dict.fromkeys(files, 0o644)
    receipt = {"schema_version": 1, "files": hashes, "file_modes": modes}
    if fault == "digest":
        hashes[targets[0]] = "0" * 64
    if fault == "undeclared":
        del hashes["configs/policy.json"]
        del modes["configs/policy.json"]
    if fault == "support":
        del files["configs/policy.json"]
    if fault == "mode":
        modes[targets[0]] = 0o755
    if fault != "receipt":
        files["quality-tooling-support.json"] = json.dumps(receipt).encode()
    sdist = tmp_path / "bioetl-1.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, data in files.items():
            item = tarfile.TarInfo("bioetl-1/" + name)
            item.size = len(data)
            item.mode = 0o644
            archive.addfile(item, io.BytesIO(data))
    wheel = _wheel(tmp_path, fault)
    _damage(wheel, sdist, fault)
    return wheel, sdist, manifest


def _damage(wheel: Path, sdist: Path, fault: str) -> None:
    if fault == "corrupt":
        sdist.write_bytes(b"not a gzip archive")
    if fault == "missing":
        wheel.unlink()


def _wheel(tmp_path: Path, fault: str) -> Path:
    wheel = tmp_path / "bioetl-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("bioetl/__init__.py", "")
        if fault == "wheel-scripts":
            archive.writestr("scripts/__init__.py", "")
        if fault == "wheel-old":
            archive.writestr("bioetl/infrastructure/quality/__init__.py", "")
        if fault == "wheel-data":
            archive.writestr("bioetl-1.data/purelib/scripts/__init__.py", "")
        if fault == "unsafe":
            archive.writestr("../escape.py", "")
    return wheel


def test_valid_exact_archives_and_read_only(tmp_path):
    paths = artifacts(tmp_path)
    before = [p.read_bytes() for p in paths]
    assert validate(*paths)["quality_modules"] == 30
    assert [p.read_bytes() for p in paths] == before


@pytest.mark.parametrize(
    "fault",
    [
        "29",
        "31",
        "parent",
        "receipt",
        "digest",
        "undeclared",
        "support",
        "mode",
        "wheel-scripts",
        "wheel-old",
        "wheel-data",
        "unsafe",
        "corrupt",
        "missing",
    ],
)
def test_rejects_broken_artifacts(tmp_path, fault):
    wheel, sdist, manifest = artifacts(tmp_path, fault)
    assert (
        main(
            ["--wheel", str(wheel), "--sdist", str(sdist), "--manifest", str(manifest)]
        )
        == 1
    )


def test_ambiguous_artifact_selection_is_rejected(tmp_path):
    with pytest.raises(SystemExit) as caught:
        main(
            [
                "--wheel",
                "one.whl",
                "two.whl",
                "--sdist",
                "x.tar.gz",
                "--manifest",
                "moves.csv",
            ]
        )
    assert caught.value.code != 0


def test_validate_rejects_input_outside_owned_roots(tmp_path, monkeypatch):
    allowed_repo = tmp_path / "repo"
    allowed_temp = tmp_path / "temp"
    outside = tmp_path / "outside"
    for directory in (allowed_repo, allowed_temp, outside):
        directory.mkdir()
    wheel, sdist, manifest = artifacts(outside)
    monkeypatch.setattr(target, "ROOT", allowed_repo)
    monkeypatch.setattr(target.tempfile, "gettempdir", lambda: str(allowed_temp))

    with pytest.raises(ValueError, match="inside the repository or temporary"):
        validate(wheel, sdist, manifest)
