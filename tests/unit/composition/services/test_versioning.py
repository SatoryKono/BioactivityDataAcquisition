"""Unit tests for composition.services.versioning."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.services import versioning


@pytest.fixture(autouse=True)
def _clear_git_commit_cache() -> None:
    versioning.get_git_commit.cache_clear()
    versioning.get_dependency_lock_hash.cache_clear()
    versioning.get_code_revision_provenance.cache_clear()


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_git_commit_returns_full_hash_on_success(mock_run: MagicMock) -> None:
    full_hash = "a" * 40
    mock_run.return_value = SimpleNamespace(returncode=0, stdout=f"{full_hash}\n")

    assert versioning.get_git_commit() == full_hash
    mock_run.assert_called_once_with(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_git_commit_returns_none_on_nonzero_exit(mock_run: MagicMock) -> None:
    mock_run.return_value = SimpleNamespace(returncode=1, stdout="")

    assert versioning.get_git_commit() is None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_git_commit_returns_none_on_exception(mock_run: MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError("git missing")

    assert versioning.get_git_commit() is None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_reports_clean_state(
    mock_run: MagicMock,
) -> None:
    mock_run.side_effect = [
        SimpleNamespace(returncode=0, stdout="abc1234\n"),
        SimpleNamespace(returncode=0, stdout=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == "abc1234"
    assert provenance.source_revision_state == "clean"
    assert provenance.dependency_lock_hash is not None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_reports_dirty_state(
    mock_run: MagicMock,
) -> None:
    mock_run.side_effect = [
        SimpleNamespace(returncode=0, stdout="abc1234\n"),
        SimpleNamespace(returncode=1, stdout=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == "abc1234"
    assert provenance.source_revision_state == "dirty"
    assert provenance.dependency_lock_hash is not None


@pytest.mark.unit
def test_get_dependency_lock_hash_reads_uv_lock_from_current_tree(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    versioning.get_dependency_lock_hash.cache_clear()

    digest = versioning.get_dependency_lock_hash()

    assert isinstance(digest, str)
    assert digest.startswith("sha256:")
    assert len(digest) == 71


@pytest.mark.unit
def test_normalize_for_hash_handles_none_and_tuple() -> None:
    assert versioning._normalize_for_hash(None) is None
    assert versioning._normalize_for_hash(("a", {"b": 1})) == ["a", {"b": 1}]


@pytest.mark.unit
def test_compute_config_hash_supports_legacy_dict_method() -> None:
    class LegacyConfig:
        def dict(self, *, exclude_none: bool) -> dict[str, object]:
            assert exclude_none is True
            return {"version": "1.0.0", "nested": {"x": 1}}

    digest = versioning.compute_config_hash(LegacyConfig())

    assert len(digest) == 64


@pytest.mark.unit
def test_compute_config_hash_supports_mapping_cast_path() -> None:
    class MappingConfig:
        def __iter__(self):
            return iter([("provider", "chembl"), ("entity", "publication")])

    digest = versioning.compute_config_hash(MappingConfig())

    assert len(digest) == 64


@pytest.mark.unit
def test_compute_config_hash_is_stable_for_equivalent_mappings() -> None:
    config_a = {
        "provider": "chembl",
        "entity": "publication",
        "runtime": {"limit": 100, "resume": False},
    }
    config_b = {
        "runtime": {"resume": False, "limit": 100},
        "entity": "publication",
        "provider": "chembl",
    }

    assert versioning.compute_config_hash(config_a) == versioning.compute_config_hash(
        config_b
    )


@pytest.mark.unit
def test_compute_config_hash_rejects_non_finite_numeric_values() -> None:
    with pytest.raises(
        ValueError,
        match="Canonical JSON serialization does not allow NaN or Infinity",
    ):
        versioning.compute_config_hash({"provider": "chembl", "limit": float("inf")})


@pytest.mark.unit
def test_get_pipeline_version_reads_dict_version() -> None:
    assert versioning.get_pipeline_version({"version": "2.3.4"}) == "2.3.4"


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.pkg_version", return_value="9.9.9")
def test_get_pipeline_version_falls_back_to_package_version(
    _mock_pkg_version: MagicMock,
) -> None:
    assert versioning.get_pipeline_version({}) == "9.9.9"


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.pkg_version", side_effect=RuntimeError)
def test_get_pipeline_version_falls_back_to_unknown_on_error(
    _mock_pkg_version: MagicMock,
) -> None:
    assert versioning.get_pipeline_version({}) == "unknown"
