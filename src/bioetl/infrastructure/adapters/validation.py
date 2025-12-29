"""Shared validation utilities for API response parsing.

Provides type-safe parsing of API responses using Pydantic models with
graceful error handling that routes invalid records to quarantine.

See RULES.md §8.2 for JSON response modeling guidelines.
See RULES.md §2.6 for quarantine handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bioetl.domain.ports import LoggerPort


T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationResult:
    """Result of validating an API record.

    Contains either a validated record or validation error details.
    """

    record: dict[str, Any] | None = None
    """The original record data (always present)."""

    validated: BaseModel | None = None
    """The validated Pydantic model (None if validation failed)."""

    is_valid: bool = False
    """Whether validation succeeded."""

    error: str | None = None
    """Error message if validation failed."""

    error_details: list[dict[str, Any]] = field(default_factory=list)
    """Detailed error information from Pydantic validation."""


def validate_record(
    record: dict[str, Any],
    model_class: type[T],
    logger: LoggerPort | None = None,
    context: str = "",
) -> ValidationResult:
    """Validate a single record against a Pydantic model.

    Args:
        record: Dictionary record to validate.
        model_class: Pydantic model class for validation.
        logger: Optional logger for validation errors.
        context: Context string for error logging (e.g., "chembl_activity").

    Returns:
        ValidationResult containing validation outcome.

    Example:
        >>> from bioetl.infrastructure.adapters.chembl.models import ChemblActivityRecord
        >>> result = validate_record(raw_record, ChemblActivityRecord)
        >>> if result.is_valid:
        ...     process(result.validated)
        ... else:
        ...     quarantine(result.record, result.error)
    """
    try:
        validated = model_class.model_validate(record)
        return ValidationResult(
            record=record,
            validated=validated,
            is_valid=True,
        )
    except ValidationError as e:
        error_details = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in e.errors()
        ]
        error_msg = f"Validation failed: {len(e.errors())} errors"

        if logger:
            logger.warning(
                "api_record_validation_failed",
                context=context,
                error_count=len(e.errors()),
                errors=error_details[:5],  # Limit to first 5 for logging
            )

        return ValidationResult(
            record=record,
            validated=None,
            is_valid=False,
            error=error_msg,
            error_details=error_details,
        )


def validate_records(
    records: list[dict[str, Any]],
    model_class: type[T],
    logger: LoggerPort | None = None,
    context: str = "",
) -> Iterator[ValidationResult]:
    """Validate multiple records against a Pydantic model.

    Yields ValidationResult for each record, allowing mixed valid/invalid handling.

    Args:
        records: List of dictionary records to validate.
        model_class: Pydantic model class for validation.
        logger: Optional logger for validation errors.
        context: Context string for error logging.

    Yields:
        ValidationResult for each record.

    Example:
        >>> for result in validate_records(raw_records, ChemblActivityRecord):
        ...     if result.is_valid:
        ...         yield result.validated.model_dump()
        ...     else:
        ...         quarantine_writer.write(result.record, result.error)
    """
    for record in records:
        yield validate_record(record, model_class, logger, context)


def parse_with_validation(
    record: dict[str, Any],
    model_class: type[T],
    strict: bool = False,
    logger: LoggerPort | None = None,
    context: str = "",
) -> dict[str, Any]:
    """Parse a record with optional validation.

    If validation is enabled (strict=True) and fails, raises ValueError.
    Otherwise, returns the original record unchanged (graceful degradation).

    Args:
        record: Dictionary record to parse.
        model_class: Pydantic model class for validation.
        strict: If True, raise on validation failure. If False, return original.
        logger: Optional logger for validation warnings.
        context: Context string for error logging.

    Returns:
        Validated dict (model_dump) if valid, otherwise original record.

    Raises:
        ValueError: If strict=True and validation fails.

    Example:
        >>> # Graceful mode (default) - returns original on failure
        >>> record = parse_with_validation(raw, ChemblActivityRecord)
        >>>
        >>> # Strict mode - raises on failure
        >>> record = parse_with_validation(raw, ChemblActivityRecord, strict=True)
    """
    result = validate_record(record, model_class, logger, context)

    if result.is_valid and result.validated is not None:
        return result.validated.model_dump(by_alias=False)

    if strict:
        raise ValueError(result.error or "Validation failed")

    # Graceful degradation: return original record
    return record


def get_record_model(
    provider: str,
    entity_type: str,
) -> type[BaseModel] | None:
    """Get the appropriate Pydantic model for a provider/entity combination.

    Args:
        provider: Provider name (chembl, pubchem, uniprot, pubmed, crossref).
        entity_type: Entity type (activity, assay, compound, etc.).

    Returns:
        Pydantic model class or None if not found.

    Example:
        >>> model = get_record_model("chembl", "activity")
        >>> if model:
        ...     validated = model.model_validate(record)
    """
    # Import here to avoid circular imports
    if provider == "chembl":
        from bioetl.infrastructure.adapters.chembl.models import CHEMBL_RECORD_MODELS

        return CHEMBL_RECORD_MODELS.get(entity_type)

    if provider == "pubchem":
        from bioetl.infrastructure.adapters.pubchem.models import PUBCHEM_RECORD_MODELS

        return PUBCHEM_RECORD_MODELS.get(entity_type)

    if provider == "uniprot":
        from bioetl.infrastructure.adapters.uniprot.models import UNIPROT_RECORD_MODELS

        return UNIPROT_RECORD_MODELS.get(entity_type)

    if provider == "pubmed":
        from bioetl.infrastructure.adapters.pubmed.models import PUBMED_RECORD_MODELS

        return PUBMED_RECORD_MODELS.get(entity_type)

    if provider == "crossref":
        from bioetl.infrastructure.adapters.crossref.models import (
            CROSSREF_RECORD_MODELS,
        )

        return CROSSREF_RECORD_MODELS.get(entity_type)

    return None
