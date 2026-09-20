"""Stream B APP: leftover 1-2 line schema, metrics, extractor, and override branches."""

from __future__ import annotations

from types import SimpleNamespace
from xml.etree.ElementTree import Element

import pytest

from bioetl.application.composite.helpers.preflight_schema_field_extraction import (
    extract_fields_from_annotations,
)
from bioetl.application.core._record_normalization_contract import _NormalizationFinding
from bioetl.application.core._record_normalization_runtime_support import (
    profile_json_runtime_finding,
    project_normalization_findings,
)
from bioetl.application.core.base_transformer._structural_policy_contracts import (
    resolve_pandera_schema,
)
from bioetl.application.core.base_transformer._structural_policy_evaluation import (
    evaluate_null_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
)
from bioetl.application.core.batch_executor_loop_helpers import build_start_index
from bioetl.application.observability.control_plane_evidence.models import _scope_kind
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.observability.replay_write_risk import _add_legacy_sink_modes
from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    _int_or_none,
)
from bioetl.application.pipelines.common.publication_transformer_context import (
    BasePublicationTransformerContext,
    coerce_publication_transformer_init,
)
from bioetl.application.pipelines.crossref.author_extractors import (
    _extract_author_affiliations_list,
    _normalize_orcid,
)
from bioetl.application.pipelines.openalex._extractors_authors import (
    extract_institution_country_codes,
)
from bioetl.application.pipelines.pubmed.extractors.identifier import IdentifierExtractor
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _extract_cofactors_raw,
)
from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor
from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
    validate_lenient_pipeline_compatibility,
    validate_rule_bundle_compatibility,
)
from bioetl.application.services.control_plane.effective_config.runtime_overrides import (
    validate_runtime_environment_provenance,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

pytestmark = pytest.mark.unit


def test_schema_null_policy_and_start_index() -> None:
    assert resolve_pandera_schema(object()) is None
    contract = StructuralFieldSpec(
        field_name="flag",
        logical_type="boolean",
        physical_type="bool",
        nullable=False,
        optional=False,
        optional_sources=(),
        boolean_true_values=(),
        boolean_false_values=(),
    )
    assert (
        evaluate_null_value(contract=contract, working_record={}, events=[]) is None
    )
    assert build_start_index(records_fetched=10, batch=[{}]) == 9
    assert _scope_kind(resolved_via="manifest_id", manifest=object()) == "exact_run"


def test_findings_json_success_and_metrics_noop() -> None:
    assert project_normalization_findings(
        (),
        record={"id": 1},
        context=None,
        index=0,
        provider="chembl",
        entity_type="activity",
    ) == {"id": 1}
    rule = SimpleNamespace(notes="stores json", normalizer=SimpleNamespace(__name__="as_json"))
    assert (
        profile_json_runtime_finding(
            rule,  # type: ignore[arg-type]
            field_name="payload",
            raw_value="{}",
            normalized_value=None,
            finding_factory=_NormalizationFinding,
        )
        is None
    )
    recorder = PipelineMetricsRecorder(pipeline="chembl_activity")
    recorder.record_output_artifact_publication(stage="gold", status="ok", count=0)
    ctx = BasePublicationTransformerContext(provider="pubmed")
    assert coerce_publication_transformer_init(ctx) is ctx
    assert _int_or_none(2.0) == 2


def test_extractor_skip_and_empty_paths() -> None:
    assert _normalize_orcid("   ") is None
    assert _extract_author_affiliations_list({"affiliation": "lab"}) == []
    assert extract_institution_country_codes(
        [{"institutions": ["not-a-dict"]}]
    ) == []
    root = Element("PubmedArticle")
    article = Element("Article")
    eloc = Element("ELocationID")
    article.append(eloc)
    root.append(article)
    assert IdentifierExtractor.extract_elocation_ids(root) == {"doi": None, "pii": None}
    assert _extract_cofactors_raw({"COFACTOR": [{"cofactors": "nope"}]}) == []
    assert GeneExtractor._collect_named_values(
        [{"geneName": [{"value": "x"}, "skip"]}],
        "geneName",
    ) == ["x"]

    class _Parent:
        id: str

    class _Child(_Parent):
        id: int
        name: str

    fields = extract_fields_from_annotations(_Child, "seed")
    assert "id" in fields
    assert "name" in fields


def test_checkpoint_overrides_and_legacy_sinks() -> None:
    current = CheckpointMetadata(
        records_processed=1,
        dq_rule_bundle_version="rb-1",
        pipeline_version=None,
    )
    checkpoint = CheckpointMetadata(
        records_processed=1,
        dq_rule_bundle_version="rb-1",
        pipeline_version=None,
    )
    messages = validate_rule_bundle_compatibility(current, checkpoint)
    assert "compatible" in messages[0]
    ok, empty = validate_lenient_pipeline_compatibility(current, checkpoint)
    assert ok is True
    assert empty == []
    with pytest.raises(TypeError, match="must be a mapping"):
        validate_runtime_environment_provenance(
            runtime_overrides={"env": {"execution_environment": "prod"}},
            required_persistence_profile="replay_ready",
        )
    with pytest.raises(ValueError, match="must be non-empty"):
        validate_runtime_environment_provenance(
            runtime_overrides={"env": {"execution_environment": {}}},
            required_persistence_profile="replay_ready",
        )
    modes: set[tuple[str, str]] = set()
    _add_legacy_sink_modes({"silver_write_mode": "append", "gold_mode": "overwrite"}, modes)
    assert ("silver", "append") in modes
    assert ("gold", "overwrite") in modes
