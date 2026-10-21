"""Governed input additions must fail closed until their contracts are complete."""

from __future__ import annotations

from enum import StrEnum
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.domain.behavior import _dq_rule_evaluators_vocab as vocab
from bioetl.domain.mapping import publication_type_classification as taxonomy
from bioetl.domain.normalization import _reference_id_registry as registry
from bioetl.domain.normalization import json as canonical
from bioetl.domain.workflow.config import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowReferenceCohort,
    WorkflowStepConfig,
)

pytestmark = pytest.mark.unit


def test_new_profile_without_a_codec_cannot_silently_use_default_bytes(monkeypatch):
    profiles = StrEnum(
        "FutureProfiles",
        {
            **{member.name: member.value for member in canonical.CanonicalJsonProfile},
            "FUTURE_V2": "future-v2",
        },
    )
    monkeypatch.setattr(canonical, "CanonicalJsonProfile", profiles)
    with pytest.raises(ValueError, match="Unsupported canonical JSON profile"):
        canonical.serialize_json_canonical({}, profile=profiles.FUTURE_V2)


def test_registry_rejects_an_unlabeled_family_before_building_normalizers(monkeypatch):
    monkeypatch.setattr(
        registry,
        "_REFERENCE_IDENTIFIER_FAMILY_SPECS",
        (("new-family", "string", "scalar", "", "Pending normalizer mapping."),),
    )
    with pytest.raises(ValueError, match="SPECS rows missing normalizer mapping keys"):
        registry.build_reference_identifier_families({})


@pytest.mark.parametrize(
    "field", ["publication_type_unified", "publication_subclass", "publication_class"]
)
def test_taxonomy_validation_uses_the_installed_classification_data(monkeypatch, field):
    data = object()
    values = frozenset({"Review"})
    resolve = Mock(return_value=values)
    monkeypatch.setattr(taxonomy, "classification_install", SimpleNamespace(data=data))
    monkeypatch.setattr(taxonomy, "publication_classification_values", resolve)
    assert (
        vocab._publication_taxonomy_vocabulary(f"validate_{field}_taxonomy") is values
    )
    resolve.assert_called_once_with(field, data)


@pytest.mark.parametrize(
    "kind, reason",
    [
        ("not-dependent", "direct upstream dependency"),
        ("transform", "pipeline producer"),
        ("wrong-table", "table must match its producer"),
    ],
)
def test_reference_cohort_requires_the_exact_upstream_pipeline(kind, reason):
    producer = (
        TransformStepConfig("producer", "derive")
        if kind == "transform"
        else WorkflowStepConfig("producer", "chembl_assay")
    )
    consumer = WorkflowStepConfig(
        "consumer",
        "chembl_activity",
        depends_on=() if kind == "not-dependent" else ("producer",),
        reference_cohort=WorkflowReferenceCohort(
            "producer",
            "chembl.target" if kind == "wrong-table" else "chembl.assay",
            "assay_id",
            "assay_id",
        ),
    )
    with pytest.raises(ValueError, match=reason):
        WorkflowConfig("cohort", (producer, consumer))


def test_reference_cohort_accepts_a_matching_direct_pipeline():
    producer = WorkflowStepConfig("producer", "chembl_assay")
    consumer = WorkflowStepConfig(
        "consumer",
        "chembl_activity",
        depends_on=("producer",),
        reference_cohort=WorkflowReferenceCohort(
            "producer", "chembl.assay", "assay_id", "assay_id"
        ),
    )
    assert (
        WorkflowConfig("cohort", (producer, consumer)).get_step("consumer") is consumer
    )
