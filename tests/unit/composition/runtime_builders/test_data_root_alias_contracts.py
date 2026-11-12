"""Trusted aliases require contained roots and an explicit runtime binding."""

from __future__ import annotations

from types import SimpleNamespace
import pytest
from bioetl.composition import control_plane_paths
from bioetl.composition.runtime_builders import run_manifest_data_roots

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("subject", [control_plane_paths, run_manifest_data_roots])
@pytest.mark.parametrize("value", [None, " "])
def test_absent_alias_does_not_resolve_to_the_working_directory(subject, value):
    assert (
        subject.resolve_dashboard_data_alias_base(
            settings=SimpleNamespace(dashboard_data_root=value)
        )
        is None
    )


@pytest.mark.parametrize("subject", [control_plane_paths, run_manifest_data_roots])
def test_explicit_alias_is_resolved_and_catalog_uses_its_control_subtree(
    subject, tmp_path
):
    settings = SimpleNamespace(dashboard_data_root=tmp_path / "alias")
    assert (
        subject.resolve_dashboard_data_alias_base(settings=settings)
        == (tmp_path / "alias").resolve()
    )
    assert (
        control_plane_paths.live_run_manifest_catalog(settings)
        == (tmp_path / "alias/output/control/run_manifest").resolve()
    )


@pytest.mark.parametrize("subject", [control_plane_paths, run_manifest_data_roots])
@pytest.mark.parametrize(
    "runtime_id,skip_reason,expected",
    [(None, None, False), ("a" * 64, "untrusted", False), ("a" * 64, None, True)],
)
def test_binding_requires_identity_and_no_skip_reason(
    subject, tmp_path, runtime_id, skip_reason, expected
):
    context = subject.EvidenceLocationBindingContext(
        write_data_root=tmp_path,
        alias_base=tmp_path,
        root_alias="dashboard_data",
        relative_data_root=".",
        runtime_source_id=runtime_id,
        report_root=None,
        skip_reason=skip_reason,
    )
    assert context.registration_allowed is expected


@pytest.mark.parametrize(
    "relative,expected",
    [(".", "."), ("output/silver", "output/silver"), ("../outside", None)],
)
def test_data_root_membership_preserves_the_alias_boundary(
    tmp_path, relative, expected
):
    alias = tmp_path / "alias"
    assert (
        run_manifest_data_roots.relative_data_root_under_alias(
            write_data_root=alias / relative, alias_base=alias
        )
        == expected
    )


@pytest.mark.parametrize("resolved", [False, True])
def test_registration_identity_uses_only_declared_repository_source(
    monkeypatch, resolved, tmp_path
):
    subject = run_manifest_data_roots
    observed = {}
    monkeypatch.setattr(
        subject,
        "__file__",
        str(tmp_path / "fixture/src/bioetl/composition/runtime_builders/roots.py"),
    )

    def repository_environment(repo_root, **kwargs):
        observed.update(root=repo_root, **kwargs)
        return {subject.RUNTIME_SOURCE_ID_ENV: "repository"}

    def resolve_identity(**kwargs):
        assert kwargs["process_environment"] == {
            subject.RUNTIME_SOURCE_ID_ENV: "configured"
        }
        assert kwargs["repository_environment"] == {
            subject.RUNTIME_SOURCE_ID_ENV: "repository"
        }
        return SimpleNamespace(
            is_resolved=resolved, value="verified-source" if resolved else None
        )

    monkeypatch.setattr(
        subject, "load_repository_source_environment", repository_environment
    )
    monkeypatch.setattr(subject, "resolve_runtime_source_identity", resolve_identity)
    result = subject.resolve_registration_runtime_source_id(
        SimpleNamespace(runtime_source_id=" configured ")
    )
    assert result == ("verified-source" if resolved else None)
    assert observed["names"] == (subject.RUNTIME_SOURCE_ID_ENV,)
    assert observed["root"] == (tmp_path / "fixture").resolve()
