# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""FS-001 safety tests for BronzeWriter cleanup (#12102).

Covers: strict date validation, artifact ownership, symlink/reparse
rejection, root containment, filter validation, flat layout.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    is_owned_artifact,
    iter_safe_child_dirs,
    safe_unlink,
    validate_scope_filter,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration

ARTIFACT = "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
SIDECAR = f"{ARTIFACT}.meta.json"
JSON_COPY = ARTIFACT.removesuffix(".zst")
OLD_DATE = "2024-01-01"
CUTOFF = datetime(2024, 6, 1, tzinfo=UTC)


def _make_writer(base_path: Path, *, flat: bool = False) -> BronzeWriter:
    return BronzeWriter(
        base_path=base_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        flat_structure=flat,
    )


def _date_dir(root: Path, *parents: str, date: str = OLD_DATE) -> Path:
    date_dir = root.joinpath(*parents, date)
    date_dir.mkdir(parents=True)
    return date_dir


def _symlink_or_skip(link: Path, target: Path) -> Path:
    """Create a symlink; fall back to junction on Windows; else skip."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return link
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
        )
        if result.returncode == 0:
            return link
    pytest.skip("symlink/junction creation not permitted on this host")


async def test_cleanup_skips_noncanonical_date_dirs(tmp_path: Path) -> None:
    """Only strict YYYY-MM-DD names are cleanup candidates."""
    writer = _make_writer(tmp_path)
    entity = tmp_path / "chembl" / "activity"
    for name in ("2024-13-99", "2024-1-1", "20240101", "9999999999", "not-a-date"):
        bad = _date_dir(entity, date=name)
        (bad / ARTIFACT).write_bytes(b"x")
    good = _date_dir(entity, date=OLD_DATE)
    (good / ARTIFACT).write_bytes(b"x")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 1
    assert result["directories_removed"] == 1
    for name in ("2024-13-99", "2024-1-1", "20240101", "9999999999", "not-a-date"):
        assert (entity / name).exists()


async def test_cleanup_preserves_unknown_artifacts(tmp_path: Path) -> None:
    """Unknown files stop deletion and keep the date directory alive."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    (date_dir / ARTIFACT).write_bytes(b"x")
    (date_dir / SIDECAR).write_bytes(b"{}")
    (date_dir / "batch.jsonl.zst").write_bytes(b"legacy-name")
    (date_dir / "README.txt").write_bytes(b"keep me")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2  # payload + sidecar
    assert result["files_skipped"] == 2
    assert result["directories_removed"] == 0
    assert result["directories_skipped"] == 1
    assert (date_dir / "batch.jsonl.zst").exists()
    assert (date_dir / "README.txt").exists()
    assert not (date_dir / ARTIFACT).exists()


async def test_cleanup_removes_json_copy_artifact(tmp_path: Path) -> None:
    """Optional uncompressed copies are owned artifacts too."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    (date_dir / ARTIFACT).write_bytes(b"x")
    (date_dir / JSON_COPY).write_bytes(b"{}")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["directories_removed"] == 1
    assert not date_dir.exists()


async def test_cleanup_does_not_escape_via_symlinked_entity(tmp_path: Path) -> None:
    """A symlinked entity dir must not lead deletion outside the root."""
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside_date = _date_dir(outside, "escape")
    victim = outside_date / ARTIFACT
    victim.write_bytes(b"victim")

    writer = _make_writer(tmp_path)
    provider_dir = tmp_path / "chembl"
    provider_dir.mkdir()
    _symlink_or_skip(provider_dir / "activity", outside / "escape")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 0
    assert victim.exists()
    assert result["files_skipped"] == 0


async def test_cleanup_skips_symlinked_date_dir(tmp_path: Path) -> None:
    """A symlinked date dir is skipped even when it points inside the root."""
    writer = _make_writer(tmp_path)
    target = tmp_path / "link_target"
    target.mkdir()
    victim = target / ARTIFACT
    victim.write_bytes(b"x")
    entity_dir = tmp_path / "chembl" / "activity"
    entity_dir.mkdir(parents=True)
    _symlink_or_skip(entity_dir / OLD_DATE, target)

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 0
    assert victim.exists()


async def test_cleanup_refuses_link_inside_date_dir(tmp_path: Path) -> None:
    """A symlinked file inside a date dir is not unlinked."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    owned = date_dir / ARTIFACT
    owned.write_bytes(b"x")
    outside_file = tmp_path.parent / f"{tmp_path.name}_victim.zst"
    outside_file.write_bytes(b"victim")
    try:
        os.symlink(outside_file, date_dir / JSON_COPY)
    except (OSError, NotImplementedError):
        pytest.skip("file symlink not permitted on this host")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 1
    assert result["files_skipped"] == 1
    assert outside_file.exists()


@pytest.mark.parametrize(
    ("provider", "entity"),
    [
        ("..", None),
        ("a/b", None),
        ("a\\b", None),
        ("*", None),
        ("prov?ider", None),
        ("prov.ider", None),
        ("", None),
        ("provider", "e*"),
        ("provider", "x/y"),
    ],
)
async def test_cleanup_rejects_invalid_scope_filters(
    tmp_path: Path, provider: str | None, entity: str | None
) -> None:
    """Scope filters with traversal/glob semantics are rejected."""
    writer = _make_writer(tmp_path)
    with pytest.raises(ValueError, match=r"Invalid .* filter"):
        await writer.cleanup_old_files(CUTOFF, provider=provider, entity=entity)


async def test_cleanup_flat_layout(tmp_path: Path) -> None:
    """Flat layout cleans level-1 date dirs through the same contract."""
    writer = _make_writer(tmp_path, flat=True)
    old_dir = _date_dir(tmp_path)
    (old_dir / ARTIFACT).write_bytes(b"x")
    recent = _date_dir(tmp_path, date="2099-01-01")
    (recent / ARTIFACT).write_bytes(b"x")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 1
    assert result["directories_removed"] == 1
    assert not old_dir.exists()
    assert recent.exists()


async def test_cleanup_flat_layout_scope_filter_is_noop(tmp_path: Path) -> None:
    """Provider/entity filters on flat storage cannot scope → refuse to broaden."""
    writer = _make_writer(tmp_path, flat=True)
    old_dir = _date_dir(tmp_path)
    (old_dir / ARTIFACT).write_bytes(b"x")

    result = await writer.cleanup_old_files(CUTOFF, provider="chembl")

    assert result["files_removed"] == 0
    assert old_dir.exists()


def test_validate_scope_filter_accepts_canonical_names() -> None:
    """Canonical provider/entity names pass validation."""
    validate_scope_filter("chembl", "provider")
    validate_scope_filter("pubchem_compound2", "entity")
    validate_scope_filter(None, "provider")


def test_is_owned_artifact_contract() -> None:
    """Ownership allowlist matches only Bronze writer artifacts."""
    assert is_owned_artifact("batch_2024-01-01_x.jsonl.zst")
    assert is_owned_artifact("batch_2024-01-01_x.jsonl.zst.meta.json")
    assert is_owned_artifact("batch_2024-01-01_x.jsonl")
    assert not is_owned_artifact("batch.jsonl.zst")
    assert not is_owned_artifact("README.txt")
    assert not is_owned_artifact("batch_2024-01-01_x.parquet")


def test_iter_safe_child_dirs_skips_links(tmp_path: Path) -> None:
    """Traversal yields real dirs and refuses link entries."""
    (tmp_path / "real").mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}_outside2"
    outside.mkdir(exist_ok=True)
    skipped: list[tuple[str, str]] = []
    _symlink_or_skip(tmp_path / "linked", outside)

    result = iter_safe_child_dirs(tmp_path, on_skip=lambda p, r: skipped.append((p, r)))

    assert result == [tmp_path / "real"]
    assert skipped and skipped[0][1] == "link_or_reparse"


def test_safe_unlink_refuses_outside_root(tmp_path: Path) -> None:
    """safe_unlink never deletes paths resolved outside the trusted root."""
    outside = tmp_path.parent / f"{tmp_path.name}_victim2"
    outside.write_bytes(b"x")

    assert safe_unlink(outside, tmp_path) is False
    assert outside.exists()
