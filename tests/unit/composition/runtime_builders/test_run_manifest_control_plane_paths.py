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
"""Branch coverage for writable run-manifest control-plane paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.composition import control_plane_paths as paths_subject
from bioetl.composition.runtime_builders import (
    run_manifest_data_roots as subject,
)

pytestmark = pytest.mark.unit


def test_control_plane_root_uses_explicit_data_dir(tmp_path: Path) -> None:
    settings = SimpleNamespace(data_dir=tmp_path)

    assert paths_subject.control_plane_root(settings, "manifests") == (
        tmp_path / "output/control/manifests"
    )


def test_resolve_data_root_uses_local_data_when_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subject.os, "access", lambda _path, _mode: True)

    assert subject.resolve_data_root(SimpleNamespace(data_dir=None)) == Path("data")
    assert (tmp_path / "data").is_dir()


@pytest.mark.parametrize("failure_mode", ["mkdir", "access"])
def test_resolve_data_root_falls_back_when_local_data_is_unusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    fallback = tmp_path / "private"
    monkeypatch.setattr(subject, "private_fallback_data_root", lambda: fallback)
    if failure_mode == "mkdir":
        (tmp_path / "data").write_text("not-a-directory", encoding="utf-8")
    else:
        monkeypatch.setattr(subject.os, "access", lambda _path, _mode: False)

    assert subject.resolve_data_root(SimpleNamespace(data_dir=None)) == fallback


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

    assert subject.private_fallback_data_root() == fallback
    assert calls == [preferred, fallback]


def test_prepare_private_runtime_dir_creates_private_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested/private"

    assert subject._prepare_private_runtime_dir(target) == target
    assert target.is_dir()


@pytest.mark.parametrize("module", [subject, paths_subject])
@pytest.mark.parametrize("configured", [None, "", "   "])
def test_alias_resolution_keeps_absent_configuration_unbound(module, configured):
    assert (
        module.resolve_dashboard_data_alias_base(
            settings=SimpleNamespace(dashboard_data_root=configured)
        )
        is None
    )


@pytest.mark.parametrize("module", [subject, paths_subject])
def test_alias_resolution_contains_write_roots(module, tmp_path):
    assert (
        module.resolve_dashboard_data_alias_base(
            settings=SimpleNamespace(dashboard_data_root=tmp_path)
        )
        == tmp_path.resolve()
    )
    assert (
        module.relative_data_root_under_alias(
            write_data_root=tmp_path, alias_base=tmp_path
        )
        == "."
    )
    assert (
        module.relative_data_root_under_alias(
            write_data_root=tmp_path / "data", alias_base=tmp_path
        )
        == "data"
    )
    assert (
        module.relative_data_root_under_alias(
            write_data_root=tmp_path.parent / "other", alias_base=tmp_path
        )
        is None
    )


@pytest.mark.parametrize("module", [subject, paths_subject])
@pytest.mark.parametrize(
    "source_id,skip,expected",
    [(None, None, False), ("a" * 64, None, True), ("a" * 64, "outside_alias", False)],
)
def test_registration_requires_identity_and_no_skip(
    module, source_id, skip, expected, tmp_path
):
    context = module.EvidenceLocationBindingContext(
        write_data_root=tmp_path,
        alias_base=tmp_path,
        root_alias="dashboard_data",
        relative_data_root=".",
        runtime_source_id=source_id,
        report_root=None,
        skip_reason=skip,
    )
    assert context.registration_allowed is expected


@pytest.mark.parametrize(
    "configured,expected", [("a" * 64, "a" * 64), ("invalid", None), (None, None)]
)
def test_registration_source_id_resolves_only_valid_explicit_identity(
    configured, expected, monkeypatch
):
    monkeypatch.setattr(
        subject, "load_repository_source_environment", lambda *a, **k: {}
    )
    assert (
        subject.resolve_registration_runtime_source_id(
            SimpleNamespace(runtime_source_id=configured)
        )
        == expected
    )


def test_live_catalog_uses_trusted_alias(tmp_path):
    assert (
        paths_subject.live_run_manifest_catalog(
            SimpleNamespace(dashboard_data_root=tmp_path)
        )
        == tmp_path / "output/control/run_manifest"
    )
