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
"""Architecture contracts for publication type code generation artifacts."""

from __future__ import annotations

import pytest

import hashlib
from pathlib import Path

import yaml
from tests.helpers import run_repo_python

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.csv"
MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.meta.yaml"
)
GEN_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "schema"
    / "generation"
    / "generate_publication_type_classification_artifacts.py"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_publication_type_codegen_manifest_hashes() -> None:
    """Manifest hashes must match source CSV and JSON asset."""

    assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}

    assert payload.get("asset") == "publication_type_classification"

    source_info = payload.get("source", {})
    artifact_info = payload.get("artifact", {})

    assert (
        source_info.get("path") == "configs/enums/publication_type_classification.csv"
    )
    artifact_path = artifact_info.get("path")
    assert isinstance(artifact_path, str)
    assert artifact_path.startswith(
        "configs/enums/publication_type_classification.asset."
    )
    assert artifact_path.endswith(".json")

    assert source_info.get("sha256") == _sha256(CSV_PATH)
    assert artifact_info.get("sha256") == _sha256(PROJECT_ROOT / artifact_path)


def test_publication_type_codegen_is_deterministic() -> None:
    """`--check` mode must pass (no stale generated artifacts)."""
    result = run_repo_python(str(GEN_SCRIPT), "--check", cwd=PROJECT_ROOT)

    assert result.returncode == 0, (
        "Publication type generated artifacts are stale.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        "Run: python scripts/schema/generation/generate_publication_type_classification_artifacts.py"
    )


def test_publication_type_logic_module_is_compact() -> None:
    """Logic module should stay compact after giant-table extraction."""

    logic_module = (
        PROJECT_ROOT
        / "src"
        / "bioetl"
        / "domain"
        / "mapping"
        / "publication_type_classification.py"
    )
    loc = len(logic_module.read_text(encoding="utf-8").splitlines())
    assert loc < 250, f"Expected compact logic module (<250 LOC), got {loc}"
