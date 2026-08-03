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
from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_makefile_uses_canonical_cli_entrypoints_for_live_ops_commands() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "bioetl.interfaces.cli.quarantine" not in makefile
    assert "bioetl.interfaces.cli.lock" not in makefile
    assert "$(RUN) bioetl quarantine inspect --pipeline $(PIPELINE)" in makefile
    assert "$(RUN) bioetl quarantine replay --pipeline $(PIPELINE)" in makefile
    assert "$(RUN) bioetl quarantine purge --pipeline $(PIPELINE)" in makefile
    assert (
        "$(RUN) bioetl lock release --pipeline $(PIPELINE) --run-id $(RUN_ID)"
        in makefile
    )


def test_docs_do_not_reference_stale_quarantine_or_lock_make_commands() -> None:
    docs = {
        "rules": PROJECT_ROOT / "docs" / "00-project" / "RULES.md",
        "rules_summary": PROJECT_ROOT / "docs" / "00-project" / "rules-summary.md",
        "cleanup_policy": PROJECT_ROOT / "docs" / "03-guides" / "cleanup-policy.md",
        "pipeline_review_checklist": PROJECT_ROOT
        / "docs"
        / "04-reference"
        / "templates"
        / "pipeline-review-checklist.md",
        "quarantine_state_diagram_source": PROJECT_ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "foundation"
        / "20-quarantine-record-states.mmd",
        "quarantine_state_diagram_svg": PROJECT_ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "foundation"
        / "svg"
        / "20-quarantine-record-states.svg",
    }

    forbidden_fragments = (
        "make quarantine purge",
        "make quarantine-inspect",
        "make quarantine-replay",
        "make quarantine-purge",
        "make release-lock PIPELINE=...",
        "make rollback VERSION=...",
    )

    for name, path in docs.items():
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, (
                f"{name} still contains stale command: {fragment}"
            )
