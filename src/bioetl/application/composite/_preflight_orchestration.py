"""Schema loading and extraction helpers for preflight validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite._preflight_types import FieldInfo, SchemaFields
from bioetl.domain.exceptions import BioETLError, DataQualityError

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort


class PreflightSchemaOrchestrationMixin:
    """Schema discovery and dtype extraction helper methods."""

    _SCHEMA_REGISTRY: dict[str, type] | None = None
    _logger: LoggerPort

    def _load_source_fields(self, config: CompositeConfig) -> dict[str, SchemaFields]:
        """Load field definitions from source schemas."""
        result: dict[str, SchemaFields] = {}

        seed_pipeline = config.seed.pipeline
        seed_fields = self._load_pipeline_schema_fields(seed_pipeline)
        if seed_fields and "_" in seed_pipeline:
            provider = seed_pipeline.split("_", 1)[0].lower()
            result[provider] = seed_fields
            result["seed"] = seed_fields

        for enricher in config.enrichers:
            enricher_fields = self._load_pipeline_schema_fields(enricher.pipeline)
            if enricher_fields and "_" in enricher.pipeline:
                provider = enricher.pipeline.split("_", 1)[0].lower()
                result[provider] = enricher_fields

        return result

    def _load_pipeline_schema_fields(self, pipeline_name: str) -> SchemaFields | None:
        """Load schema fields for a specific pipeline."""
        registry = self._get_schema_registry()
        if "_" not in pipeline_name:
            return None

        provider = pipeline_name.split("_", 1)[0].lower()
        schema_class = registry.get(provider)
        if schema_class is None:
            self._logger.debug(
                "No schema found for provider",
                provider=provider,
                pipeline=pipeline_name,
            )
            return None

        return self._extract_fields_from_schema(schema_class, provider)

    def _extract_fields_from_schema(
        self, schema_class: type, source: str
    ) -> SchemaFields:
        """Extract field information from a Pandera schema class."""
        fields: SchemaFields = {}

        try:
            schema_instance = schema_class.to_schema()  # type: ignore[attr-defined]
            for col_name, col_info in schema_instance.columns.items():
                dtype_str = str(col_info.dtype) if col_info.dtype else "object"
                dtype_str = self._simplify_dtype(dtype_str)
                fields[col_name] = FieldInfo(
                    name=col_name,
                    dtype=dtype_str,
                    nullable=col_info.nullable
                    if col_info.nullable is not None
                    else True,
                    source=source,
                )
        except (ValueError, TypeError, RuntimeError, DataQualityError) as error:
            self._logger.warning(
                "Failed to extract fields from schema",
                schema=schema_class.__name__,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="schema_field_extraction_failed",
            )
            fields = self._extract_fields_from_annotations(schema_class, source)
        except BioETLError as error:
            self._logger.warning(
                "Failed to extract fields from schema",
                schema=schema_class.__name__,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="schema_field_extraction_failed",
            )
            fields = self._extract_fields_from_annotations(schema_class, source)

        return fields

    def _extract_fields_from_annotations(
        self, schema_class: type, source: str
    ) -> SchemaFields:
        """Fallback: extract fields from class annotations."""
        fields: SchemaFields = {}

        for klass in schema_class.__mro__:
            if not hasattr(klass, "__annotations__"):
                continue
            for field_name, field_type in klass.__annotations__.items():
                if field_name.startswith("_") and field_name not in (
                    "_source",
                    "_dq_warn",
                    "_dq_error",
                ):
                    continue
                if field_name in fields:
                    continue

                dtype_str = self._extract_dtype_from_annotation(field_type)
                fields[field_name] = FieldInfo(
                    name=field_name,
                    dtype=dtype_str,
                    nullable=True,
                    source=source,
                )

        return fields

    def _extract_dtype_from_annotation(self, annotation: object) -> str:
        """Extract dtype string from a type annotation."""
        ann_str = str(annotation)
        if "Series[" in ann_str:
            inner = ann_str.split("Series[", 1)[1].rstrip("]")
            return self._simplify_dtype(inner)
        return self._simplify_dtype(ann_str)

    def _simplify_dtype(self, dtype_str: str) -> str:
        """Simplify a dtype string for comparison."""
        normalized = dtype_str.strip()
        for prefix in ("pandas.core.arrays.integer.", "pandas.", "pandera."):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]

        simplifications = {
            "Int64Dtype()": "int",
            "Int64Dtype": "int",
            "Int64": "int",
            "int64": "int",
            "Float64": "float",
            "float64": "float",
            "object": "str",
            "string": "str",
            "String": "str",
            "boolean": "bool",
            "datetime64[ns]": "datetime",
        }
        return simplifications.get(normalized, normalized)

    @classmethod
    def _get_schema_registry(cls) -> dict[str, type]:
        """Get or create the schema registry."""
        if cls._SCHEMA_REGISTRY is not None:
            return cls._SCHEMA_REGISTRY

        registry: dict[str, type] = {}

        try:
            from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

            registry["chembl"] = ChemblPublicationSchema
        except ImportError:
            pass  # Why: optional feature; chembl schema unavailable, skip registration

        try:
            from bioetl.domain.schemas.crossref.publication import (
                PublicationEnrichedSchema,
            )

            registry["crossref"] = PublicationEnrichedSchema
        except ImportError:
            pass  # Why: optional feature; crossref schema unavailable, skip registration

        try:
            from bioetl.domain.schemas.openalex.publication import (
                OpenAlexPublicationSchema,
            )

            registry["openalex"] = OpenAlexPublicationSchema
        except ImportError:
            pass  # Why: optional feature; openalex schema unavailable, skip registration

        try:
            from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

            registry["pubmed"] = PubMedPublicationSchema
        except ImportError:
            pass  # Why: optional feature; pubmed schema unavailable, skip registration

        try:
            from bioetl.domain.schemas.semanticscholar.publication import (
                SemanticScholarPublicationSchema,
            )

            registry["semanticscholar"] = SemanticScholarPublicationSchema
        except ImportError:
            pass  # Why: optional feature; semanticscholar schema unavailable, skip registration

        cls._SCHEMA_REGISTRY = registry
        return registry
