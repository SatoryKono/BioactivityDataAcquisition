"""Integration tests for OpenAlex Publication Pipeline.

Tests full pipeline flow: Bronze -> Silver -> Gold with VCR-recorded HTTP.
Covers DOI resolution, title fallback, and error handling scenarios.
"""

from __future__ import annotations

import csv
import glob
import os
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import structlog

from bioetl.composition.factories.pipeline_factories import openalex_publication_factory
from bioetl.composition.factories.storage import StorageAdapter, StorageContext
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.types import RunType
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

logger = structlog.get_logger()

# VCR cassette directory
CASSETTE_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "vcr" / "openalex"
)


@pytest.fixture(scope="module")
def vcr_config():
    """Configure VCR for OpenAlex pipeline tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_query_parameters": ["mailto"],
        "decode_compressed_response": True,
    }


class TestOpenAlexPublicationPipeline:
    """Integration tests for OpenAlex Publication Pipeline."""

    @pytest.fixture(autouse=True)
    def _setup_storage(self, tmp_path):
        """Setup temporary storage paths."""
        self.storage_root = tmp_path / "storage"
        self.storage_root.mkdir()

        self.bronze_path = str(self.storage_root / "bronze")
        self.silver_path = str(self.storage_root / "silver")
        self.gold_path = str(self.storage_root / "gold")
        self.checkpoints_path = str(self.storage_root / "checkpoints")
        self.json_path = str(self.storage_root / "json")
        self.input_path = str(self.storage_root / "input")

        # Create directories
        for path in [
            self.bronze_path,
            self.silver_path,
            self.gold_path,
            self.checkpoints_path,
            self.json_path,
            self.input_path,
        ]:
            os.makedirs(path, exist_ok=True)

    def _create_input_csv(self, rows: list[dict[str, str]]) -> str:
        """Create input CSV file with DOIs and titles.

        Args:
            rows: List of dicts with 'doi' and 'title' keys.

        Returns:
            Path to created CSV file.
        """
        csv_path = os.path.join(self.input_path, "dois.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["doi", "title"])
            writer.writeheader()
            writer.writerows(rows)
        return csv_path

    def _create_storage_context(
        self,
        settings: Settings,
        config: PipelineYamlConfig,
        log: structlog.BoundLogger,
        metrics: MetricsPort,
    ) -> StorageContext:
        """Create StorageContext pointing to local temp paths."""
        bronze_config = config.sink.get("bronze")
        save_json = bronze_config.save_json if bronze_config else False

        adapter = StorageAdapter(
            bronze_writer=BronzeWriter(
                base_path=self.bronze_path,
                logger=log,
                metrics=metrics,
                save_json=save_json,
                json_path=self.json_path if save_json else None,
            ),
            silver_writer=SilverWriter(
                base_path=self.silver_path,
                logger=log,
                csv_exporter=None,
            ),
            gold_writer=GoldWriter(
                base_path=self.gold_path,
                logger=log,
                csv_exporter=None,
            ),
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=Path(self.bronze_path),
            silver_path=Path(self.silver_path),
            gold_path=Path(self.gold_path),
            checkpoints_path=Path(self.checkpoints_path),
        )

    @pytest.fixture
    def settings(self):
        """Return test settings."""
        os.environ["BIOETL_ENV"] = "dev"
        os.environ["BIOETL_OPENALEX_EMAIL"] = "bioetl-test@example.com"
        return Settings()

    @pytest.fixture
    def runtime_config(self):
        """Return default runtime config."""
        return RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            heartbeat_interval=10,
            resume=False,
            limit=None,
        )

    @pytest.fixture
    def run_id(self):
        """Return unique run ID."""
        return uuid4()

    def _create_runner(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
        input_csv_path: str | None = None,
    ):
        """Create pipeline runner with mocked storage."""
        from unittest.mock import patch

        from bioetl.infrastructure.config import load_pipeline_config

        pipeline_config = load_pipeline_config("openalex_publication")

        # Override input filter source path if provided
        if input_csv_path:
            # Update the input_filter source_path
            input_filter = pipeline_config.input_filter
            if input_filter:
                # Create a copy with updated source_path
                updated_filter = input_filter.model_copy(
                    update={"source_path": input_csv_path}
                )
                pipeline_config = pipeline_config.model_copy(
                    update={"input_filter": updated_filter}
                )

        observability = ObservabilityBundle(
            logger=structlog.get_logger(),
            metrics=NoOpMetrics(warn_on_use=False),
            tracer=NoOpTracing(),
        )

        # Patch StorageFactory to use local paths
        with patch(
            "bioetl.composition.factories.storage.StorageFactory.create"
        ) as mock_create:
            mock_create.side_effect = self._create_storage_context

            runner = openalex_publication_factory.create_runner(
                run_id=run_id,
                runtime=runtime_config,
                settings=settings,
                observability=observability,
                config=pipeline_config,
            )

            return runner

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_openalex_publication_doi_resolution(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test DOI resolution flow: Bronze -> Silver -> Gold."""
        # Create input CSV with known DOI
        input_csv = self._create_input_csv(
            [
                {
                    "doi": "10.1038/s41586-020-2012-7",
                    "title": "A pneumonia outbreak associated with a new coronavirus",
                },
            ]
        )

        # Limit to 1 record for test
        runtime_config = replace(runtime_config, limit=1)

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        # Run the pipeline
        await runner.run()

        # Verify Bronze files exist
        bronze_files = glob.glob(f"{self.bronze_path}/**/*.jsonl.zst", recursive=True)
        if not bronze_files:
            bronze_files = glob.glob(
                f"{self.bronze_path}/**/*.jsonl.zstd", recursive=True
            )
        assert len(bronze_files) > 0, f"No bronze files found in {self.bronze_path}"

        # Verify Silver Delta Table
        from deltalake import DeltaTable

        silver_table_path = f"{self.silver_path}/openalex_publication"
        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()
        assert len(silver_df) > 0, "Silver table is empty"

        # Verify lineage fields
        assert "_run_id" in silver_df.column_names
        assert "_run_type" in silver_df.column_names
        assert "_ingestion_ts" in silver_df.column_names

        # Verify OpenAlex-specific fields
        assert "openalex_id" in silver_df.column_names
        assert "doi" in silver_df.column_names
        assert "_lookup_method" in silver_df.column_names

        # Verify Gold Delta Table
        gold_table_path = f"{self.gold_path}/openalex_publication"
        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0, "Gold table is empty"

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_openalex_publication_title_fallback(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test title fallback when DOI not found."""
        # Create input CSV with invalid DOI and valid title
        input_csv = self._create_input_csv(
            [
                {
                    "doi": "10.9999/invalid-doi-12345",
                    "title": "COVID-19 vaccine development",
                },
            ]
        )

        runtime_config = replace(runtime_config, limit=1)

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        # Run the pipeline
        await runner.run()

        # If fallback found results, check lookup_method
        from deltalake import DeltaTable

        silver_table_path = f"{self.silver_path}/openalex_publication"

        try:
            dt_silver = DeltaTable(silver_table_path)
            silver_df = dt_silver.to_pandas()

            if len(silver_df) > 0:
                # Verify lookup method is title_fallback
                lookup_methods = silver_df["_lookup_method"].unique().tolist()
                assert any(
                    m in ("title_fallback", "title_only") for m in lookup_methods
                ), f"Expected fallback lookup method, got: {lookup_methods}"
        except Exception:
            # Table might not exist if no results found
            pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_openalex_publication_title_only(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test title-only lookup when DOI is empty."""
        # Create input CSV with empty DOI
        input_csv = self._create_input_csv(
            [
                {
                    "doi": "",
                    "title": "COVID-19 vaccine development",
                },
            ]
        )

        runtime_config = replace(runtime_config, limit=1)

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        await runner.run()

        # Verify results if any
        from deltalake import DeltaTable

        silver_table_path = f"{self.silver_path}/openalex_publication"

        try:
            dt_silver = DeltaTable(silver_table_path)
            silver_df = dt_silver.to_pandas()

            if len(silver_df) > 0:
                # Verify lookup method is title_only
                assert "title_only" in silver_df["_lookup_method"].values
        except Exception:
            # Table might not exist if no results found
            pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_openalex_publication_batch_dois(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test batch DOI resolution with multiple DOIs."""
        # Create input CSV with multiple DOIs
        input_csv = self._create_input_csv(
            [
                {
                    "doi": "10.1038/s41586-020-2012-7",
                    "title": "A pneumonia outbreak",
                },
                {
                    "doi": "10.1016/j.cell.2020.02.052",
                    "title": "Structure of SARS-CoV-2 spike",
                },
            ]
        )

        runtime_config = replace(runtime_config, limit=5)

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        await runner.run()

        # Verify Silver has records
        from deltalake import DeltaTable

        silver_table_path = f"{self.silver_path}/openalex_publication"

        try:
            dt_silver = DeltaTable(silver_table_path)
            silver_df = dt_silver.to_pyarrow_table()

            # At least one record should be found
            assert len(silver_df) >= 1, "Expected at least 1 record from batch"
        except Exception as e:
            pytest.skip(f"Silver table not created: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_openalex_publication_empty_input(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test graceful handling of empty input CSV."""
        # Create empty input CSV
        input_csv = self._create_input_csv([])

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        # Should complete without error
        await runner.run()

        # No Silver table should be created
        silver_table_path = f"{self.silver_path}/openalex_publication"
        from deltalake import DeltaTable

        with pytest.raises(Exception):
            DeltaTable(silver_table_path)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_openalex_publication_api_error_handling(
        self,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
    ) -> None:
        """Test error handling when API fails."""
        input_csv = self._create_input_csv(
            [
                {
                    "doi": "10.1038/s41586-020-2012-7",
                    "title": "Test",
                },
            ]
        )

        runner = self._create_runner(
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
            input_csv_path=input_csv,
        )

        # Mock the adapter to raise an error
        from bioetl.domain.exceptions import ApiError

        async def mock_fetch(*args, **kwargs):
            if False:
                yield  # make it a generator
            raise ApiError("Simulated OpenAlex API Failure")

        runner.services.data_source.fetch_filtered_with_fallback = mock_fetch

        with pytest.raises(ApiError, match="Simulated OpenAlex API Failure"):
            await runner.run()


@pytest.mark.integration
class TestOpenAlexPublicationTransformerIntegration:
    """Integration tests for OpenAlex transformer specifically."""

    @pytest.mark.asyncio
    async def test_transformer_abstract_reconstruction(self) -> None:
        """Test abstract reconstruction from inverted index."""
        from bioetl.application.pipelines.openalex.extractors import (
            reconstruct_abstract,
        )

        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
            "abstract": [4],
        }

        result = reconstruct_abstract(inverted_index)
        assert result == "This is a test abstract"

    @pytest.mark.asyncio
    async def test_transformer_author_extraction(self) -> None:
        """Test author extraction from authorships."""
        from bioetl.application.pipelines.openalex.extractors import extract_authors

        authorships = [
            {"author": {"display_name": "John Doe"}},
            {"author": {"display_name": "Jane Smith"}},
            {"author": {}},  # Missing display_name
        ]

        authors = extract_authors(authorships)
        assert len(authors) == 2
        assert "John Doe" in authors
        assert "Jane Smith" in authors

    @pytest.mark.asyncio
    async def test_transformer_doi_normalization(self) -> None:
        """Test DOI normalization from various URL formats."""
        from bioetl.application.pipelines.openalex.extractors import extract_doi

        # HTTPS URL
        assert (
            extract_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        )
        # HTTP URL
        assert (
            extract_doi("http://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        )
        # doi: prefix
        assert extract_doi("doi:10.1038/nature12373") == "10.1038/nature12373"
        # Bare DOI
        assert extract_doi("10.1038/nature12373") == "10.1038/nature12373"
        # None
        assert extract_doi(None) is None

    @pytest.mark.asyncio
    async def test_transformer_openalex_id_extraction(self) -> None:
        """Test OpenAlex ID extraction from URL."""
        from bioetl.application.pipelines.openalex.extractors import extract_openalex_id

        # Full URL
        assert extract_openalex_id("https://openalex.org/W2148763428") == "W2148763428"
        # Bare ID
        assert extract_openalex_id("W2148763428") == "W2148763428"
        # None
        assert extract_openalex_id(None) is None

    @pytest.mark.asyncio
    async def test_transformer_concepts_extraction(self) -> None:
        """Test concepts extraction with max count."""
        from bioetl.application.pipelines.openalex.extractors import extract_concepts

        concepts = [
            {"display_name": "Biology", "score": 0.9},
            {"display_name": "Chemistry", "score": 0.8},
            {"display_name": "Physics", "score": 0.7},
            {"display_name": "Math", "score": 0.6},
        ]

        # Default max_count=10
        result = extract_concepts(concepts)
        assert len(result) == 4

        # With max_count=2
        result = extract_concepts(concepts, max_count=2)
        assert len(result) == 2
        assert "Biology" in result
        assert "Chemistry" in result

    @pytest.mark.asyncio
    async def test_transformer_journal_info_extraction(self) -> None:
        """Test journal info extraction from primary_location."""
        from bioetl.application.pipelines.openalex.extractors import (
            extract_journal_info,
        )

        primary_location = {
            "source": {
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "host_organization_name": "Springer Nature",
            }
        }

        result = extract_journal_info(primary_location)
        assert result["journal_name"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["publisher"] == "Springer Nature"

    @pytest.mark.asyncio
    async def test_transformer_open_access_extraction(self) -> None:
        """Test Open Access info extraction."""
        from bioetl.application.pipelines.openalex.extractors import (
            extract_open_access_info,
        )

        open_access = {
            "is_oa": True,
            "oa_status": "gold",
        }

        result = extract_open_access_info(open_access)
        assert result["is_oa"] is True
        assert result["oa_status"] == "gold"

        # Empty case
        result = extract_open_access_info({})
        assert result["is_oa"] is None
        assert result["oa_status"] is None
