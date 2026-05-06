"""File-backed artifact byte comparison adapter for forensic diffs."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

from bioetl.domain.ports import ArtifactByteComparisonPort

__all__ = ["FileArtifactByteComparisonAdapter"]


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_paths(ref: Mapping[str, object]) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for key in ("artifact_path", "metadata_path", "path"):
        raw = ref.get(key)
        if raw:
            candidates.append(Path(str(raw)).resolve())
    return tuple(sorted(set(candidates), key=str))


class FileArtifactByteComparisonAdapter(ArtifactByteComparisonPort):
    """Compare referenced artifacts by deterministic byte hash."""

    def compare_artifacts(
        self,
        left_refs: tuple[Mapping[str, object], ...] | list[Mapping[str, object]],
        right_refs: tuple[Mapping[str, object], ...] | list[Mapping[str, object]],
    ) -> dict[str, object]:
        left_paths = tuple(path for ref in left_refs for path in _candidate_paths(ref))
        right_paths = tuple(
            path for ref in right_refs for path in _candidate_paths(ref)
        )
        compared_artifacts: list[str] = []
        missing_artifacts: list[str] = []
        mismatched_artifacts: list[str] = []
        for left_path, right_path in zip(left_paths, right_paths, strict=False):
            label = f"{left_path} == {right_path}"
            if not left_path.exists() or not right_path.exists():
                missing_artifacts.append(label)
                continue
            compared_artifacts.append(label)
            if _hash_path(left_path) != _hash_path(right_path):
                mismatched_artifacts.append(label)
        overflow = left_paths[len(right_paths) :] + right_paths[len(left_paths) :]
        missing_artifacts.extend(str(path) for path in overflow)
        available = bool(left_paths and right_paths)
        return {
            "available": available,
            "equivalent": available
            and not missing_artifacts
            and not mismatched_artifacts
            and len(left_paths) == len(right_paths),
            "compared_artifacts": compared_artifacts,
            "missing_artifacts": missing_artifacts,
            "mismatched_artifacts": mismatched_artifacts,
            "comparison_scope": "artifact_and_metadata_paths",
        }
