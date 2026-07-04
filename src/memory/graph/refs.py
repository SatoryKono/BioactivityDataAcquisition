"""Deterministic graph reference helpers shared by memory surfaces."""

from __future__ import annotations

from pathlib import Path

TEST_SURFACE_NAMES: dict[str, str] = {
    "unit": "unit tests",
    "integration": "integration tests",
    "e2e": "e2e tests",
    "architecture": "architecture tests",
    "contract": "contract tests",
    "benchmarks": "benchmarks",
}

COMPOSITE_CONFIG_PREFIX = "configs/composites/"
ENTITY_CONFIG_PREFIX = "configs/entities/"
RUN_MANIFEST_ARTIFACT_REF = "run_manifest::json"
RUN_LEDGER_ARTIFACT_REF = "run_ledger::jsonl"


def node_ref(label: str, name: str) -> str:
    """Return a deterministic string reference for a graph node key."""
    return f"{label}:{name}"


def related_ref(kind: str, name: str) -> str:
    """Return a deterministic cross-layer related reference."""
    return f"{kind}::{name}"


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def module_dotted_name(relative_path: str) -> str:
    """Mirror graph dotted-path derivation for Python modules."""
    without_suffix = relative_path.removesuffix(".py")
    return without_suffix.replace("/", ".")


def test_suite_name(relative_path: str) -> str | None:
    """Return the deterministic test surface name for a test artifact path."""
    parts = Path(relative_path).parts
    if len(parts) < 2:
        return None
    return TEST_SURFACE_NAMES.get(parts[1])


def pipeline_family_from_name(name: str) -> tuple[str | None, str | None]:
    """Infer provider and entity segments from a pipeline-like name."""
    if "_" not in name:
        return None, None
    provider, entity = name.split("_", 1)
    if not provider or not entity:
        return None, None
    return provider, entity


def _pipeline_like_name_from_path(source_path: str) -> str | None:
    path = Path(source_path)
    parts = path.parts
    stem = path.stem

    if source_path.startswith(ENTITY_CONFIG_PREFIX) and len(parts) >= 4:
        provider = parts[2]
        entity = path.stem
        return f"{provider}_{entity}"
    if source_path.startswith(COMPOSITE_CONFIG_PREFIX) and stem != "__init__":
        return stem
    if (
        source_path.startswith("src/bioetl/application/pipelines/")
        and stem != "__init__"
    ):
        return stem
    if source_path.startswith("tests/") and stem.startswith("test_"):
        candidate = stem.removeprefix("test_")
        return candidate or None
    return None


def _provider_from_path(source_path: str) -> str | None:
    path = Path(source_path)
    parts = path.parts
    if source_path.startswith(ENTITY_CONFIG_PREFIX) and len(parts) >= 4:
        return parts[2]
    if (
        source_path.startswith("src/bioetl/infrastructure/adapters/")
        and len(parts) >= 5
    ):
        return parts[4]
    pipeline_like = _pipeline_like_name_from_path(source_path)
    if pipeline_like is not None:
        provider, _ = pipeline_family_from_name(pipeline_like)
        return provider
    return None


def _config_graph_refs(source_path: str) -> list[str]:
    refs = [node_ref("config_artifact", source_path)]
    path = Path(source_path)
    parts = path.parts
    if source_path.startswith(ENTITY_CONFIG_PREFIX) and len(parts) >= 4:
        provider = parts[2]
        entity = path.stem
        pipeline_name = f"{provider}_{entity}"
        refs.extend(
            [
                node_ref("provider_surface", provider),
                node_ref("entity_config", pipeline_name),
                node_ref("pipeline_surface", pipeline_name),
            ]
        )
    elif source_path.startswith(COMPOSITE_CONFIG_PREFIX) and path.stem != "__init__":
        refs.extend(
            [
                node_ref("composite_config", path.stem),
                node_ref("pipeline_surface", path.stem),
            ]
        )
    return refs


def related_refs_for_source(
    source_path: str,
    source_type: str,
    *,
    symbol_kind: str | None = None,
    symbol_name: str | None = None,
) -> list[str]:
    """Derive stable cross-layer refs from one source path."""
    refs: list[str] = [related_ref("file", source_path)]
    path = Path(source_path)
    refs.extend(
        _related_refs_by_source_type(
            source_path,
            source_type,
            symbol_kind=symbol_kind,
            symbol_name=symbol_name,
            path=path,
        )
    )
    refs.extend(_related_refs_for_provider_and_pipeline(source_path))
    return _dedupe(refs)


def _related_refs_by_source_type(
    source_path: str,
    source_type: str,
    *,
    symbol_kind: str | None,
    symbol_name: str | None,
    path: Path,
) -> list[str]:
    if source_type == "adr":
        return [related_ref("adr", path.stem)]
    if source_type == "runbook":
        return _related_runbook_refs(source_path, path)
    if source_type == "doc":
        return [related_ref("doc", source_path)]
    if source_type == "devin_wiki":
        return [related_ref("devin-wiki", source_path)]
    if source_type in {"memory", "plan", "workflow", "dashboard", "script"}:
        return [related_ref(source_type, source_path)]
    if source_type == "code":
        return _related_code_refs(source_path, symbol_kind, symbol_name)
    if source_type == "test":
        return _related_test_refs(source_path)
    if source_type == "config":
        return _related_config_refs(source_path, path)
    return []


def _related_runbook_refs(source_path: str, path: Path) -> list[str]:
    refs = [related_ref("runbook", source_path)]
    if any(token in path.stem for token in ("incident", "failure")):
        refs.append(related_ref("incident", path.stem))
    return refs


def _related_code_refs(
    source_path: str,
    symbol_kind: str | None,
    symbol_name: str | None,
) -> list[str]:
    dotted_path = module_dotted_name(source_path)
    refs = [related_ref("module", dotted_path)]
    if symbol_name and symbol_kind == "class":
        refs.append(related_ref("class", f"{dotted_path}.{symbol_name}"))
    elif symbol_name and symbol_kind in {"function", "async_function"}:
        refs.append(related_ref("function", f"{dotted_path}.{symbol_name}"))
    return refs


def _related_test_refs(source_path: str) -> list[str]:
    refs = [related_ref("test-artifact", source_path)]
    suite_name = test_suite_name(source_path)
    if suite_name is not None:
        refs.append(related_ref("test-suite", suite_name))
    return refs


def _related_config_refs(source_path: str, path: Path) -> list[str]:
    refs = [related_ref("config", source_path)]
    if source_path.startswith(ENTITY_CONFIG_PREFIX) and len(path.parts) >= 4:
        provider = path.parts[2]
        entity = path.stem
        refs.append(related_ref("entity", f"{provider}.{entity}"))
    elif source_path.startswith(COMPOSITE_CONFIG_PREFIX) and path.stem != "__init__":
        refs.append(related_ref("composite", path.stem))
    return refs


def _related_refs_for_provider_and_pipeline(source_path: str) -> list[str]:
    refs: list[str] = []
    provider = _provider_from_path(source_path)
    if provider is not None:
        refs.append(related_ref("provider", provider))

    pipeline_name = _pipeline_like_name_from_path(source_path)
    if pipeline_name is not None:
        refs.append(related_ref("pipeline", pipeline_name))
        provider_name, entity_name = pipeline_family_from_name(pipeline_name)
        if provider_name is not None and entity_name is not None:
            refs.append(related_ref("entity", f"{provider_name}.{entity_name}"))
    return refs


def graph_refs_for_source(
    source_path: str,
    source_type: str,
    *,
    symbol_kind: str | None = None,
    symbol_name: str | None = None,
) -> list[str]:
    """Derive deterministic graph node refs from a repository source path."""
    refs: list[str] = [node_ref("file_surface", source_path)]
    refs.extend(
        _graph_refs_by_source_type(
            source_path,
            source_type,
            symbol_kind=symbol_kind,
            symbol_name=symbol_name,
        )
    )
    return _dedupe(refs)


def _graph_refs_by_source_type(
    source_path: str,
    source_type: str,
    *,
    symbol_kind: str | None,
    symbol_name: str | None,
) -> list[str]:
    if source_type in {
        "doc",
        "adr",
        "runbook",
        "memory",
        "plan",
        "dashboard",
        "devin_wiki",
    }:
        return [node_ref("doc_artifact", source_path)]
    if source_type in {"workflow", "script"}:
        return [node_ref("operational_artifact", source_path)]
    if source_type == "code":
        return _graph_code_refs(source_path, symbol_kind, symbol_name)
    if source_type == "test":
        return _graph_test_refs(source_path)
    if source_type == "config":
        return _config_graph_refs(source_path)
    return []


def _graph_code_refs(
    source_path: str,
    symbol_kind: str | None,
    symbol_name: str | None,
) -> list[str]:
    refs = [node_ref("module_surface", source_path)]
    provider = _provider_from_path(source_path)
    if provider is not None:
        refs.append(node_ref("provider_surface", provider))
    pipeline_name = _pipeline_like_name_from_path(source_path)
    if pipeline_name is not None:
        refs.append(node_ref("pipeline_surface", pipeline_name))
    refs.extend(_graph_symbol_refs(source_path, symbol_kind, symbol_name))
    return refs


def _graph_symbol_refs(
    source_path: str,
    symbol_kind: str | None,
    symbol_name: str | None,
) -> list[str]:
    if not symbol_name:
        return []
    dotted_path = module_dotted_name(source_path)
    if symbol_kind == "class":
        return [node_ref("class_surface", f"{dotted_path}.{symbol_name}")]
    if symbol_kind in {"function", "async_function"}:
        return [node_ref("function_surface", f"{dotted_path}.{symbol_name}")]
    return []


def _graph_test_refs(source_path: str) -> list[str]:
    refs = [node_ref("test_artifact", source_path)]
    suite_name = test_suite_name(source_path)
    if suite_name is not None:
        refs.append(node_ref("test_surface", suite_name))
    pipeline_name = _pipeline_like_name_from_path(source_path)
    if pipeline_name is not None:
        refs.append(node_ref("pipeline_surface", pipeline_name))
    provider = _provider_from_path(source_path)
    if provider is not None:
        refs.append(node_ref("provider_surface", provider))
    return _dedupe(refs)


def graph_refs_for_workflow(source_path: str, workflow_name: str) -> list[str]:
    """Derive deterministic refs for a workflow definition source."""
    return [
        node_ref("file_surface", source_path),
        node_ref("workflow_surface", workflow_name),
    ]


def graph_refs_for_workflow_job(
    source_path: str, workflow_name: str, job_id: str
) -> list[str]:
    """Derive deterministic refs for a workflow job definition."""
    refs = graph_refs_for_workflow(source_path, workflow_name)
    refs.append(node_ref("workflow_job_surface", f"{workflow_name}::{job_id}"))
    return refs


def graph_refs_for_runtime_event(
    evidence_name: str,
    *,
    pipeline_name: str | None = None,
) -> list[str]:
    """Derive deterministic refs for run/control-plane timeline events."""
    refs = [node_ref("runtime_evidence_surface", evidence_name)]
    if evidence_name == "run_manifest":
        refs.append(
            node_ref("control_plane_artifact_surface", RUN_MANIFEST_ARTIFACT_REF)
        )
    elif evidence_name == "run_ledger":
        refs.append(node_ref("control_plane_artifact_surface", RUN_LEDGER_ARTIFACT_REF))
    if pipeline_name:
        refs.append(node_ref("pipeline_surface", pipeline_name))
    return refs


def related_refs_for_runtime_event(
    evidence_name: str,
    *,
    manifest_id: str | None = None,
    run_id: str | None = None,
    pipeline_name: str | None = None,
    provider: str | None = None,
    entity: str | None = None,
) -> list[str]:
    """Derive stable related refs for control-plane runtime events."""
    refs: list[str] = [related_ref("runtime-evidence", evidence_name)]
    if manifest_id:
        refs.append(related_ref("run-manifest", manifest_id))
        refs.append(related_ref("run-instance", manifest_id))
    if run_id:
        refs.append(related_ref("run-id", run_id))
    if pipeline_name:
        refs.append(related_ref("pipeline", pipeline_name))
        inferred_provider, inferred_entity = pipeline_family_from_name(pipeline_name)
        provider = provider or inferred_provider
        entity = entity or inferred_entity
    if provider:
        refs.append(related_ref("provider", provider))
    if provider and entity:
        refs.append(related_ref("entity", f"{provider}.{entity}"))
    return _dedupe(refs)


def related_refs_for_workflow(source_path: str, workflow_name: str) -> list[str]:
    """Derive stable related refs for a workflow source."""
    return _dedupe(
        [
            related_ref("file", source_path),
            related_ref("workflow", workflow_name),
            related_ref("workflow-path", source_path),
        ]
    )


def related_refs_for_workflow_job(
    source_path: str,
    workflow_name: str,
    job_id: str,
) -> list[str]:
    """Derive stable related refs for a workflow job definition."""
    refs = related_refs_for_workflow(source_path, workflow_name)
    refs.append(related_ref("workflow-job", f"{workflow_name}::{job_id}"))
    return _dedupe(refs)
