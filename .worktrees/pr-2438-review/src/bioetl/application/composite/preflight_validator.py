"""Preflight validator for composite pipeline configurations.

Validates field_priorities configuration against source schemas BEFORE pipeline
execution starts. This ensures schema drift and configuration errors are caught
early, not during merge phase.

See ADR-026 for composite pipeline architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class FieldInfo:
    """Information about a field from a source schema.

    Attributes:
        name: Field name.
        dtype: Data type name (e.g., 'str', 'int', 'bool').
        nullable: Whether field can be null.
        source: Source identifier (e.g., 'chembl', 'crossref').
    """

    name: str
    dtype: str
    nullable: bool
    source: str


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single validation issue found during preflight check.

    Attributes:
        field: Field name from field_priorities.
        source: Source reference from priorities (e.g., 'chembl', 'pubmed').
        issue_type: Type of issue ('missing_field', 'type_mismatch', 'unknown_source').
        message: Human-readable description.
        severity: 'error' for blocking issues, 'warning' for non-blocking.
    """

    field: str
    source: str
    issue_type: str
    message: str
    severity: str = "error"


@dataclass
class PreflightValidationResult:
    """Result of preflight validation.

    Attributes:
        is_valid: True if no blocking errors found.
        issues: List of validation issues (errors and warnings).
        resolved_fields: Mapping of field → source that will provide it.
    """

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    resolved_fields: dict[str, str] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]


class PreflightValidationError(Exception):
    """Raised when preflight validation fails with blocking errors.

    Attributes:
        result: Full validation result with all issues.
    """

    def __init__(self, result: PreflightValidationResult) -> None:
        self.result = result
        error_msgs = [f"  - {e.field}: {e.message}" for e in result.errors]
        super().__init__(
            f"Composite pipeline preflight validation failed with "
            f"{len(result.errors)} error(s):\n" + "\n".join(error_msgs)
        )


# Type alias for schema field extraction
SchemaFields = dict[str, FieldInfo]


class CompositePreflightValidator:
    """Validates composite pipeline configuration before execution.

    Performs preflight checks on field_priorities to ensure:
    1. Each field exists in at least one source schema
    2. Each source reference is valid (exists in config)
    3. Field types are compatible across sources

    Usage:
        >>> validator = CompositePreflightValidator(logger)
        >>> result = validator.validate(composite_config)
        >>> if not result.is_valid:
        ...     raise PreflightValidationError(result)
    """

    # Map of source names to schema classes
    # Lazy-loaded to avoid circular imports
    _SCHEMA_REGISTRY: dict[str, type] | None = None

    # Compatible type groups for coalescing
    # Types within the same group can be coalesced
    _COMPATIBLE_TYPES: tuple[frozenset[str], ...] = (
        frozenset({"str", "object", "String"}),
        frozenset(
            {"int", "Int64", "int64", "Int64Dtype", "float", "Float64", "float64"}
        ),
        frozenset({"bool", "boolean"}),
        frozenset({"date", "datetime", "datetime64"}),
    )

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize validator.

        Args:
            logger: Logger for validation messages.
        """
        self._logger = logger

    def validate(
        self,
        config: CompositeConfig,
        *,
        fail_on_error: bool = True,
    ) -> PreflightValidationResult:
        """Validate composite configuration field_priorities.

        Checks that all field priorities reference valid fields and sources
        with compatible types.

        Args:
            config: Composite pipeline configuration.
            fail_on_error: If True, raises PreflightValidationError on errors.

        Returns:
            PreflightValidationResult with validation outcome.

        Raises:
            PreflightValidationError: If fail_on_error=True and errors found.
        """
        issues: list[ValidationIssue] = []
        resolved_fields: dict[str, str] = {}

        # Get valid source names from config
        valid_sources = self._get_valid_sources(config)

        # Load schema fields for all sources
        source_fields = self._load_source_fields(config)

        # Log schema loading summary
        self._logger.debug(
            "Preflight validator loaded source schemas",
            sources=list(source_fields.keys()),
            field_counts={s: len(fields) for s, fields in source_fields.items()},
        )

        # Validate each field_priority entry
        field_priorities = config.merge.field_priorities
        for field_name, priorities in field_priorities.items():
            field_issues, resolved_source = self._validate_field_priority(
                field_name=field_name,
                priorities=priorities,
                valid_sources=valid_sources,
                source_fields=source_fields,
            )
            issues.extend(field_issues)
            if resolved_source:
                resolved_fields[field_name] = resolved_source

        # Determine if validation passed (no errors)
        is_valid = all(i.severity != "error" for i in issues)

        result = PreflightValidationResult(
            is_valid=is_valid,
            issues=issues,
            resolved_fields=resolved_fields,
        )

        # Log validation result
        if is_valid:
            self._logger.info(
                "Preflight validation passed",
                composite=config.name,
                fields_validated=len(field_priorities),
                resolved_fields=resolved_fields,
            )
        else:
            self._logger.error(
                "Preflight validation failed",
                composite=config.name,
                error_count=len(result.errors),
                warning_count=len(result.warnings),
                errors=[
                    {"field": e.field, "issue": e.issue_type, "msg": e.message}
                    for e in result.errors
                ],
            )

        if fail_on_error and not is_valid:
            raise PreflightValidationError(result)

        return result

    def _get_valid_sources(self, config: CompositeConfig) -> frozenset[str]:
        """Extract valid source names from composite config.

        Valid sources include:
        - 'seed' (keyword for seed pipeline)
        - Seed provider name (e.g., 'chembl')
        - All enricher provider names (e.g., 'crossref', 'pubmed')

        Args:
            config: Composite configuration.

        Returns:
            Frozen set of valid source names.
        """
        sources: set[str] = {"seed"}

        # Add seed provider
        seed_pipeline = config.seed.pipeline
        if "_" in seed_pipeline:
            seed_provider = seed_pipeline.split("_", 1)[0]
            sources.add(seed_provider)
            sources.add(seed_provider.lower())

        # Add enricher providers
        for enricher in config.enrichers:
            if "_" in enricher.pipeline:
                provider = enricher.pipeline.split("_", 1)[0]
                sources.add(provider)
                sources.add(provider.lower())

        return frozenset(sources)

    def _load_source_fields(self, config: CompositeConfig) -> dict[str, SchemaFields]:
        """Load field definitions from source schemas.

        Args:
            config: Composite configuration.

        Returns:
            Mapping of source name → field definitions.
        """
        result: dict[str, SchemaFields] = {}

        # Load seed schema
        seed_pipeline = config.seed.pipeline
        seed_fields = self._load_pipeline_schema_fields(seed_pipeline)
        if seed_fields and "_" in seed_pipeline:
            provider = seed_pipeline.split("_", 1)[0].lower()
            result[provider] = seed_fields
            result["seed"] = seed_fields  # Alias for 'seed' keyword

        # Load enricher schemas
        for enricher in config.enrichers:
            enricher_fields = self._load_pipeline_schema_fields(enricher.pipeline)
            if enricher_fields and "_" in enricher.pipeline:
                provider = enricher.pipeline.split("_", 1)[0].lower()
                result[provider] = enricher_fields

        return result

    def _load_pipeline_schema_fields(self, pipeline_name: str) -> SchemaFields | None:
        """Load schema fields for a specific pipeline.

        Args:
            pipeline_name: Pipeline name (e.g., 'chembl_publication').

        Returns:
            Mapping of field name → FieldInfo, or None if schema not found.
        """
        registry = self._get_schema_registry()

        # Extract provider from pipeline name
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
        """Extract field information from a Pandera schema class.

        Args:
            schema_class: Pandera DataFrameSchema class.
            source: Source identifier for the schema.

        Returns:
            Mapping of field name → FieldInfo.
        """
        fields: SchemaFields = {}

        # Get schema columns via Pandera API
        try:
            # Instantiate schema to access columns
            # Pandera DataFrameModel classes have to_schema() method
            schema_instance = schema_class.to_schema()  # type: ignore[attr-defined]
            for col_name, col_info in schema_instance.columns.items():
                # Extract type info
                dtype_str = str(col_info.dtype) if col_info.dtype else "object"
                # Simplify type name
                dtype_str = self._simplify_dtype(dtype_str)

                fields[col_name] = FieldInfo(
                    name=col_name,
                    dtype=dtype_str,
                    nullable=col_info.nullable
                    if col_info.nullable is not None
                    else True,
                    source=source,
                )
        except Exception as e:
            self._logger.warning(
                "Failed to extract fields from schema",
                schema=schema_class.__name__,
                error=str(e),
            )
            # Fallback: try to get fields from class annotations
            fields = self._extract_fields_from_annotations(schema_class, source)

        return fields

    def _extract_fields_from_annotations(
        self, schema_class: type, source: str
    ) -> SchemaFields:
        """Fallback: extract fields from class annotations.

        Args:
            schema_class: Schema class.
            source: Source identifier.

        Returns:
            Mapping of field name → FieldInfo.
        """
        fields: SchemaFields = {}

        # Traverse MRO to get all annotations including inherited
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
                    nullable=True,  # Assume nullable in fallback
                    source=source,
                )

        return fields

    def _extract_dtype_from_annotation(self, annotation: object) -> str:
        """Extract dtype string from a type annotation.

        Args:
            annotation: Type annotation (e.g., Series[str]).

        Returns:
            Simplified dtype string.
        """
        ann_str = str(annotation)
        # Handle Series[str], Series[int], etc.
        if "Series[" in ann_str:
            inner = ann_str.split("Series[", 1)[1].rstrip("]")
            return self._simplify_dtype(inner)
        return self._simplify_dtype(ann_str)

    def _simplify_dtype(self, dtype_str: str) -> str:
        """Simplify a dtype string for comparison.

        Args:
            dtype_str: Raw dtype string.

        Returns:
            Simplified dtype name.
        """
        dtype_str = dtype_str.strip()
        # Remove pandas/pandera prefixes
        for prefix in ("pandas.core.arrays.integer.", "pandas.", "pandera."):
            if dtype_str.startswith(prefix):
                dtype_str = dtype_str[len(prefix) :]

        # Simplify common types
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
        return simplifications.get(dtype_str, dtype_str)

    def _validate_field_priority(
        self,
        field_name: str,
        priorities: tuple[str, ...],
        valid_sources: frozenset[str],
        source_fields: dict[str, SchemaFields],
    ) -> tuple[list[ValidationIssue], str | None]:
        """Validate a single field_priority entry.

        Args:
            field_name: Name of the field being prioritized.
            priorities: Ordered list of source preferences.
            valid_sources: Set of valid source names.
            source_fields: Schema fields by source.

        Returns:
            Tuple of (issues, resolved_source).
        """
        issues: list[ValidationIssue] = []
        resolved_source: str | None = None
        field_dtypes: dict[str, str] = {}

        # Check each priority source
        for source in priorities:
            source_lower = source.lower()

            # Check if source is valid (exists in config)
            if source_lower not in valid_sources:
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        source=source,
                        issue_type="unknown_source",
                        message=f"Source '{source}' not found in composite config "
                        f"(valid: {sorted(valid_sources)})",
                    )
                )
                continue

            # Check if field exists in source schema
            schema_fields = source_fields.get(source_lower, {})
            if field_name not in schema_fields:
                # This is a warning, not error - field may not exist in this source
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        source=source,
                        issue_type="missing_field",
                        message=f"Field '{field_name}' not found in {source} schema",
                        severity="warning",  # Warning: field may come from other source
                    )
                )
            else:
                # Field exists - record dtype and resolved source
                field_info = schema_fields[field_name]
                field_dtypes[source] = field_info.dtype
                if resolved_source is None:
                    resolved_source = source

        # Check that field exists in at least one source
        if not field_dtypes:
            issues.append(
                ValidationIssue(
                    field=field_name,
                    source=",".join(priorities),
                    issue_type="missing_field",
                    message=f"Field '{field_name}' not found in ANY source schema "
                    f"(checked: {list(priorities)})",
                    severity="error",
                )
            )

        # Check type compatibility across sources
        if len(field_dtypes) > 1:
            type_issue = self._check_type_compatibility(field_name, field_dtypes)
            if type_issue:
                issues.append(type_issue)

        return issues, resolved_source

    def _check_type_compatibility(
        self, field_name: str, field_dtypes: dict[str, str]
    ) -> ValidationIssue | None:
        """Check if field types are compatible across sources.

        Args:
            field_name: Name of the field.
            field_dtypes: Mapping of source → dtype.

        Returns:
            ValidationIssue if incompatible, None otherwise.
        """
        dtypes = list(field_dtypes.values())
        sources = list(field_dtypes.keys())

        # Check if all types are in the same compatibility group
        for compat_group in self._COMPATIBLE_TYPES:
            if all(self._dtype_in_group(dt, compat_group) for dt in dtypes):
                return None

        # Types are incompatible
        return ValidationIssue(
            field=field_name,
            source=",".join(sources),
            issue_type="type_mismatch",
            message=f"Incompatible types for '{field_name}': "
            f"{dict(zip(sources, dtypes, strict=False))}",
            severity="error",
        )

    def _dtype_in_group(self, dtype: str, group: frozenset[str]) -> bool:
        """Check if a dtype belongs to a compatibility group.

        Args:
            dtype: Dtype string.
            group: Set of compatible types.

        Returns:
            True if dtype is in the group.
        """
        dtype_lower = dtype.lower()
        return dtype_lower in {g.lower() for g in group}

    @classmethod
    def _get_schema_registry(cls) -> dict[str, type]:
        """Get or create the schema registry.

        Lazy-loads schema classes to avoid circular imports.

        Returns:
            Mapping of provider name → schema class.
        """
        if cls._SCHEMA_REGISTRY is not None:
            return cls._SCHEMA_REGISTRY

        registry: dict[str, type] = {}

        # Load publication schemas
        try:
            from bioetl.domain.schemas.chembl.publication import (
                ChemblPublicationSchema,
            )

            registry["chembl"] = ChemblPublicationSchema
        except ImportError:
            pass

        try:
            from bioetl.domain.schemas.crossref.publication import (
                PublicationEnrichedSchema,
            )

            registry["crossref"] = PublicationEnrichedSchema
        except ImportError:
            pass

        try:
            from bioetl.domain.schemas.openalex.publication import (
                OpenAlexPublicationSchema,
            )

            registry["openalex"] = OpenAlexPublicationSchema
        except ImportError:
            pass

        try:
            from bioetl.domain.schemas.pubmed.publication import (
                PubMedPublicationSchema,
            )

            registry["pubmed"] = PubMedPublicationSchema
        except ImportError:
            pass

        try:
            from bioetl.domain.schemas.semanticscholar.publication import (
                SemanticScholarPublicationSchema,
            )

            registry["semanticscholar"] = SemanticScholarPublicationSchema
        except ImportError:
            pass

        cls._SCHEMA_REGISTRY = registry
        return registry

    def log_resolved_field_sources(
        self, result: PreflightValidationResult, composite_name: str
    ) -> None:
        """Log resolved field sources for debugging and auditability.

        Args:
            result: Validation result with resolved fields.
            composite_name: Name of the composite pipeline.
        """
        if not result.resolved_fields:
            return

        self._logger.info(
            "Field priority resolution",
            composite=composite_name,
            resolved_fields=result.resolved_fields,
            field_count=len(result.resolved_fields),
        )

        # Log each field individually at debug level
        for field_name, source in result.resolved_fields.items():
            self._logger.debug(
                "Resolved field source",
                composite=composite_name,
                field=field_name,
                primary_source=source,
            )
