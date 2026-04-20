"""Validation helpers for the project-memory scaffold and note formats."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.notes import (
    extract_markdown_headings,
    normalize_text_key,
    parse_markdown_note,
)
from memory.resources import (
    CATALOG_DIR,
    MEMORY_ROOT,
    POLICY_DIR,
    SCHEMA_DIR,
    REQUIRED_CATALOG_FILES,
    REQUIRED_POLICY_FILES,
    REQUIRED_SCHEMA_FILES,
    load_json_resource,
    load_yaml_resource,
)


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
    valid_modes = storage_policy.get("storage_modes", [])
    if not isinstance(valid_modes, list) or not all(
        isinstance(mode, str) for mode in valid_modes
    ):
        issues.append(
            ValidationIssue(
                path="policy/storage.yaml",
                message="storage_modes must be a list of strings",
            )
        )
        return

    storage_classes = storage_policy.get("artifact_classes", {})
    retention_classes = retention_policy.get("artifact_classes", {})
    if not isinstance(storage_classes, dict):
        issues.append(
            ValidationIssue(
                path="policy/storage.yaml",
                message="artifact_classes must be a mapping",
            )
        )
        return
    if not isinstance(retention_classes, dict):
        issues.append(
            ValidationIssue(
                path="policy/retention.yaml",
                message="artifact_classes must be a mapping",
            )
        )
        return

    for artifact_class in retention_classes:
        if artifact_class not in storage_classes:
            issues.append(
                ValidationIssue(
                    path="policy/storage.yaml",
                    message=f"missing storage policy for artifact class: {artifact_class}",
                )
            )

    for artifact_class, entry in storage_classes.items():
        if not isinstance(entry, dict):
            issues.append(
                ValidationIssue(
                    path="policy/storage.yaml",
                    message=f"storage policy entry must be a mapping: {artifact_class}",
                )
            )
            continue
        storage_mode = entry.get("storage_mode")
        if storage_mode not in valid_modes:
            issues.append(
                ValidationIssue(
                    path="policy/storage.yaml",
                    message=f"invalid storage_mode for {artifact_class}: {storage_mode}",
                )
            )
        commit_to_git = entry.get("commit_to_git")
        if not isinstance(commit_to_git, bool):
            issues.append(
                ValidationIssue(
                    path="policy/storage.yaml",
                    message=f"commit_to_git must be boolean for {artifact_class}",
                )
            )
        default_paths = entry.get("default_paths")
        if not isinstance(default_paths, list) or not default_paths:
            issues.append(
                ValidationIssue(
                    path="policy/storage.yaml",
                    message=f"default_paths must be a non-empty list for {artifact_class}",
                )
            )
            continue
        for default_path in default_paths:
            if not isinstance(default_path, str):
                issues.append(
                    ValidationIssue(
                        path="policy/storage.yaml",
                        message=f"default_paths must contain strings for {artifact_class}",
                    )
                )
                continue
            if not default_path.startswith("src/memory/"):
                issues.append(
                    ValidationIssue(
                        path="policy/storage.yaml",
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


def _iter_note_paths(root: Path) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for artifact_class, directories in _note_dirs(root).items():
        for directory in directories:
            if not directory.exists():
                continue
            for path in sorted(directory.rglob("*.md")):
                if path.name == "README.md" or "templates" in path.parts:
                    continue
                result.append((artifact_class, path))
    return result


def _normalize_target_dir(target_dir: str) -> str:
    prefix = "src/memory/"
    if target_dir.startswith(prefix):
        return target_dir[len(prefix) :]
    return target_dir


def _rule_map(placement_rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rules = placement_rules.get("rules", [])
    if not isinstance(rules, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if isinstance(rule, dict) and isinstance(rule.get("artifact_class"), str):
            mapped[rule["artifact_class"]] = rule
    return mapped


def _schema_value_matches(expected_type: Any, value: Any) -> bool:
    candidates = expected_type if isinstance(expected_type, list) else [expected_type]
    for candidate in candidates:
        if candidate == "string" and isinstance(value, str):
            return True
        if (
            candidate == "integer"
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            return True
        if (
            candidate == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            return True
        if candidate == "boolean" and isinstance(value, bool):
            return True
        if candidate == "array" and isinstance(value, list):
            return True
        if candidate == "object" and isinstance(value, dict):
            return True
        if candidate == "null" and value is None:
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
        relative_path = path.resolve().relative_to(memory_root)
    except ValueError:
        issues.append(
            ValidationIssue(path=str(path), message="note path is outside memory root")
        )
        return
    if expected_rel and not str(relative_path).startswith(expected_rel):
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


def _validate_note_governance(
    path: Path,
    artifact_class: str,
    metadata: dict[str, Any],
    retention_policy: dict[str, Any],
    confidence_policy: dict[str, Any],
    promotion_policy: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    source_refs = metadata.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        issues.append(
            ValidationIssue(
                path=str(path), message="note source_refs must be a non-empty list"
            )
        )

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

    artifact_classes = retention_policy.get("artifact_classes", {})
    policy_entry = (
        artifact_classes.get(artifact_class)
        if isinstance(artifact_classes, dict)
        else None
    )
    if artifact_class == "episodic_note":
        ttl_days = metadata.get("ttl_days")
        if isinstance(policy_entry, dict) and isinstance(
            policy_entry.get("ttl_days"), int
        ):
            policy_ttl = policy_entry["ttl_days"]
            if isinstance(ttl_days, int) and ttl_days > policy_ttl:
                issues.append(
                    ValidationIssue(
                        path=str(path),
                        message=f"episodic ttl_days exceeds policy maximum of {policy_ttl}",
                    )
                )
    if artifact_class == "curated_note":
        kind = metadata.get("kind")
        parent_dir = path.parent.name
        expected_kind_by_dir = {
            "decisions": "decision",
            "incidents": "incident",
            "lessons": "lesson",
            "domain_knowledge": "domain_knowledge",
        }.get(parent_dir)
        if expected_kind_by_dir and kind != expected_kind_by_dir:
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message=(
                        f"curated note kind must be {expected_kind_by_dir!r} "
                        f"inside {parent_dir}/"
                    ),
                )
            )
        summary = metadata.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            issues.append(
                ValidationIssue(
                    path=str(path), message="curated note summary must be non-empty"
                )
            )
        else:
            min_words = promotion_policy.get("global", {}).get("summary_min_words", 0)
            if isinstance(min_words, int) and len(summary.split()) < min_words:
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
        if any(
            _contains_placeholder(str(ref), promotion_policy)
            for ref in source_refs
            if isinstance(ref, str)
        ):
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message="curated note source_refs contain placeholder text",
                )
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

    for artifact_class, path in _iter_note_paths(memory_root):
        try:
            note = parse_markdown_note(path)
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


def validate_memory_scaffold(root: Path | None = None) -> list[ValidationIssue]:
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

    if not issues:
        _validate_note_files(
            memory_root,
            schema_payloads,
            policy_payloads,
            catalog_payloads,
            issues,
        )

    return issues
