"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.default_batch_size import (
    MANIFEST_ID_TEMPLATE,
    RUN_ID_TEMPLATE,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    RUN_MANIFEST_LEDGER_DOC_PATH,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    CONTROL_PLANE_LEDGER_DOCS,
    EFFECTIVE_CONFIG_RUNTIME_MODULES,
    LINEAGE_RUNTIME_MODULES,
    RUN_LEDGER_RUNTIME_MODULES,
    RUN_MANIFEST_RUNTIME_MODULES,
)

__all__ = [
    "RUNTIME_EVIDENCE_DEFINITIONS",
    "_control_plane_runtime_evidence_specs",
    "_runtime_evidence_definition_spec",
    "_runtime_evidence_spec",
]

RUNTIME_EVIDENCE_DEFINITIONS = (
    (
        "run_manifest",
        "Control-plane runtime evidence for immutable run manifests.",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        CONTROL_PLANE_LEDGER_DOCS,
        RUN_MANIFEST_RUNTIME_MODULES,
        (
            (
                f"control/run_manifest/{MANIFEST_ID_TEMPLATE}.json",
                "json",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                f"control/run_manifest/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "run_ledger",
        "Control-plane runtime evidence for append-only run ledgers.",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        CONTROL_PLANE_LEDGER_DOCS,
        RUN_LEDGER_RUNTIME_MODULES,
        (
            (
                f"control/run_ledger/{MANIFEST_ID_TEMPLATE}.jsonl",
                "jsonl",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                f"control/run_ledger/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "effective_config_artifact",
        "Runtime evidence for effective configuration artifacts and hashes.",
        "docs/04-reference/components/config-runtime-artifacts.md",
        (
            "docs/04-reference/components/config-runtime-artifacts.md",
            RUN_MANIFEST_INSPECTION_DOC_PATH,
        ),
        EFFECTIVE_CONFIG_RUNTIME_MODULES,
        (
            ("control/effective_config/{artifact_id}.json", "json", "{artifact_id}"),
            (
                f"control/effective_config/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "lineage",
        "Runtime evidence for artifact lineage and inspection surfaces.",
        TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
        (
            TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
            RUN_MANIFEST_LEDGER_DOC_PATH,
        ),
        LINEAGE_RUNTIME_MODULES,
        (
            (
                "control/lineage/fragments/{fragment_hash}.json",
                "fragment",
                "{fragment_id}",
            ),
            (
                "control/lineage/_by_run_id/{run_id_hash}.jsonl",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
            (
                "control/lineage/_by_manifest_id/{manifest_id_hash}.jsonl",
                "manifest_index",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                "control/lineage/_by_node_id/{node_id_hash}.jsonl",
                "node_index",
                "{node_id}",
            ),
        ),
    ),
)


def _runtime_evidence_spec(
    *,
    name: str,
    summary: str,
    source_path: str,
    docs: tuple[str, ...],
    modules: tuple[str, ...],
    storage_refs: tuple[tuple[str, str, str], ...],
) -> dict[str, object]:
    return {
        "name": name,
        "summary": summary,
        "source_path": source_path,
        "docs": docs,
        "modules": modules,
        "storage_refs": storage_refs,
    }


def _runtime_evidence_definition_spec(
    definition: tuple[
        str,
        str,
        str,
        tuple[str, ...],
        tuple[str, ...],
        tuple[tuple[str, str, str], ...],
    ],
) -> dict[str, object]:
    name, summary, source_path, docs, modules, storage_refs = definition
    return _runtime_evidence_spec(
        name=name,
        summary=summary,
        source_path=source_path,
        docs=docs,
        modules=modules,
        storage_refs=storage_refs,
    )


def _control_plane_runtime_evidence_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        _runtime_evidence_definition_spec(definition)
        for definition in RUNTIME_EVIDENCE_DEFINITIONS
    )
