# pyright: reportArgumentType=false
"""Regression tests for the canonical runtime source identity resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.run_reports.source_identity import (
    IDENTITY_RESOLUTION_INVALID,
    IDENTITY_SOURCE_CONTAINER_ENVIRONMENT,
    IDENTITY_SOURCE_CONTAINER_LABEL,
    IDENTITY_SOURCE_PROCESS_ENVIRONMENT,
    IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT,
    IDENTITY_SOURCE_RUNTIME_ROOT,
    IDENTITY_STATE_ALIGNED,
    IDENTITY_STATE_FOREIGN,
    IDENTITY_STATE_INVALID,
    IDENTITY_STATE_MISSING,
    RUNTIME_SOURCE_ID_ENV,
    compare_runtime_source_identity,
    compute_runtime_source_id,
    load_repository_source_environment,
    normalize_runtime_path,
    resolve_runtime_source_identity,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "root",
    [
        r"E:\github\BioactivityDataAcquisition",
        "E:/github/BioactivityDataAcquisition",
        "/mnt/e/github/BioactivityDataAcquisition",
        "/run/desktop/mnt/host/e/github/BioactivityDataAcquisition",
        "/host_mnt/e/github/BioactivityDataAcquisition",
    ],
)
def test_compute_identity_normalizes_windows_wsl_and_desktop(root: str) -> None:
    identity = compute_runtime_source_id(
        runtime_root=root,
        mounts={
            "/app/data": f"{root}/data",
            "/app/reports": f"{root}/reports",
        },
    )
    canonical = compute_runtime_source_id(
        runtime_root="/mnt/e/github/BioactivityDataAcquisition",
        mounts={
            "/app/data": "/mnt/e/github/BioactivityDataAcquisition/data",
            "/app/reports": "/mnt/e/github/BioactivityDataAcquisition/reports",
        },
    )
    assert identity == canonical


def test_normalize_docker_desktop_wsl_bind_path() -> None:
    desktop = (
        "/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/Ubuntu/abc123/reports"
    )
    host = "/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/abc123/reports"
    assert normalize_runtime_path(desktop, root=host) == normalize_runtime_path(
        host,
        root=host,
    )


def test_normalize_runtime_path_resolves_relative_root_without_recursion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    normalized = normalize_runtime_path("reports/output", root="workspace")
    expected = normalize_runtime_path(
        tmp_path / "workspace" / "reports" / "output",
        root=tmp_path,
    )

    assert normalized == expected
    assert normalized.endswith("/workspace/reports/output")


@pytest.mark.parametrize(
    ("path", "root"),
    [
        (
            "docker-compose.neo4j.yml",
            r"E:\github\BioactivityDataAcquisition",
        ),
        (
            "docker-compose.neo4j.yml",
            "E:/github/BioactivityDataAcquisition",
        ),
        (
            r"E:\github\BioactivityDataAcquisition\docker-compose.neo4j.yml",
            r"E:\github\BioactivityDataAcquisition",
        ),
        (
            "/mnt/e/github/bioactivitydataacquisition/docker-compose.neo4j.yml",
            r"E:\github\BioactivityDataAcquisition",
        ),
        (
            "/mnt/e/github/BioactivityDataAcquisition/docker-compose.neo4j.yml",
            "E:/github/BioactivityDataAcquisition",
        ),
        (
            "/run/desktop/mnt/host/e/github/BioactivityDataAcquisition/docker-compose.neo4j.yml",
            r"E:\github\BioactivityDataAcquisition",
        ),
    ],
)
def test_normalize_runtime_path_windows_and_wsl_compose_file_are_equal(
    path: str,
    root: str,
) -> None:
    canonical = "/mnt/e/github/bioactivitydataacquisition/docker-compose.neo4j.yml"
    assert normalize_runtime_path(path, root=root) == canonical


def test_normalize_runtime_path_foreign_clone_stays_distinct() -> None:
    canonical = r"E:\github\BioactivityDataAcquisition"
    foreign = r"E:\other-clone\BioactivityDataAcquisition2"
    assert normalize_runtime_path(
        "docker-compose.yml",
        root=canonical,
    ) != normalize_runtime_path("docker-compose.yml", root=foreign)


@pytest.mark.parametrize(
    ("kwargs", "expected_source"),
    [
        (
            {
                "computed_identity": "a" * 64,
                "process_environment": {RUNTIME_SOURCE_ID_ENV: "b" * 64},
                "repository_environment": {RUNTIME_SOURCE_ID_ENV: "c" * 64},
                "container_environment": {RUNTIME_SOURCE_ID_ENV: "d" * 64},
                "container_labels": {"io.bioetl.dashboard-source-id": "e" * 64},
            },
            IDENTITY_SOURCE_RUNTIME_ROOT,
        ),
        (
            {
                "process_environment": {RUNTIME_SOURCE_ID_ENV: "b" * 64},
                "repository_environment": {RUNTIME_SOURCE_ID_ENV: "c" * 64},
                "container_environment": {RUNTIME_SOURCE_ID_ENV: "d" * 64},
                "container_labels": {"io.bioetl.dashboard-source-id": "e" * 64},
            },
            IDENTITY_SOURCE_PROCESS_ENVIRONMENT,
        ),
        (
            {
                "repository_environment": {RUNTIME_SOURCE_ID_ENV: "c" * 64},
                "container_environment": {RUNTIME_SOURCE_ID_ENV: "d" * 64},
                "container_labels": {"io.bioetl.dashboard-source-id": "e" * 64},
            },
            IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT,
        ),
        (
            {
                "container_environment": {RUNTIME_SOURCE_ID_ENV: "d" * 64},
                "container_labels": {"io.bioetl.dashboard-source-id": "e" * 64},
            },
            IDENTITY_SOURCE_CONTAINER_ENVIRONMENT,
        ),
        (
            {
                "container_labels": {"io.bioetl.dashboard-source-id": "e" * 64},
            },
            IDENTITY_SOURCE_CONTAINER_LABEL,
        ),
    ],
)
def test_resolver_precedence(
    kwargs: dict[str, object],
    expected_source: str,
) -> None:
    resolution = resolve_runtime_source_identity(**kwargs)
    assert resolution.source == expected_source
    assert resolution.value is not None


def test_invalid_higher_precedence_value_does_not_fall_through() -> None:
    resolution = resolve_runtime_source_identity(
        process_environment={RUNTIME_SOURCE_ID_ENV: "not-a-digest"},
        repository_environment={RUNTIME_SOURCE_ID_ENV: "a" * 64},
    )
    assert resolution.status == IDENTITY_RESOLUTION_INVALID
    assert resolution.value is None
    assert resolution.source == IDENTITY_SOURCE_PROCESS_ENVIRONMENT
    assert resolution.state == IDENTITY_STATE_INVALID


def test_lower_precedence_disagreement_is_foreign_and_inconsistent() -> None:
    resolution = resolve_runtime_source_identity(
        computed_identity="a" * 64,
        process_environment={RUNTIME_SOURCE_ID_ENV: "b" * 64},
    )

    assert resolution.value == "a" * 64
    assert resolution.state == IDENTITY_STATE_FOREIGN
    assert resolution.conflicts == (IDENTITY_SOURCE_PROCESS_ENVIRONMENT,)
    assert resolution.is_consistent is False


@pytest.mark.parametrize(
    ("expected", "actual", "state"),
    [
        ("a" * 64, None, IDENTITY_STATE_MISSING),
        ("a" * 64, "invalid", IDENTITY_STATE_INVALID),
        ("a" * 64, "b" * 64, IDENTITY_STATE_FOREIGN),
        ("a" * 64, "A" * 64, IDENTITY_STATE_ALIGNED),
    ],
)
def test_comparison_states(
    expected: str,
    actual: str | None,
    state: str,
) -> None:
    assert (
        compare_runtime_source_identity(
            expected=expected,
            actual=actual,
        ).state
        == state
    )


def test_repository_env_loader_is_whitelisted_and_local_overrides(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        f"{RUNTIME_SOURCE_ID_ENV}={'a' * 64}\nSECRET_VALUE=do-not-read\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        f"{RUNTIME_SOURCE_ID_ENV}={'b' * 64}\n",
        encoding="utf-8",
    )
    loaded = load_repository_source_environment(
        tmp_path,
        names=(RUNTIME_SOURCE_ID_ENV,),
    )
    assert loaded == {RUNTIME_SOURCE_ID_ENV: "b" * 64}


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("value # inline comment", "value"),
        ("value#literal", "value#literal"),
        ('"value # literal"', "value # literal"),
        ("'value # literal'", "value # literal"),
    ],
)
def test_repository_env_loader_preserves_hash_literal_semantics(
    tmp_path: Path,
    raw_value: str,
    expected: str,
) -> None:
    (tmp_path / ".env").write_text(
        f"TEST_VALUE={raw_value}\n",
        encoding="utf-8",
    )

    loaded = load_repository_source_environment(
        tmp_path,
        names=("TEST_VALUE",),
    )

    assert loaded == {"TEST_VALUE": expected}
