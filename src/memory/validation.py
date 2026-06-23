"""Validation helpers for the project-memory scaffold and note formats."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.notes import (
    NOTE_READ_TIMEOUT_SECONDS,
    extract_markdown_headings,
    normalize_text_key,
    parse_markdown_note,
    parse_markdown_note_metadata,
)
from memory.resources import (
    CATALOG_DIR,
    MEMORY_ROOT,
    POLICY_DIR,
    REQUIRED_CATALOG_FILES,
    REQUIRED_POLICY_FILES,
    REQUIRED_SCHEMA_FILES,
    SCHEMA_DIR,
    load_json_resource,
    load_yaml_resource,
)

STORAGE_POLICY_PATH = "policy/storage.yaml"
CURATED_KIND_BY_DIR = {
    "decisions": "decision",
    "incidents": "incident",
    "lessons": "lesson",
    "domain_knowledge": "domain_knowledge",
}
REBUILD_ONLY_DIRS = (
    "src/memory/rag/manifests",
    "src/memory/graph/exports",
    "src/memory/graph/projections",
    "src/memory/graph/indexes",
    "src/memory/timeline/events",
)
DEFAULT_EPISODIC_NOTE_SCAN_LIMIT = 200
VALIDATION_NOTE_READ_TIMEOUT_SECONDS = max(NOTE_READ_TIMEOUT_SECONDS, 15.0)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Represents a memory validation failure."""

    path: str
    message: str


def _validate_exists(path: Path, issues: list[ValidationIssue]) -> None:
    if not path.exists():
        issues.append(ValidationIssue(path=str(path), message="missing required file"))


def _validate_schema_shape(
    path: Path, payload: Any, issues: list[ValidationIssue]
) -> None:
    if not isinstance(payload, dict):
        issues.append(
            ValidationIssue(path=str(path), message="schema root must be a JSON object")
        )
        return
    for key in ("$schema", "title", "type"):
        if key not in payload:
            issues.append(
                ValidationIssue(
                    path=str(path), message=f"schema missing required key: {key}"
                )
            )


def _validate_source_priority(
    policy_payload: dict[str, Any],
    source_registry: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    known_source_ids = {
        item.get("id")
        for item in source_registry.get("sources", [])
        if isinstance(item, dict) and item.get("id")
    }
    ordered_sources = policy_payload.get("ordered_sources", [])
    if not isinstance(ordered_sources, list):
        issues.append(
            ValidationIssue(
                path="policy/source_priority.yaml",
                message="ordered_sources must be a list",
            )
        )
        return
    for source_id in ordered_sources:
        if source_id not in known_source_ids:
            issues.append(
                ValidationIssue(
                    path="policy/source_priority.yaml",
                    message=f"unknown source id in ordered_sources: {source_id}",
                )
            )


def _validate_storage_policy(
    storage_policy: dict[str, Any],
    retention_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    valid_modes = _validate_storage_modes(storage_policy, issues)
    storage_classes, retention_classes = _validate_storage_class_maps(
        storage_policy, retention_policy, issues
    )
    if valid_modes is None or storage_classes is None or retention_classes is None:
        return

    _validate_storage_class_coverage(storage_classes, retention_classes, issues)
    for artifact_class, entry in storage_classes.items():
        _validate_storage_class_entry(artifact_class, entry, valid_modes, issues)


def _is_tracked_generated_memory_artifact(relative_path: str) -> bool:
    path = Path(relative_path)
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        return True
    if path.name in {"README.md", ".gitignore"}:
        return False
    return any(relative_path.startswith(f"{prefix}/") for prefix in REBUILD_ONLY_DIRS)


def _tracked_memory_files(memory_root: Path) -> list[str]:
    repo_root = memory_root.parent.parent
    if not (repo_root / ".git").exists():
        return []
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "src/memory"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _validate_tracked_generated_artifacts(
    memory_root: Path,
    issues: list[ValidationIssue],
) -> None:
    for relative_path in _tracked_memory_files(memory_root):
        if _is_tracked_generated_memory_artifact(relative_path):
            issues.append(
                ValidationIssue(
                    path=relative_path,
                    message=(
                        "generated or rebuild-only memory artifact must not be "
                        "tracked in git"
                    ),
                )
            )


def _is_working_tree_junk(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc"


def _is_tolerated_memory_bootstrap_cache(path: Path, memory_root: Path) -> bool:
    try:
        rel_path = path.relative_to(memory_root)
    except ValueError:
        return False
    return (
        rel_path.parts == ("__pycache__", path.name)
        and path.name.startswith("__init__.")
        and path.suffix == ".pyc"
    )


def _validate_working_tree_junk(
    memory_root: Path,
    issues: list[ValidationIssue],
) -> None:
    if not memory_root.exists():
        return
    for path in sorted(memory_root.rglob("*")):
        if _is_tolerated_memory_bootstrap_cache(path, memory_root):
            continue
        if path.is_file() and _is_working_tree_junk(path):
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message="working-tree Python cache should not live under src/memory",
                )
            )


def _validate_storage_modes(
    storage_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> list[str] | None:
    valid_modes = storage_policy.get("storage_modes", [])
    if not isinstance(valid_modes, list) or not all(
        isinstance(mode, str) for mode in valid_modes
    ):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message="storage_modes must be a list of strings",
            )
        )
        return None
    return valid_modes


def _validate_storage_class_maps(
    storage_policy: dict[str, Any],
    retention_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    storage_classes = storage_policy.get("artifact_classes", {})
    retention_classes = retention_policy.get("artifact_classes", {})
    if not isinstance(storage_classes, dict):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message="artifact_classes must be a mapping",
            )
        )
        return None, None
    if not isinstance(retention_classes, dict):
        issues.append(
            ValidationIssue(
                path="policy/retention.yaml",
                message="artifact_classes must be a mapping",
            )
        )
        return None, None
    return storage_classes, retention_classes


def _validate_storage_class_coverage(
    storage_classes: dict[str, Any],
    retention_classes: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    for artifact_class in retention_classes:
        if artifact_class not in storage_classes:
            issues.append(
                ValidationIssue(
                    path=STORAGE_POLICY_PATH,
                    message=f"missing storage policy for artifact class: {artifact_class}",
                )
            )


def _validate_storage_class_entry(
    artifact_class: str,
    entry: Any,
    valid_modes: list[str],
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(entry, dict):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=f"storage policy entry must be a mapping: {artifact_class}",
            )
        )
        return
    _validate_storage_mode(artifact_class, entry, valid_modes, issues)
    _validate_commit_to_git(artifact_class, entry, issues)
    _validate_default_paths(artifact_class, entry, issues)


def _validate_storage_mode(
    artifact_class: str,
    entry: dict[str, Any],
    valid_modes: list[str],
    issues: list[ValidationIssue],
) -> None:
    storage_mode = entry.get("storage_mode")
    if storage_mode not in valid_modes:
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=f"invalid storage_mode for {artifact_class}: {storage_mode}",
            )
        )


def _validate_commit_to_git(
    artifact_class: str,
    entry: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    commit_to_git = entry.get("commit_to_git")
    if not isinstance(commit_to_git, bool):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=f"commit_to_git must be boolean for {artifact_class}",
            )
        )


def _validate_default_paths(
    artifact_class: str,
    entry: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    default_paths = entry.get("default_paths")
    if not isinstance(default_paths, list) or not default_paths:
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=f"default_paths must be a non-empty list for {artifact_class}",
            )
        )
        return
    for default_path in default_paths:
        _validate_default_path(artifact_class, default_path, issues)


def _validate_default_path(
    artifact_class: str,
    default_path: Any,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(default_path, str):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=f"default_paths must contain strings for {artifact_class}",
            )
        )
        return
    if not default_path.startswith("src/memory/"):
        issues.append(
            ValidationIssue(
                path=STORAGE_POLICY_PATH,
                message=(
                    f"default path for {artifact_class} must stay under src/memory/: "
                    f"{default_path}"
                ),
            )
        )


def _memory_root(root: Path | None) -> Path:
    return (root or MEMORY_ROOT).resolve()


def _required_policy_paths(root: Path) -> list[Path]:
    policy_dir = root / POLICY_DIR.name
    return [policy_dir / name for name in REQUIRED_POLICY_FILES]


def _required_catalog_paths(root: Path) -> list[Path]:
    catalog_dir = root / CATALOG_DIR.name
    return [catalog_dir / name for name in REQUIRED_CATALOG_FILES]


def _required_schema_paths(root: Path) -> list[Path]:
    schema_dir = root / SCHEMA_DIR.name
    return [schema_dir / name for name in REQUIRED_SCHEMA_FILES]


def _note_dirs(root: Path) -> dict[str, list[Path]]:
    return {
        "curated_note": [
            root / "curated" / "decisions",
            root / "curated" / "incidents",
            root / "curated" / "lessons",
            root / "curated" / "domain_knowledge",
        ],
        "episodic_note": [
            root / "episodic" / "sessions",
            root / "episodic" / "summaries",
        ],
    }


def _bounded_episodic_note_paths(
    directory: Path,
    *,
    limit: int | None,
) -> list[Path]:
    paths = sorted(
        path
        for path in directory.rglob("*.md")
        if path.name != "README.md" and "templates" not in path.parts
    )
    if limit is None:
        return paths
    return paths[:limit]


def _iter_note_paths(
    root: Path,
    *,
    include_all_episodic_notes: bool = False,
) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for artifact_class, directories in _note_dirs(root).items():
        for directory in directories:
            if not directory.exists():
                continue
            if artifact_class == "episodic_note":
                limit = (
                    None
                    if include_all_episodic_notes
                    else DEFAULT_EPISODIC_NOTE_SCAN_LIMIT
                )
                note_paths = _bounded_episodic_note_paths(directory, limit=limit)
            else:
                note_paths = [
                    path
                    for path in sorted(directory.rglob("*.md"))
                    if path.name != "README.md" and "templates" not in path.parts
                ]
            for path in note_paths:
                result.append((artifact_class, path))
    return result


def _normalize_target_dir(target_dir: str) -> str:
    normalized = target_dir.replace("\\", "/").strip("/")
    prefix = "src/memory/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def _rule_map(placement_rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rules = placement_rules.get("rules", [])
    if not isinstance(rules, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if isinstance(rule, dict) and isinstance(rule.get("artifact_class"), str):
            mapped[rule["artifact_class"]] = rule
    return mapped


def _is_string_value(value: Any) -> bool:
    return isinstance(value, str)


def _is_integer_value(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_boolean_value(value: Any) -> bool:
    return isinstance(value, bool)


def _is_array_value(value: Any) -> bool:
    return isinstance(value, list)


def _is_object_value(value: Any) -> bool:
    return isinstance(value, dict)


def _is_null_value(value: Any) -> bool:
    return value is None


SCHEMA_TYPE_CHECKS = {
    "string": _is_string_value,
    "integer": _is_integer_value,
    "number": _is_number_value,
    "boolean": _is_boolean_value,
    "array": _is_array_value,
    "object": _is_object_value,
    "null": _is_null_value,
}


def _schema_type_candidates(expected_type: Any) -> list[Any]:
    return expected_type if isinstance(expected_type, list) else [expected_type]


def _schema_value_matches(expected_type: Any, value: Any) -> bool:
    for candidate in _schema_type_candidates(expected_type):
        checker = SCHEMA_TYPE_CHECKS.get(candidate)
        if checker is not None and checker(value):
            return True
    return False


def _expected_confidence_id(
    confidence_policy: dict[str, Any],
    artifact_class: str,
) -> str | None:
    defaults = confidence_policy.get("defaults", {})
    if not isinstance(defaults, dict):
        return None
    value = defaults.get(artifact_class)
    return value if isinstance(value, str) else None


def _promotion_placeholders(promotion_policy: dict[str, Any]) -> list[str]:
    markers = promotion_policy.get("global", {}).get("placeholder_markers", [])
    return [str(marker).lower() for marker in markers if isinstance(marker, str)]


def _contains_placeholder(text: str, promotion_policy: dict[str, Any]) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered for marker in _promotion_placeholders(promotion_policy)
    )


def _validate_note_placement(
    memory_root: Path,
    path: Path,
    artifact_class: str,
    placement_rules: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    rule = _rule_map(placement_rules).get(artifact_class)
    if not rule:
        return
    expected_dir = str(rule.get("target_dir") or "")
    expected_rel = _normalize_target_dir(expected_dir)
    try:
        relative_path = path.relative_to(memory_root)
    except ValueError:
        issues.append(
            ValidationIssue(path=str(path), message="note path is outside memory root")
        )
        return
    relative_text = relative_path.as_posix()
    if expected_rel and not relative_text.startswith(expected_rel):
        issues.append(
            ValidationIssue(
                path=str(path),
                message=(
                    f"note is misplaced for {artifact_class}; expected under "
                    f"{expected_rel}"
                ),
            )
        )


def _validate_note_required_fields(
    path: Path,
    metadata: dict[str, Any],
    schema: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    for field_name in schema.get("required", []):
        if field_name not in metadata:
            issues.append(
                ValidationIssue(
                    path=str(path), message=f"note missing required field: {field_name}"
                )
            )


def _validate_note_field_types(
    path: Path,
    metadata: dict[str, Any],
    schema: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return
    for field_name, field_schema in properties.items():
        if field_name not in metadata or not isinstance(field_schema, dict):
            continue
        expected_type = field_schema.get("type")
        if expected_type is not None and not _schema_value_matches(
            expected_type, metadata[field_name]
        ):
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message=f"note field has invalid type for {field_name}",
                )
            )
        if field_name == "ttl_days" and isinstance(metadata[field_name], int):
            minimum = field_schema.get("minimum")
            if isinstance(minimum, int) and metadata[field_name] < minimum:
                issues.append(
                    ValidationIssue(
                        path=str(path),
                        message=f"note field ttl_days must be >= {minimum}",
                    )
                )


def _validate_note_source_refs(
    path: Path,
    metadata: dict[str, Any],
    issues: list[ValidationIssue],
) -> list[Any]:
    source_refs = metadata.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        issues.append(
            ValidationIssue(
                path=str(path), message="note source_refs must be a non-empty list"
            )
        )
        return []
    return source_refs


def _validate_note_confidence(
    path: Path,
    artifact_class: str,
    metadata: dict[str, Any],
    confidence_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    expected_confidence = _expected_confidence_id(confidence_policy, artifact_class)
    actual_confidence = metadata.get("confidence")
    if expected_confidence and actual_confidence != expected_confidence:
        issues.append(
            ValidationIssue(
                path=str(path),
                message=(
                    f"note confidence must be {expected_confidence!r} for "
                    f"{artifact_class}"
                ),
            )
        )


def _retention_entry(
    retention_policy: dict[str, Any],
    artifact_class: str,
) -> dict[str, Any] | None:
    artifact_classes = retention_policy.get("artifact_classes", {})
    if not isinstance(artifact_classes, dict):
        return None
    entry = artifact_classes.get(artifact_class)
    return entry if isinstance(entry, dict) else None


def _validate_episodic_note_ttl(
    path: Path,
    metadata: dict[str, Any],
    policy_entry: dict[str, Any] | None,
    issues: list[ValidationIssue],
) -> None:
    ttl_days = metadata.get("ttl_days")
    policy_ttl = policy_entry.get("ttl_days") if policy_entry else None
    if (
        isinstance(policy_ttl, int)
        and isinstance(ttl_days, int)
        and ttl_days > policy_ttl
    ):
        issues.append(
            ValidationIssue(
                path=str(path),
                message=f"episodic ttl_days exceeds policy maximum of {policy_ttl}",
            )
        )


def _validate_curated_note_kind(
    path: Path,
    metadata: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    kind = metadata.get("kind")
    parent_dir = path.parent.name
    expected_kind = CURATED_KIND_BY_DIR.get(parent_dir)
    if expected_kind and kind != expected_kind:
        issues.append(
            ValidationIssue(
                path=str(path),
                message=(
                    f"curated note kind must be {expected_kind!r} inside {parent_dir}/"
                ),
            )
        )


def _summary_min_words(promotion_policy: dict[str, Any]) -> int:
    min_words = promotion_policy.get("global", {}).get("summary_min_words", 0)
    return min_words if isinstance(min_words, int) else 0


def _validate_curated_note_summary(
    path: Path,
    metadata: dict[str, Any],
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    summary = metadata.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        issues.append(
            ValidationIssue(
                path=str(path), message="curated note summary must be non-empty"
            )
        )
        return
    min_words = _summary_min_words(promotion_policy)
    if len(summary.split()) < min_words:
        issues.append(
            ValidationIssue(
                path=str(path),
                message=f"curated note summary must contain at least {min_words} words",
            )
        )
    if _contains_placeholder(summary, promotion_policy):
        issues.append(
            ValidationIssue(
                path=str(path),
                message="curated note summary contains placeholder text",
            )
        )


def _validate_curated_source_refs(
    path: Path,
    source_refs: list[Any],
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    has_placeholder = any(
        _contains_placeholder(str(ref), promotion_policy)
        for ref in source_refs
        if isinstance(ref, str)
    )
    if has_placeholder:
        issues.append(
            ValidationIssue(
                path=str(path),
                message="curated note source_refs contain placeholder text",
            )
        )


def _validate_curated_governance(
    path: Path,
    metadata: dict[str, Any],
    source_refs: list[Any],
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    _validate_curated_note_kind(path, metadata, issues)
    _validate_curated_note_summary(path, metadata, promotion_policy, issues)
    _validate_curated_source_refs(path, source_refs, promotion_policy, issues)


def _validate_note_governance(
    path: Path,
    artifact_class: str,
    metadata: dict[str, Any],
    retention_policy: dict[str, Any],
    confidence_policy: dict[str, Any],
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    source_refs = _validate_note_source_refs(path, metadata, issues)
    _validate_note_confidence(path, artifact_class, metadata, confidence_policy, issues)
    policy_entry = _retention_entry(retention_policy, artifact_class)
    if artifact_class == "episodic_note":
        _validate_episodic_note_ttl(path, metadata, policy_entry, issues)
    if artifact_class == "curated_note":
        _validate_curated_governance(
            path, metadata, source_refs, promotion_policy, issues
        )


def _validate_curated_note_body(
    path: Path,
    metadata: dict[str, Any],
    body: str,
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    kind = metadata.get("kind")
    if not isinstance(kind, str):
        return
    required_headings = (
        promotion_policy.get("kinds", {}).get(kind, {}).get("required_headings", [])
    )
    headings = set(extract_markdown_headings(body))
    for heading in required_headings:
        if isinstance(heading, str) and heading not in headings:
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message=f"curated note missing required heading: {heading}",
                )
            )
    if _contains_placeholder(body, promotion_policy):
        issues.append(
            ValidationIssue(
                path=str(path), message="curated note body contains placeholder text"
            )
        )


def _validate_curated_duplicates(
    curated_notes: list[tuple[Path, dict[str, Any]]],
    issues: list[ValidationIssue],
) -> None:
    by_id: dict[str, Path] = {}
    by_title: dict[str, Path] = {}
    for path, metadata in curated_notes:
        note_id = metadata.get("id")
        if isinstance(note_id, str):
            if note_id in by_id:
                issues.append(
                    ValidationIssue(
                        path=str(path),
                        message=f"duplicate curated note id also used by {by_id[note_id].as_posix()}",
                    )
                )
            else:
                by_id[note_id] = path
        title = metadata.get("title")
        if isinstance(title, str):
            normalized_title = normalize_text_key(title)
            if normalized_title in by_title:
                issues.append(
                    ValidationIssue(
                        path=str(path),
                        message=(
                            "duplicate curated note title also used by "
                            f"{by_title[normalized_title].as_posix()}"
                        ),
                    )
                )
            else:
                by_title[normalized_title] = path


def _validate_note_files(
    memory_root: Path,
    schema_payloads: dict[str, Any],
    policy_payloads: dict[str, Any],
    catalog_payloads: dict[str, Any],
    issues: list[ValidationIssue],
    *,
    include_all_episodic_notes: bool,
) -> None:
    placement_rules = catalog_payloads.get("placement_rules.yaml", {})
    retention_policy = policy_payloads.get("retention.yaml", {})
    confidence_policy = policy_payloads.get("confidence.yaml", {})
    promotion_policy = policy_payloads.get("promotion.yaml", {})
    curated_schema = schema_payloads.get("curated_note.schema.json", {})
    episodic_schema = schema_payloads.get("episodic_note.schema.json", {})
    schema_map = {
        "curated_note": curated_schema if isinstance(curated_schema, dict) else {},
        "episodic_note": episodic_schema if isinstance(episodic_schema, dict) else {},
    }
    curated_notes: list[tuple[Path, dict[str, Any]]] = []

    for artifact_class, path in _iter_note_paths(
        memory_root,
        include_all_episodic_notes=include_all_episodic_notes,
    ):
        try:
            if artifact_class == "curated_note":
                note = parse_markdown_note(
                    path,
                    include_body=True,
                    read_timeout_seconds=VALIDATION_NOTE_READ_TIMEOUT_SECONDS,
                )
            else:
                note = parse_markdown_note_metadata(
                    path,
                    read_timeout_seconds=VALIDATION_NOTE_READ_TIMEOUT_SECONDS,
                )
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    path=str(path), message=f"failed to parse markdown note: {exc}"
                )
            )
            continue

        schema = schema_map[artifact_class]
        _validate_note_placement(
            memory_root, path, artifact_class, placement_rules, issues
        )
        _validate_note_required_fields(path, note.metadata, schema, issues)
        _validate_note_field_types(path, note.metadata, schema, issues)
        _validate_note_governance(
            path,
            artifact_class,
            note.metadata,
            retention_policy,
            confidence_policy,
            promotion_policy if isinstance(promotion_policy, dict) else {},
            issues,
        )
        if artifact_class == "curated_note":
            curated_notes.append((path, note.metadata))
            _validate_curated_note_body(
                path,
                note.metadata,
                note.body,
                promotion_policy if isinstance(promotion_policy, dict) else {},
                issues,
            )

    _validate_curated_duplicates(curated_notes, issues)


def validate_memory_scaffold(
    root: Path | None = None,
    *,
    include_working_tree_junk: bool = False,
    include_all_episodic_notes: bool = False,
) -> list[ValidationIssue]:
    """Validate the baseline project-memory scaffold and note contracts."""
    memory_root = _memory_root(root)
    issues: list[ValidationIssue] = []

    policy_paths = _required_policy_paths(memory_root)
    catalog_paths = _required_catalog_paths(memory_root)
    schema_paths = _required_schema_paths(memory_root)

    for path in (*policy_paths, *catalog_paths, *schema_paths):
        _validate_exists(path, issues)

    if issues:
        return issues

    policy_payloads = {path.name: load_yaml_resource(path) for path in policy_paths}
    catalog_payloads = {path.name: load_yaml_resource(path) for path in catalog_paths}
    schema_payloads = {path.name: load_json_resource(path) for path in schema_paths}

    for name, payload in {**policy_payloads, **catalog_payloads}.items():
        if not isinstance(payload, dict):
            issues.append(
                ValidationIssue(path=name, message="YAML root must be a mapping")
            )

    for name, payload in schema_payloads.items():
        _validate_schema_shape(Path("schemas") / name, payload, issues)

    source_priority = policy_payloads.get("source_priority.yaml")
    storage_policy = policy_payloads.get("storage.yaml")
    retention_policy = policy_payloads.get("retention.yaml")
    source_registry = catalog_payloads.get("source_registry.yaml")
    if isinstance(source_priority, dict) and isinstance(source_registry, dict):
        _validate_source_priority(source_priority, source_registry, issues)
    if isinstance(storage_policy, dict) and isinstance(retention_policy, dict):
        _validate_storage_policy(storage_policy, retention_policy, issues)
    _validate_tracked_generated_artifacts(memory_root, issues)
    if include_working_tree_junk:
        _validate_working_tree_junk(memory_root, issues)

    if not issues:
        _validate_note_files(
            memory_root,
            schema_payloads,
            policy_payloads,
            catalog_payloads,
            issues,
            include_all_episodic_notes=include_all_episodic_notes,
        )

    return issues
