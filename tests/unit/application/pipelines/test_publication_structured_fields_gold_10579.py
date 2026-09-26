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
"""#10579: transformer → Gold structured-field acceptance for publications.

Proves required raw/canonical sidecar columns survive transform_for_gold and
pass provider Gold Pandera schemas for nested, empty, and null payloads.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pandas as pd
import pytest

from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.contracts.gold.publications_openalex import (
    OpenAlexPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_pubmed import (
    PubMedPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_semanticscholar import (
    SemanticScholarPublicationGoldSchema,
)
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")

S2_STRUCTURED_PAIRS: tuple[tuple[str, str], ...] = (
    ("subject_fields_raw_json", "subject_fields_canonical_json"),
    ("publication_types_raw_json", "publication_types_canonical_json"),
    ("citation_contexts_raw_json", "citation_contexts_canonical_json"),
    ("author_h_indices_raw_json", "author_h_indices_canonical_json"),
)


def _context() -> PipelineContext:
    return PipelineContext(
        run_id=UUID("10579000-1057-4057-8057-105790000001"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
        logger=MagicMock(),
    )


def _validate_gold(schema: type[Any], gold: dict[str, Any]) -> None:
    fields = schema.to_schema().columns
    row = {key: gold.get(key) for key in fields}
    frame = pd.DataFrame([row])
    for name, column in fields.items():
        dtype = str(getattr(column, "dtype", ""))
        if "float" in dtype:
            frame[name] = pd.to_numeric(frame[name], errors="coerce")
    schema.validate(frame)


def _assert_keys_present(record: dict[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in record]
    assert not missing, f"missing structured columns: {missing}"


@pytest.fixture
def s2_transformer() -> SemanticScholarPublicationTransformer:
    return instantiate_test_transformer(SemanticScholarPublicationTransformer)


@pytest.fixture
def openalex_transformer() -> OpenAlexPublicationTransformer:
    return instantiate_test_transformer(OpenAlexPublicationTransformer)


@pytest.fixture
def pubmed_transformer() -> PubMedPublicationTransformer:
    return instantiate_test_transformer(PubMedPublicationTransformer)


def _s2_payload(*, nested: bool) -> dict[str, Any]:
    authors = [
        {
            "authorId": "1741101",
            "name": "Jane Researcher",
            "hIndex": 42,
            "externalIds": {"ORCID": "0000-0001-2345-6789"},
        },
        {
            "authorId": "1741102",
            "name": "John Collaborator",
            "hIndex": None,
        },
    ]
    citations: list[dict[str, Any]] = [
        {
            "contexts": ["Nested context A.", "  Nested context B.  "],
            "intents": ["background"],
        }
    ]
    return {
        "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
        "externalIds": {
            "DOI": "10.1038/s41586-024-07487-w",
            "PubMed": "12345678",
            "CorpusId": 123456,
        },
        "title": "CRISPR-Cas9 gene editing in human embryos",
        "abstract": "This study demonstrates novel applications...",
        "year": 2024,
        "publicationDate": "2024-05-15",
        "venue": "Nature",
        "journal": {"name": "Nature", "volume": "629", "pages": "123-130"},
        "authors": authors if nested else [],
        "citationCount": 42,
        "referenceCount": 85,
        "influentialCitationCount": 7,
        "isOpenAccess": True,
        "openAccessPdf": {"url": "https://example.com/paper.pdf", "status": "GREEN"},
        "fieldsOfStudy": ["Biology", "Medicine"] if nested else None,
        "publicationTypes": ["JournalArticle"] if nested else [],
        "citations": citations if nested else None,
        "_lookup_method": "doi",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("nested", [True, False])
async def test_s2_structured_pairs_reach_gold_schema(
    s2_transformer: SemanticScholarPublicationTransformer,
    nested: bool,
) -> None:
    """S2 raw/canonical pairs remain present through Gold validation."""
    context = _context()
    silver = await s2_transformer.transform(context, _s2_payload(nested=nested), 0)
    assert silver is not None
    for raw_key, canonical_key in S2_STRUCTURED_PAIRS:
        _assert_keys_present(silver, (raw_key, canonical_key))

    gold = s2_transformer.transform_for_gold(context, silver)
    assert gold["corpus_id"] == "123456"
    for raw_key, canonical_key in S2_STRUCTURED_PAIRS:
        _assert_keys_present(gold, (raw_key, canonical_key))
        assert gold[raw_key] == silver[raw_key]
        assert gold[canonical_key] == silver[canonical_key]

    if nested:
        assert json.loads(gold["subject_fields_raw_json"]) == ["Biology", "Medicine"]
        assert json.loads(gold["publication_types_raw_json"]) == ["JournalArticle"]
        assert isinstance(json.loads(gold["citation_contexts_raw_json"]), list)
        assert json.loads(gold["author_h_indices_raw_json"]) == [42, None]
    else:
        assert gold["subject_fields_raw_json"] is None
        assert gold["publication_types_raw_json"] in (None, "[]")
        assert gold["citation_contexts_raw_json"] is None

    _validate_gold(SemanticScholarPublicationGoldSchema, gold)


@pytest.mark.asyncio
async def test_s2_structured_pairs_are_deterministic(
    s2_transformer: SemanticScholarPublicationTransformer,
) -> None:
    """Repeated transforms yield identical raw/canonical JSON sidecars."""
    context = _context()
    payload = _s2_payload(nested=True)
    first = await s2_transformer.transform(context, payload, 0)
    second = await s2_transformer.transform(context, payload, 0)
    assert first is not None and second is not None
    for raw_key, canonical_key in S2_STRUCTURED_PAIRS:
        assert first[raw_key] == second[raw_key]
        assert first[canonical_key] == second[canonical_key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary_topic",
    [
        {
            "id": "https://openalex.org/T12345",
            "display_name": "Topic A",
            "score": 0.95,
        },
        None,
        {},
    ],
)
async def test_openalex_primary_topic_sidecars_reach_gold(
    openalex_transformer: OpenAlexPublicationTransformer,
    primary_topic: dict[str, Any] | None,
) -> None:
    """OpenAlex primary_topic sidecars survive Gold projection for nested/null/empty."""
    context = _context()
    record = {
        "id": "https://openalex.org/W2148763428",
        "doi": "https://doi.org/10.1038/s41586-024-07487-w",
        "title": "Example Publication Title",
        "publication_year": 2024,
        "publication_date": "2024-05-15",
        "type": "article",
        "type_crossref": "journal-article",
        "cited_by_count": 42,
        "language": "en",
        "is_retracted": False,
        "primary_topic": primary_topic,
        "_lookup_method": "doi",
    }
    silver = await openalex_transformer.transform(context, record, 0)
    assert silver is not None
    _assert_keys_present(
        silver,
        ("primary_topic_raw_json", "primary_topic_canonical_json"),
    )
    gold = openalex_transformer.transform_for_gold(context, silver)
    _assert_keys_present(
        gold,
        ("primary_topic_raw_json", "primary_topic_canonical_json"),
    )
    if primary_topic:
        assert json.loads(gold["primary_topic_raw_json"]) == primary_topic
    else:
        assert gold["primary_topic_raw_json"] in (None, "null", "{}")
    _validate_gold(OpenAlexPublicationGoldSchema, gold)


@pytest.mark.asyncio
async def test_pubmed_affiliation_sidecars_reach_gold(
    pubmed_transformer: PubMedPublicationTransformer,
) -> None:
    """PubMed authors_with_affiliations sidecars remain present through Gold."""
    from tests.unit.application.pipelines.pubmed.test_pubmed_transformer import (
        FULL_PUBMED_XML,
    )

    context = _context()
    silver = await pubmed_transformer.transform(
        context, {"_raw_xml": FULL_PUBMED_XML}, 0
    )
    assert silver is not None
    keys = (
        "authors_with_affiliations_raw_json",
        "authors_with_affiliations_canonical_json",
        "affiliation_structured_raw_json",
        "affiliation_structured_canonical_json",
    )
    _assert_keys_present(silver, keys)
    gold = pubmed_transformer.transform_for_gold(context, silver)
    _assert_keys_present(gold, keys)
    assert gold["authors_with_affiliations_raw_json"] is not None
    assert gold["authors_with_affiliations_canonical_json"] is not None
    _validate_gold(PubMedPublicationGoldSchema, gold)


def test_hundred_percent_gold_schema_quarantine_keeps_terminal_invariants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """100% Gold schema quarantine keeps bronze partition intact.

    Gold-layer schema quarantine is durable (#10555/#10556) and must not be
    double-counted as silver ``records_quarantined``. Flat runner metrics for
    this case keep silver intact, gold=0, silver-quarantine=0; unresolved gold
    appears as output backlog, while intentional contract exclusions remain a
    separate terminal success path.
    """
    from types import SimpleNamespace

    from bioetl.application.core import runner_flow

    host = SimpleNamespace(
        _config=SimpleNamespace(
            pipeline_name="pubmed_publication",
            scd_config=object(),
            table=SimpleNamespace(gold_write_mode="append"),
            gold_schema=object(),
        ),
        _runtime=SimpleNamespace(run_type=SimpleNamespace(value="incremental")),
        _context=SimpleNamespace(
            started_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
            run_id="run-10579",
        ),
        _executor=SimpleNamespace(),
        _checkpoint_manager=SimpleNamespace(),
        _services=SimpleNamespace(metrics=MagicMock()),
        _logger=MagicMock(),
        _run_ledger_service=MagicMock(),
        execution_diagnostics={},
        execution_metrics={
            "records_fetched": 10,
            "records_bronze": 10,
            "records_silver": 10,
            "records_gold": 0,
            "records_gold_excluded_by_contract": 0,
            "records_quarantined": 0,
            "records_filtered_out": 0,
        },
    )
    monkeypatch.setattr(
        runner_flow,
        "current_utc_time",
        lambda: datetime(2026, 9, 22, 12, 0, 30, tzinfo=UTC),
    )
    runner_flow.record_run_finished(host)

    invariant_statuses = {
        call.args[2]["invariant"]: call.args[2]["status"]
        for call in host._services.metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    }
    assert invariant_statuses["fetched_equals_bronze"] == "passed"
    assert invariant_statuses["bronze_partitioned"] == "passed"
    assert invariant_statuses["silver_gold_monotonic"] == "passed"
    assert invariant_statuses["silver_gold_terminal_accounted"] == "passed"

    backlog = {
        call.args[2]["stage"]: call.args[1]
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_backlog_records"
    }
    assert backlog["validation"] == 0.0
    assert backlog["output"] == 10.0


def test_silver_quarantine_double_count_is_not_gold_schema_model() -> None:
    """Mixing gold failures into flat silver quarantine violates bronze partition."""
    from bioetl.application.core.runner_flow_metrics import (
        _record_count_flow_invariants,
    )
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )

    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "pubmed_publication")
    _record_count_flow_invariants(
        pipeline_metrics=recorder,
        run_type="incremental",
        fetched=10,
        bronze=10,
        silver=10,
        gold=0,
        gold_excluded_by_contract=0,
        quarantined=10,
        filtered_out=0,
    )
    statuses = {
        call.args[2]["invariant"]: call.args[2]["status"]
        for call in metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    }
    assert statuses["bronze_partitioned"] == "violated"
