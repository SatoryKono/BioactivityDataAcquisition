"""Shared test contracts for artifact-generator scripts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


WriteArtifactsFn = Callable[..., Any]
BuildArtifactsFn = Callable[[], Mapping[str, str]]
CheckArtifactsFn = Callable[[Path], int]
PayloadAssertionFn = Callable[[Any, Any], None]


def assert_written_core_artifacts_are_deterministic(
    tmp_path: Path,
    *,
    write_artifacts: WriteArtifactsFn,
    csv_name: str,
    md_name: str,
    write_kwargs: dict[str, Any] | None = None,
    payload_assertion: PayloadAssertionFn | None = None,
) -> None:
    """Assert repeated writes produce byte-identical core artifacts."""
    kwargs = write_kwargs or {}
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_payload = write_artifacts(first, **kwargs)
    second_payload = write_artifacts(second, **kwargs)

    assert (first / csv_name).read_text(encoding="utf-8") == (
        second / csv_name
    ).read_text(encoding="utf-8")
    assert (first / md_name).read_text(encoding="utf-8") == (
        second / md_name
    ).read_text(encoding="utf-8")
    if payload_assertion is not None:
        payload_assertion(first_payload, second_payload)


def assert_build_artifacts_are_stable(
    *,
    build_artifacts: BuildArtifactsFn,
    artifact_names: tuple[str, ...],
) -> None:
    """Assert in-memory artifacts are stable across repeated builds."""
    first = build_artifacts()
    second = build_artifacts()

    for artifact_name in artifact_names:
        assert first[artifact_name].encode("utf-8") == second[artifact_name].encode(
            "utf-8"
        )


def assert_check_artifacts_detects_drift(
    tmp_path: Path,
    *,
    build_artifacts: BuildArtifactsFn,
    check_artifacts: CheckArtifactsFn,
    csv_name: str,
    md_name: str,
) -> None:
    """Assert artifact drift detection trips when one core file changes."""
    out_dir = tmp_path / "matrix"
    payloads = build_artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / csv_name).write_text(payloads[csv_name], encoding="utf-8")
    (out_dir / md_name).write_text("drift", encoding="utf-8")

    assert check_artifacts(out_dir) == 1


def assert_check_artifacts_passes_for_fresh_outputs(
    tmp_path: Path,
    *,
    write_artifacts: WriteArtifactsFn,
    check_artifacts: CheckArtifactsFn,
    write_kwargs: dict[str, Any] | None = None,
) -> None:
    """Assert freshly written artifacts match the current generator output."""
    out_dir = tmp_path / "matrix"
    kwargs = write_kwargs or {}

    write_artifacts(out_dir, **kwargs)

    assert check_artifacts(out_dir) == 0


def assert_repeated_core_output_bytes_are_stable(
    tmp_path: Path,
    *,
    write_artifacts: WriteArtifactsFn,
    artifact_name: str,
    write_kwargs: dict[str, Any] | None = None,
) -> None:
    """Assert writing the same artifacts twice preserves exact bytes."""
    out_dir = tmp_path / "matrix"
    kwargs = write_kwargs or {}

    write_artifacts(out_dir, **kwargs)
    first_bytes = (out_dir / artifact_name).read_bytes()

    write_artifacts(out_dir, **kwargs)
    second_bytes = (out_dir / artifact_name).read_bytes()

    assert first_bytes == second_bytes
