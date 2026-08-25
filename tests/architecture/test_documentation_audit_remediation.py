# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Ratchets for the 2026-04-29 strict documentation-audit remediation wave."""

from __future__ import annotations

import pytest

from pathlib import Path

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RULES_DOC = PROJECT_ROOT / "docs/00-project/RULES.md"
GLOSSARY_DOC = PROJECT_ROOT / "docs/00-project/glossary.md"
PIPELINE_GUIDE_DOC = PROJECT_ROOT / "docs/03-guides/pipeline-configuration.md"
CLI_DOC = PROJECT_ROOT / "docs/04-reference/cli.md"
ADR_044_DOC = (
    PROJECT_ROOT
    / "docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md"
)
MAP_DOC = PROJECT_ROOT / "docs/00-project/00-map.md"
MKDOCS_FILE = PROJECT_ROOT / "mkdocs.yml"
SOURCE_MAP_DOC = PROJECT_ROOT / "src/bioetl/README.md"


def test_operator_docs_use_current_readiness_endpoint() -> None:
    """Published operator docs must use `/health/ready`, not the stale `/ready`."""
    rules_text = RULES_DOC.read_text(encoding="utf-8")
    cli_text = CLI_DOC.read_text(encoding="utf-8")

    assert "/health/ready" in rules_text
    assert "GET /ready" not in rules_text
    assert "/health/ready" in cli_text


def test_cli_reference_covers_checkpoint_inspection_commands() -> None:
    """CLI reference must document the active checkpoint inspection surface."""
    text = CLI_DOC.read_text(encoding="utf-8")

    expected_fragments = (
        "bioetl checkpoint audit-run --run-id <UUID>",
        "bioetl checkpoint inspect --pipeline <NAME>",
        "`--run-id`",
        "`--pipeline`",
        "`--audit-limit`",
        "persistence_profile",
        "composite_resume_reconstructability",
    )
    missing = [fragment for fragment in expected_fragments if fragment not in text]
    assert not missing, f"CLI checkpoint inspection coverage drifted: {missing}"


def test_write_mode_docs_match_domain_enums() -> None:
    """Active docs must agree with domain write-mode enums."""
    silver_values = [member.name for member in SilverWriteMode]
    gold_values = [member.name for member in GoldWriteMode]

    rules_text = RULES_DOC.read_text(encoding="utf-8")
    glossary_text = GLOSSARY_DOC.read_text(encoding="utf-8")
    pipeline_text = PIPELINE_GUIDE_DOC.read_text(encoding="utf-8")

    for token in silver_values:
        assert token in rules_text
        assert token in glossary_text
    for token in gold_values:
        assert token in rules_text
        assert token in glossary_text

    assert "`MERGE`, `OVERWRITE`" not in glossary_text
    assert "`MERGE`, `OVERWRITE`, `SCD2`" not in glossary_text

    expected_pipeline_tokens = (
        "merge | append | delete",
        "append | overwrite | scd2",
        "| `delete`    | —             | Полная перезапись | —                 |",
        "| `scd2`      | —             | —                 | Историзация Type 2 |",
    )
    missing = [
        fragment
        for fragment in expected_pipeline_tokens
        if fragment not in pipeline_text
    ]
    assert not missing, f"Pipeline write-mode guide drifted: {missing}"


def test_adr_044_keeps_owner_doc_boundary_for_mutable_control_plane_facts() -> None:
    """ADR-044 must remain decision-focused and defer mutable facts elsewhere."""
    text = ADR_044_DOC.read_text(encoding="utf-8")

    required_fragments = (
        "the **contract doc** owns storage layout, rollout-flag matrix, event",
        "the **CLI reference** owns command and option inventory",
        "the **runbook** owns operator procedure and triage flow",
        "does **not** own a mutable file-path inventory",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    assert not missing, f"ADR-044 missing owner-doc boundary fragments: {missing}"

    forbidden_fragments = (
        "src/bioetl/application/services/run_manifest_service.py",
        "bioetl run-manifest show <run-id|manifest-id>",
        "bioetl run-manifest diff <left> <right>",
    )
    violations = [fragment for fragment in forbidden_fragments if fragment in text]
    assert not violations, (
        f"ADR-044 reintroduced mutable runtime inventory: {violations}"
    )


def test_project_map_promotes_active_entrypoints_into_published_nav() -> None:
    """Navigator quick links for active entrypoints must be visible in published nav."""
    map_text = MAP_DOC.read_text(encoding="utf-8")
    mkdocs_text = MKDOCS_FILE.read_text(encoding="utf-8")

    assert "docs-parity-gate.md" in map_text
    assert "adr-registry.md" in map_text
    assert "03-guides/docs-parity-gate.md" in mkdocs_text
    assert "02-architecture/adr-registry.md" in mkdocs_text
    assert "## Document Status" not in map_text


def test_rules_appendix_f_tracks_latest_adr_registry_policy() -> None:
    """RULES appendix must expose current ADR summary and delegate live registry."""
    text = RULES_DOC.read_text(encoding="utf-8")

    expected_fragments = (
        "canonical live ADR registry",
        "docs/02-architecture/decisions/README.md",
        "docs/02-architecture/adr-registry.md",
        "[ADR-046]",
        "[ADR-047]",
    )
    missing = [fragment for fragment in expected_fragments if fragment not in text]
    assert not missing, f"RULES ADR appendix drifted: {missing}"


def test_mkdocs_comment_uses_packaged_docs_guardrail_name() -> None:
    """Published MkDocs config should reference the active docs CLI guardrail."""
    text = MKDOCS_FILE.read_text(encoding="utf-8")

    assert "scripts/check_doc_links.py" not in text
    assert "python -m scripts.docs check-links" in text


def test_source_tree_readme_maps_entrypoints_and_ownership() -> None:
    """The source-tree README must expose useful entrypoints and ownership seams."""
    text = SOURCE_MAP_DOC.read_text(encoding="utf-8")

    expected_fragments = (
        "interfaces/cli/main.py",
        "composition/execution_api.py",
        "composition/control_plane_runtime.py",
        "application/services/control_plane/",
        "domain/medallion.py",
        "Canonical Ownership",
        "Reading Order",
    )
    missing = [fragment for fragment in expected_fragments if fragment not in text]
    assert not missing, f"src/bioetl/README.md is missing source-map anchors: {missing}"


def test_application_readme_documents_layered_port_registries() -> None:
    """Application navigation must name ports/ and ADR-058 (#9624)."""
    text = (PROJECT_ROOT / "src/bioetl/application/README.md").read_text(
        encoding="utf-8"
    )
    missing = [
        fragment
        for fragment in ("`ports/`", "ADR-058", "bioetl.application.ports")
        if fragment not in text
    ]
    assert not missing, (
        f"src/bioetl/application/README.md is missing ADR-058 port anchors: {missing}"
    )
