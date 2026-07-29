# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for publication controlled-vocabulary loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)


@pytest.mark.unit
def test_loader_builds_trimmed_registry_with_inheritance(tmp_path: Path) -> None:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir(parents=True)
    (vocab_dir / "publication_controlled.yaml").write_text(
        """
version: 1.0.0
providers:
  crossref:
    publication_type:
      preserve_unknown: true
      values:
        - "  Journal-Article  "
        - Dataset
  openalex:
    publication_type:
      preserve_unknown: true
      values:
        - " Article "
    type_crossref:
      preserve_unknown: true
      inherits: providers.crossref.publication_type
  pubmed:
    publication_status:
      preserve_unknown: false
      values:
        - ppublish
""".strip()
        + "\n",
        encoding="utf-8",
    )

    registry = PublicationControlledVocabularyLoader(tmp_path).load()

    assert registry.allowed_values("crossref", "publication_type") == frozenset(
        {"Journal-Article", "Dataset"}
    )
    assert registry.allowed_values("openalex", "publication_type") == frozenset(
        {"Article"}
    )
    assert registry.allowed_values("openalex", "type_crossref") == frozenset(
        {"Journal-Article", "Dataset"}
    )
    assert registry.allowed_values("pubmed", "publication_status") == frozenset()
