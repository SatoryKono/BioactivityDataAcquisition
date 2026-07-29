# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for composition.services.versioning."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.services import versioning
from bioetl.domain.control_plane.run_manifest import DOCUMENTED_SOURCE_REVISION_STATES


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
        cwd=versioning._REPO_ROOT,
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
def test_get_git_commit_rejects_non_full_sha(mock_run: MagicMock) -> None:
    mock_run.return_value = SimpleNamespace(returncode=0, stdout="abc1234\n")

    assert versioning.get_git_commit() is None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_git_commit_returns_none_on_exception(mock_run: MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError("git missing")

    assert versioning.get_git_commit() is None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning._iter_windows_git_fallback_executables")
@patch("bioetl.composition.services.versioning.os.name", "nt")
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_git_commit_falls_back_to_explicit_windows_git_executable(
    mock_run: MagicMock,
    mock_candidates: MagicMock,
) -> None:
    full_hash = "d" * 40
    mock_candidates.return_value = ("C:/Program Files/Git/cmd/git.exe",)
    mock_run.side_effect = [
        SimpleNamespace(returncode=4294967295, stdout="", stderr=""),
        SimpleNamespace(returncode=0, stdout=f"{full_hash}\n", stderr=""),
    ]

    assert versioning.get_git_commit() == full_hash
    assert mock_run.call_count == 2


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_reports_clean_state(
    mock_run: MagicMock,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "b" * 40
    isolated = tmp_path / "external-cwd-clean"
    isolated.mkdir()
    monkeypatch.chdir(isolated)
    monkeypatch.setattr(
        versioning,
        "_get_repo_dependency_lock_hash",
        lambda: "sha256:" + "1" * 64,
    )
    mock_run.side_effect = [
        SimpleNamespace(returncode=0, stdout=f"{full_hash}\n"),
        SimpleNamespace(returncode=0, stdout=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "clean"
    assert provenance.dependency_lock_hash is not None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_reports_dirty_state(
    mock_run: MagicMock,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "c" * 40
    isolated = tmp_path / "external-cwd-dirty"
    isolated.mkdir()
    monkeypatch.chdir(isolated)
    monkeypatch.setattr(
        versioning,
        "_get_repo_dependency_lock_hash",
        lambda: "sha256:" + "2" * 64,
    )
    mock_run.side_effect = [
        SimpleNamespace(returncode=0, stdout=f"{full_hash}\n"),
        SimpleNamespace(returncode=1, stdout=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "dirty"
    assert provenance.dependency_lock_hash is not None


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_reports_documented_git_unavailable_state(
    mock_run: MagicMock,
) -> None:
    mock_run.side_effect = FileNotFoundError("git missing")

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit is None
    assert provenance.source_revision_state == "git_unavailable"
    assert provenance.source_revision_state in DOCUMENTED_SOURCE_REVISION_STATES


@pytest.mark.unit
@patch("bioetl.composition.services.versioning._iter_windows_git_fallback_executables")
@patch("bioetl.composition.services.versioning.os.name", "nt")
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_uses_same_windows_git_fallback_for_dirty_check(
    mock_run: MagicMock,
    mock_candidates: MagicMock,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "e" * 40
    isolated = tmp_path / "external-cwd-windows"
    isolated.mkdir()
    monkeypatch.chdir(isolated)
    monkeypatch.setattr(
        versioning,
        "_get_repo_dependency_lock_hash",
        lambda: "sha256:" + "3" * 64,
    )
    mock_candidates.return_value = ("C:/Program Files/Git/cmd/git.exe",)
    mock_run.side_effect = [
        SimpleNamespace(returncode=4294967295, stdout="", stderr=""),
        SimpleNamespace(returncode=0, stdout=f"{full_hash}\n", stderr=""),
        SimpleNamespace(returncode=4294967295, stdout="", stderr=""),
        SimpleNamespace(returncode=0, stdout="", stderr=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "clean"
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
def test_get_dependency_lock_hash_uses_runtime_path_class(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_root = tmp_path / "runtime-tree"
    runtime_nested = runtime_root / "nested"
    runtime_nested.mkdir(parents=True)
    lockfile = runtime_root / "uv.lock"
    lockfile.write_text("version = 1\n", encoding="utf-8")

    process_cwd = tmp_path / "process-cwd"
    process_cwd.mkdir()
    monkeypatch.chdir(process_cwd)

    class RuntimePath:
        @staticmethod
        def cwd():
            return runtime_nested

    monkeypatch.setattr(versioning, "_RUNTIME_PATH_CLS", RuntimePath)
    versioning.get_dependency_lock_hash.cache_clear()

    digest = versioning.get_dependency_lock_hash()

    assert isinstance(digest, str)
    assert digest.startswith("sha256:")


@pytest.mark.unit
def test_get_dependency_lock_hash_returns_none_without_supported_lockfile(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated = tmp_path / "work" / "nested"
    isolated.mkdir(parents=True)
    monkeypatch.chdir(isolated)
    versioning.get_dependency_lock_hash.cache_clear()

    assert versioning.get_dependency_lock_hash() is None


@pytest.mark.unit
def test_should_try_windows_git_fallback_branch_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(versioning.os, "name", "posix", raising=False)
    assert (
        versioning._should_try_windows_git_fallback(
            None,
            accepted_returncodes=(0,),
        )
        is False
    )

    monkeypatch.setattr(versioning.os, "name", "nt", raising=False)
    assert versioning._should_try_windows_git_fallback(None, accepted_returncodes=(0,))
    assert not versioning._should_try_windows_git_fallback(
        SimpleNamespace(returncode=0),
        accepted_returncodes=(0,),
    )
    assert not versioning._should_try_windows_git_fallback(
        SimpleNamespace(returncode=128),
        accepted_returncodes=(0,),
    )
    assert versioning._should_try_windows_git_fallback(
        SimpleNamespace(returncode=4294967295),
        accepted_returncodes=(0,),
    )


@pytest.mark.unit
def test_iter_windows_git_fallback_executables_discovers_unique_git_exe(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_one = tmp_path / "git-one"
    bin_two = tmp_path / "git-two"
    bin_one.mkdir()
    bin_two.mkdir()
    git_one = bin_one / "git.exe"
    git_two = bin_two / "git.exe"
    git_one.write_text("", encoding="utf-8")
    git_two.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        versioning.os,
        "get_exec_path",
        lambda: [str(bin_one), str(bin_one), str(bin_two), str(tmp_path / "empty")],
    )

    assert versioning._iter_windows_git_fallback_executables() == (
        str(git_one.resolve()),
        str(git_two.resolve()),
    )


@pytest.mark.unit
@patch("bioetl.composition.services.versioning._iter_windows_git_fallback_executables")
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_run_git_command_preserves_repo_failures_without_windows_retry(
    mock_run: MagicMock,
    mock_candidates: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(versioning.os, "name", "nt", raising=False)
    mock_run.return_value = SimpleNamespace(returncode=128, stdout="", stderr="")

    result = versioning._run_git_command("rev-parse", "HEAD")

    assert result.returncode == 128
    mock_candidates.assert_not_called()
    mock_run.assert_called_once()


@pytest.mark.unit
@patch("bioetl.composition.services.versioning._iter_windows_git_fallback_executables")
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_run_git_command_returns_last_windows_fallback_result_after_failures(
    mock_run: MagicMock,
    mock_candidates: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(versioning.os, "name", "nt", raising=False)
    mock_candidates.return_value = ("C:/Git/git.exe", "D:/Git/git.exe")
    mock_run.side_effect = [
        OSError("shim failed"),
        OSError("candidate failed"),
        SimpleNamespace(returncode=2, stdout="", stderr="bad fallback"),
    ]

    result = versioning._run_git_command("rev-parse", "HEAD")

    assert result.returncode == 2
    assert mock_run.call_count == 3


@pytest.mark.unit
def test_get_repo_dependency_lock_hash_reads_repo_root_lockfile(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(versioning, "_REPO_ROOT", tmp_path)

    digest = versioning._get_repo_dependency_lock_hash()

    assert isinstance(digest, str)
    assert digest.startswith("sha256:")


@pytest.mark.unit
def test_get_repo_dependency_lock_hash_falls_back_to_git_show(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(versioning, "_REPO_ROOT", tmp_path)

    def _fake_run_git_command(*arguments: str) -> object:
        calls.append(arguments)
        if arguments == ("show", "HEAD:poetry.lock"):
            return SimpleNamespace(returncode=0, stdout="poetry-lock\n")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(versioning, "_run_git_command", _fake_run_git_command)

    digest = versioning._get_repo_dependency_lock_hash()

    assert isinstance(digest, str)
    assert digest.startswith("sha256:")
    assert calls == [("show", "HEAD:uv.lock"), ("show", "HEAD:poetry.lock")]


@pytest.mark.unit
def test_get_code_revision_provenance_reports_unknown_when_dirty_check_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "a" * 40
    monkeypatch.setattr(versioning, "get_git_commit", lambda: full_hash)
    monkeypatch.setattr(versioning, "get_dependency_lock_hash", lambda: None)
    monkeypatch.setattr(versioning, "_get_repo_dependency_lock_hash", lambda: None)
    monkeypatch.setattr(versioning, "_run_git_command", lambda *args, **kwargs: None)
    versioning.get_code_revision_provenance.cache_clear()

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "dirty_state_unknown"


@pytest.mark.unit
def test_get_code_revision_provenance_reports_unknown_on_unexpected_returncode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "a" * 40
    monkeypatch.setattr(versioning, "get_git_commit", lambda: full_hash)
    monkeypatch.setattr(versioning, "get_dependency_lock_hash", lambda: "sha256:abc")
    monkeypatch.setattr(
        versioning,
        "_run_git_command",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout=""),
    )
    versioning.get_code_revision_provenance.cache_clear()

    provenance = versioning.get_code_revision_provenance()

    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "dirty_state_unknown"


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.subprocess.run")
def test_get_code_revision_provenance_falls_back_to_repo_lockfile_outside_runtime_tree(
    mock_run: MagicMock,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_hash = "f" * 40
    isolated = tmp_path / "external-cwd"
    isolated.mkdir()
    monkeypatch.chdir(isolated)
    mock_run.side_effect = [
        SimpleNamespace(returncode=0, stdout=f"{full_hash}\n"),
        SimpleNamespace(returncode=0, stdout="version = 1\n"),
        SimpleNamespace(returncode=0, stdout=""),
    ]

    provenance = versioning.get_code_revision_provenance()

    assert versioning.get_dependency_lock_hash() is None
    assert provenance.git_commit == full_hash
    assert provenance.source_revision_state == "clean"
    assert provenance.dependency_lock_hash is not None


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
def test_compute_config_hash_supports_pydantic_model_dump_path() -> None:
    class ModelConfig:
        def model_dump(self, *, mode: str, exclude_none: bool) -> dict[str, object]:
            assert mode == "json"
            assert exclude_none is True
            return {"version": "1.0.0", "nested": {"x": 1}}

    digest = versioning.compute_config_hash(ModelConfig())

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
def test_compute_config_hash_rejects_non_json_like_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(versioning, "_normalize_for_hash", lambda obj: "not-json-like")

    with pytest.raises(TypeError, match="must produce JSON-like data"):
        versioning.compute_config_hash({"provider": "chembl"})


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
def test_get_pipeline_version_reads_object_version() -> None:
    assert versioning.get_pipeline_version(SimpleNamespace(version="3.4.5")) == "3.4.5"


@pytest.mark.unit
@patch("bioetl.composition.services.versioning.pkg_version", return_value="8.8.8")
def test_get_pipeline_version_handles_absent_config(
    _mock_pkg_version: MagicMock,
) -> None:
    assert versioning.get_pipeline_version(None) == "8.8.8"


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
