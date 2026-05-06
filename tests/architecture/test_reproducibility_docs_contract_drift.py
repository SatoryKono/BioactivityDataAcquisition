"""Architecture tests for reproducibility docs/contract drift guardrails."""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from bioetl.domain.control_plane.run_manifest import (
    DOCUMENTED_SOURCE_REVISION_STATES,
    RunCodeProvenance,
    RunManifest,
)
from scripts.engineering.qa.generate_reproducibility_support_matrix import (
    build_reproducibility_support_matrix_markdown,
)

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _string_set_literal(node: ast.AST) -> set[str] | None:
    if not isinstance(node, ast.Set):
        return None
    values: set[str] = set()
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.add(element.value)
    return values


@pytest.mark.architecture
def test_chembl_molecule_schema_demotes_occurrence_provenance_from_row_contract() -> (
    None
):
    text = _read("docs/04-reference/schemas/domain/chembl/molecule-schema.md")

    assert "## System Fields (Persisted-Row Contract)" in text
    assert (
        "Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,"
        in text
    )
    assert "| `_run_id`" not in text
    assert '|  "_run_id":' not in text
    assert '|  "_run_type":' not in text
    assert '|  "_ingestion_ts":' not in text


@pytest.mark.architecture
def test_publication_provider_docs_mark_occurrence_provenance_as_sidecar_only() -> None:
    targets = (
        "docs/04-reference/providers/crossref/publication.md",
        "docs/04-reference/providers/openalex/publication.md",
        "docs/04-reference/providers/semanticscholar/publication.md",
    )

    for relative_path in targets:
        text = _read(relative_path)
        assert "persisted Silver/Gold row contract" in text, relative_path
        assert "sidecar/control-plane" in text, relative_path


@pytest.mark.architecture
def test_normalization_matrix_declares_non_contract_scope_and_drops_storage_wording() -> (
    None
):
    text = _read(
        "docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md"
    )

    assert (
        "This matrix is a normalization inventory, not a persisted-row publication contract."
        in text
    )
    assert (
        "System/meta field retained for storage but excluded from content_hash."
        not in text
    )
    assert (
        "Technical field is passed through unchanged when no explicit profile rule is defined."
        not in text
    )


@pytest.mark.architecture
def test_run_manifest_contract_documents_lifecycle_snapshot_and_scoring_surfaces() -> (
    None
):
    text = _read("docs/04-reference/contracts/run-manifest-ledger.md")

    assert "## Lifecycle Management" in text
    assert "Protected-reference rules are fail-closed" in text
    assert "FileControlPlaneArtifactLifecycleStore.plan(..., dry_run=True)" in text
    assert "### Input snapshot identity vs locator" in text
    assert "`snapshot_id` is content-addressed as `sha256:{content_hash}`" in text
    assert "`bronze://{relative_path_from_bronze_root}`" in text
    assert "Supported production and debug-critical launches inherit" in text
    assert "this effective default is `replay_ready`" in text
    assert "The effective default is fail-closed" in text
    assert "## Reproducibility Scoring Rubric" in text
    assert "|   100 | `forensic_grade`" in text
    assert "| Evidence surface" in text


@pytest.mark.architecture
def test_run_manifest_contract_doc_covers_runtime_manifest_schema() -> None:
    text = _read("docs/04-reference/contracts/run-manifest-ledger.md")

    missing_manifest_fields = [
        field.name for field in fields(RunManifest) if field.name not in text
    ]
    assert not missing_manifest_fields, (
        "Run manifest contract doc is missing manifest fields: "
        f"{missing_manifest_fields}"
    )

    missing_provenance_fields = [
        field.name for field in fields(RunCodeProvenance) if field.name not in text
    ]
    assert not missing_provenance_fields, (
        "Run manifest contract doc is missing code provenance fields: "
        f"{missing_provenance_fields}"
    )


@pytest.mark.architecture
def test_run_manifest_contract_doc_freezes_documented_source_revision_states() -> None:
    text = _read("docs/04-reference/contracts/run-manifest-ledger.md")

    for state in sorted(DOCUMENTED_SOURCE_REVISION_STATES):
        assert f"`{state}`" in text

    assert "run_id` is the canonical occurrence anchor" in text
    assert "manifest_id` is the immutable persisted manifest record key" in text
    assert (
        "execution_fingerprint` remains the canonical semantic execution identity"
        in text
    )


@pytest.mark.architecture
def test_run_manifest_docs_define_replay_equivalence_levels() -> None:
    """Replay docs must distinguish semantic equivalence from byte equality."""
    contract = _read("docs/04-reference/contracts/run-manifest-ledger.md")
    runbook = _read("docs/05-operations/runbooks/run-manifest-inspection.md")

    for text, doc_name in (
        (contract, "run-manifest-ledger.md"),
        (runbook, "run-manifest-inspection.md"),
    ):
        assert "semantic_execution_equivalence" in text, doc_name
        assert "artifact_byte_equivalence" in text, doc_name
        assert "occurrence-only" in text, doc_name
        assert "sidecar `output.content_hash`" in text, doc_name

    assert "not as a byte-identical artifact claim" in contract
    assert "semantically equivalent rather than byte-identical" in runbook


@pytest.mark.architecture
def test_reproducibility_support_matrix_matches_published_profiles() -> None:
    """Generated support docs must drift-check against domain profiles."""
    assert _read(
        "docs/02-architecture/policies/reproducibility-support-matrix.md"
    ) == build_reproducibility_support_matrix_markdown()


@pytest.mark.architecture
def test_content_hash_policy_classifies_ordered_and_set_like_fields() -> None:
    """Content-hash docs must state list-order identity policy explicitly."""
    policy = _read("docs/02-architecture/policies/content-hash-identity-policy.md")
    implementation = _read("src/bioetl/domain/transformations/hashing.py")

    assert "Ordered vs Set-Like Fields" in policy
    assert "ordered identity fields by default" in policy
    assert "`set_like_fields`" in policy
    assert "canonical JSON string fields" in policy
    assert "set_like_fields" in implementation


@pytest.mark.architecture
def test_run_manifest_config_hash_legacy_alias_contract_is_documented_and_wired() -> (
    None
):
    contract = _read("docs/04-reference/contracts/run-manifest-ledger.md")
    runbook = _read("docs/05-operations/runbooks/run-manifest-inspection.md")
    policy = _read("src/bioetl/domain/control_plane/reproducibility_policy.py")
    builder = _read("src/bioetl/composition/runtime_builders/run_manifest_builder.py")
    refs = _read("src/bioetl/composition/runtime_builders/_run_manifest_refs.py")

    assert (
        "`config_hash` is a legacy compatibility anchor retained for older manifest"
        in contract
    )
    assert "Current write paths populate it from" in contract
    assert "`resolved_config_hash`;" in contract
    assert "must not treat" in contract
    assert "`config_hash` as a synonym for `effective_config_hash`" in contract
    assert "`config_hash`" in runbook
    assert "legacy compatibility" in runbook
    assert "legacy_config_hash_from_resolved_config_hash" in policy
    assert "config_hash=legacy_config_hash_from_resolved_config_hash(" in builder
    assert "config_hash=legacy_config_hash_from_resolved_config_hash(" in refs


@pytest.mark.architecture
def test_strict_persistence_profile_set_is_centralized_in_domain_policy() -> None:
    """Prevent new local replay_ready/forensic_grade gates in launch paths."""
    allowed = {
        Path("src/bioetl/domain/control_plane/reproducibility_policy.py"),
    }
    strict_profiles = {"replay_ready", "forensic_grade"}
    violations: list[str] = []

    for path in sorted((ROOT / "src/bioetl").rglob("*.py")):
        relative_path = path.relative_to(ROOT)
        if relative_path in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if _string_set_literal(node) == strict_profiles:
                violations.append(f"{relative_path}:{node.lineno}")

    assert not violations, (
        "Strict persistence profile sets must use "
        "bioetl.domain.control_plane.reproducibility_policy."
        f"STRICT_PERSISTENCE_PROFILES, not local literals: {violations}"
    )


@pytest.mark.architecture
def test_reproducibility_rubric_declares_repeatable_7x5_scoring_matrix() -> None:
    text = _read("docs/04-reference/contracts/reproducibility-scoring-rubric.md")

    categories = (
        "### Determinism",
        "### Idempotency",
        "### Run Identity",
        "### Checkpoint Safety",
        "### Lineage Completeness",
        "### Replay Readiness",
        "### Layer Consistency",
    )
    for category in categories:
        assert category in text

    for prefix in ("DET", "IDE", "RID", "CPS", "LIN", "REP", "LAY"):
        for number in range(1, 6):
            assert f"| {prefix}-{number} |" in text

    assert "| 0 | Absent, unsafe, fail-open, or not evidenced |" in text
    assert "| 2 | Implemented, documented, and test-backed |" in text
    assert "Reviewers MUST cite evidence for every non-zero score" in text
    assert "## Evidence Matrix" in text
    assert "## Criterion Evidence Index" in text
    assert "docs/05-operations/control-plane-lifecycle.md" in text
