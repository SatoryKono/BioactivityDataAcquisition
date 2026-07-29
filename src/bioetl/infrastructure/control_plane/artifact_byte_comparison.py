"""File-backed semantic-first artifact comparison adapter for forensic diffs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bioetl.domain.behavior.dataset_content_identity import (
    DATASET_CONTENT_HASH_OCCURRENCE_ONLY_FIELDS,
)
from bioetl.domain.ports import ArtifactByteComparisonPort

__all__ = ["FileArtifactByteComparisonAdapter"]

_SEMANTIC_SIDECAR_SUFFIXES = frozenset({".json", ".yaml", ".yml"})
_OCCURRENCE_ONLY_FIELDS = DATASET_CONTENT_HASH_OCCURRENCE_ONLY_FIELDS | frozenset(
    {"run_id", "manifest_id"}
)
_CandidatePath = tuple[str, Path]


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_paths(ref: Mapping[str, object]) -> tuple[tuple[str, Path], ...]:
    candidates: list[tuple[str, Path]] = []
    for key in ("artifact_path", "metadata_path", "path"):
        raw = ref.get(key)
        if raw:
            candidates.append((key, Path(str(raw)).resolve()))
    seen: dict[tuple[str, str], tuple[str, Path]] = {}
    for key, path in candidates:
        seen[(key, str(path))] = (key, path)
    return tuple(sorted(seen.values(), key=lambda item: (item[0], str(item[1]))))


def _is_semantic_sidecar(*, ref_key: str, path: Path) -> bool:
    return (
        ref_key == "metadata_path" or path.suffix.lower() in _SEMANTIC_SIDECAR_SUFFIXES
    )


def _load_structured_payload(path: Path) -> object | None:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload: object = json.loads(text)
        return payload
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
        return payload
    return None


def _strip_occurrence_only_fields(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_occurrence_only_fields(item)
            for key, item in value.items()
            if str(key) not in _OCCURRENCE_ONLY_FIELDS
        }
    if isinstance(value, list):
        return [_strip_occurrence_only_fields(item) for item in value]
    return value


def _mapping_difference_paths(
    left: Mapping[object, object],
    right: Mapping[object, object],
    *,
    prefix: str,
) -> tuple[str, ...]:
    paths: list[str] = []
    for key in sorted(set(left) | set(right), key=str):
        key_text = str(key)
        next_prefix = f"{prefix}.{key_text}" if prefix else key_text
        if key not in left or key not in right:
            paths.append(next_prefix)
            continue
        paths.extend(
            _collect_difference_paths(left[key], right[key], prefix=next_prefix)
        )
    return tuple(paths)


def _list_difference_paths(
    left: list[object],
    right: list[object],
    *,
    prefix: str,
) -> tuple[str, ...]:
    if len(left) != len(right):
        return (prefix or "value",)
    list_paths: list[str] = []
    for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
        next_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
        list_paths.extend(
            _collect_difference_paths(left_item, right_item, prefix=next_prefix)
        )
    return tuple(list_paths)


def _collect_difference_paths(
    left: object,
    right: object,
    *,
    prefix: str = "",
) -> tuple[str, ...]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return _mapping_difference_paths(left, right, prefix=prefix)
    if isinstance(left, list) and isinstance(right, list):
        return _list_difference_paths(left, right, prefix=prefix)
    if left == right:
        return ()
    return (prefix or "value",)


def _leaf_field_name(path: str) -> str:
    head = path.split("[", maxsplit=1)[0]
    return head.rsplit(".", maxsplit=1)[-1]


@dataclass
class _ArtifactComparisonState:
    compared_artifacts: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    mismatched_artifacts: list[str] = field(default_factory=list)
    raw_byte_mismatched_artifacts: list[str] = field(default_factory=list)
    occurrence_only_artifacts: list[str] = field(default_factory=list)
    raw_byte_only_artifacts: list[str] = field(default_factory=list)
    semantic_difference_fields: list[str] = field(default_factory=list)
    occurrence_difference_fields: list[str] = field(default_factory=list)

    def as_result(
        self,
        *,
        left_count: int,
        right_count: int,
    ) -> dict[str, object]:
        available = bool(left_count and right_count)
        same_candidate_count = left_count == right_count
        semantic_equivalent = (
            available
            and same_candidate_count
            and not self.missing_artifacts
            and not self.mismatched_artifacts
        )
        raw_byte_equivalent = (
            available
            and same_candidate_count
            and not self.missing_artifacts
            and not self.raw_byte_mismatched_artifacts
        )
        return {
            "available": available,
            "equivalent": semantic_equivalent,
            "semantic_equivalent": semantic_equivalent,
            "raw_byte_equivalent": raw_byte_equivalent,
            "occurrence_only": semantic_equivalent
            and bool(self.occurrence_only_artifacts),
            "compared_artifacts": self.compared_artifacts,
            "missing_artifacts": self.missing_artifacts,
            "mismatched_artifacts": self.mismatched_artifacts,
            "raw_byte_mismatched_artifacts": self.raw_byte_mismatched_artifacts,
            "occurrence_only_artifacts": self.occurrence_only_artifacts,
            "raw_byte_only_artifacts": self.raw_byte_only_artifacts,
            "semantic_difference_fields": self.semantic_difference_fields,
            "occurrence_difference_fields": self.occurrence_difference_fields,
            "comparison_scope": "artifact_and_metadata_paths",
            "comparison_mode": "semantic_first_with_raw_byte_forensics",
        }


def _flatten_candidate_paths(
    refs: Sequence[Mapping[str, object]],
) -> tuple[_CandidatePath, ...]:
    return tuple(candidate for ref in refs for candidate in _candidate_paths(ref))


def _label_pair(left: _CandidatePath, right: _CandidatePath) -> str:
    left_key, left_path = left
    right_key, right_path = right
    return f"{left_key}:{left_path} == {right_key}:{right_path}"


def _semantic_sidecar_pair(left: _CandidatePath, right: _CandidatePath) -> bool:
    left_key, left_path = left
    right_key, right_path = right
    return _is_semantic_sidecar(
        ref_key=left_key,
        path=left_path,
    ) and _is_semantic_sidecar(ref_key=right_key, path=right_path)


def _record_semantic_difference(
    state: _ArtifactComparisonState,
    *,
    label: str,
    ref_key: str,
    left_semantic: object,
    right_semantic: object,
) -> None:
    state.mismatched_artifacts.append(label)
    state.semantic_difference_fields.extend(
        _collect_difference_paths(
            left_semantic,
            right_semantic,
            prefix=ref_key,
        )
    )


def _record_nonsemantic_raw_difference(
    state: _ArtifactComparisonState,
    *,
    label: str,
    raw_byte_equivalent: bool,
) -> None:
    if not raw_byte_equivalent:
        state.mismatched_artifacts.append(label)


def _record_semantic_raw_difference(
    state: _ArtifactComparisonState,
    *,
    label: str,
    raw_difference_fields: tuple[str, ...],
    raw_byte_equivalent: bool,
) -> None:
    if raw_difference_fields and all(
        _leaf_field_name(path) in _OCCURRENCE_ONLY_FIELDS
        for path in raw_difference_fields
    ):
        state.occurrence_only_artifacts.append(label)
        state.occurrence_difference_fields.extend(raw_difference_fields)
        return
    if not raw_byte_equivalent:
        state.raw_byte_only_artifacts.append(label)


def _compare_semantic_sidecar_pair(
    state: _ArtifactComparisonState,
    *,
    left: _CandidatePath,
    right: _CandidatePath,
    label: str,
    raw_byte_equivalent: bool,
) -> None:
    left_key, left_path = left
    _, right_path = right
    left_payload = _load_structured_payload(left_path)
    right_payload = _load_structured_payload(right_path)
    if left_payload is None or right_payload is None:
        _record_nonsemantic_raw_difference(
            state,
            label=label,
            raw_byte_equivalent=raw_byte_equivalent,
        )
        return

    left_semantic = _strip_occurrence_only_fields(left_payload)
    right_semantic = _strip_occurrence_only_fields(right_payload)
    if left_semantic != right_semantic:
        _record_semantic_difference(
            state,
            label=label,
            ref_key=left_key,
            left_semantic=left_semantic,
            right_semantic=right_semantic,
        )
        return

    if left_payload != right_payload:
        _record_semantic_raw_difference(
            state,
            label=label,
            raw_difference_fields=_collect_difference_paths(
                left_payload,
                right_payload,
                prefix=left_key,
            ),
            raw_byte_equivalent=raw_byte_equivalent,
        )
        return
    if not raw_byte_equivalent:
        state.raw_byte_only_artifacts.append(label)


def _compare_existing_file_pair(
    state: _ArtifactComparisonState,
    *,
    left: _CandidatePath,
    right: _CandidatePath,
    label: str,
) -> None:
    _, left_path = left
    _, right_path = right
    if left_path.is_dir() or right_path.is_dir():
        return
    raw_byte_equivalent = _hash_path(left_path) == _hash_path(right_path)
    if not raw_byte_equivalent:
        state.raw_byte_mismatched_artifacts.append(label)
    if _semantic_sidecar_pair(left, right):
        _compare_semantic_sidecar_pair(
            state,
            left=left,
            right=right,
            label=label,
            raw_byte_equivalent=raw_byte_equivalent,
        )
        return
    _record_nonsemantic_raw_difference(
        state,
        label=label,
        raw_byte_equivalent=raw_byte_equivalent,
    )


def _compare_candidate_pair(
    state: _ArtifactComparisonState,
    *,
    left: _CandidatePath,
    right: _CandidatePath,
) -> None:
    label = _label_pair(left, right)
    left_path = left[1]
    right_path = right[1]
    if not left_path.exists() or not right_path.exists():
        state.missing_artifacts.append(label)
        return
    state.compared_artifacts.append(label)
    _compare_existing_file_pair(state, left=left, right=right, label=label)


def _record_overflow_paths(
    state: _ArtifactComparisonState,
    *,
    left_paths: tuple[_CandidatePath, ...],
    right_paths: tuple[_CandidatePath, ...],
) -> None:
    overflow = left_paths[len(right_paths) :] + right_paths[len(left_paths) :]
    state.missing_artifacts.extend(f"{key}:{path}" for key, path in overflow)


class FileArtifactByteComparisonAdapter(ArtifactByteComparisonPort):
    """Compare referenced artifacts semantically before falling back to raw bytes."""

    def compare_artifacts(
        self,
        left_refs: Sequence[Mapping[str, object]],
        right_refs: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        left_paths = _flatten_candidate_paths(left_refs)
        right_paths = _flatten_candidate_paths(right_refs)
        state = _ArtifactComparisonState()

        for left, right in zip(left_paths, right_paths, strict=False):
            _compare_candidate_pair(state, left=left, right=right)

        _record_overflow_paths(state, left_paths=left_paths, right_paths=right_paths)
        return state.as_result(left_count=len(left_paths), right_count=len(right_paths))
