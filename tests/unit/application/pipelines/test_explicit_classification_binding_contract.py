"""Publication and protein classification require explicit, caller-owned policies."""

from unittest.mock import Mock

import polars as pl
import pytest

from bioetl.application.pipelines.chembl.target_protein_classification_summary import summarize_target_protein_classification_dependency
from bioetl.application.pipelines.common.publication_transformer_context import BasePublicationTransformerContext, coerce_publication_transformer_init
from bioetl.application.pipelines.common.publication_transformer_hooks_mixin import PublicationTransformerHooksMixin
from bioetl.application.services.protein.classification_resolution import ProteinClassificationResolutionService

pytestmark = pytest.mark.unit


def test_supplied_publication_policy_replaces_only_its_owned_context_field():
    original_vocabulary, classification, replacement = object(), object(), object()
    original = BasePublicationTransformerContext("pubmed", publication_vocabulary=original_vocabulary, publication_classification=classification)
    updated = coerce_publication_transformer_init(original, publication_vocabulary=replacement)
    assert updated is not original
    assert updated.publication_vocabulary is replacement
    assert updated.publication_classification is classification
    assert updated.provider == "pubmed"
    assert original.publication_vocabulary is original_vocabulary
    assert coerce_publication_transformer_init(original) is original


def test_explicitly_cleared_classification_does_not_restore_previous_policy():
    original = BasePublicationTransformerContext("pubmed", publication_classification=object())
    assert coerce_publication_transformer_init(original, publication_classification=None).publication_classification is None
    assert original.publication_classification is not None


def test_publication_hook_without_classification_does_not_use_global_taxonomy():
    with pytest.raises(RuntimeError, match="passed explicitly"):
        PublicationTransformerHooksMixin()._classify_publication_type("pubmed", raw_type="Review")


def test_nonempty_target_summary_requires_its_mapping():
    with pytest.raises(RuntimeError, match="explicit mapping"):
        summarize_target_protein_classification_dependency(pl.DataFrame({"target_id": ["CHEMBL1"]}))


def test_invalid_record_policy_is_rejected_before_protein_lookup():
    port = Mock()
    with pytest.raises(ValueError, match="invalid_record_policy must be one of"):
        ProteinClassificationResolutionService(port, invalid_record_policy="unsupported")
    assert not port.mock_calls
