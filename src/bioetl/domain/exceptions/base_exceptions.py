"""Base exception classes for BioETL domain layer.

This module provides a hierarchical exception system for consistent error handling
across the BioETL project. All domain-specific exceptions should inherit from these
base classes to ensure proper error classification and handling.

REQ-ARCH-011: Domain layer should use structured exception hierarchy
REQ-ARCH-012: Exceptions should be immutable and include context
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class BioETLError(Exception):
    """Base exception for all BioETL errors.
    
    This is the root exception class for the entire BioETL exception hierarchy.
    All custom exceptions should inherit from this class either directly or
    through more specific intermediate classes.
    """
    pass


@dataclass(frozen=True)
class BioETLDomainError(BioETLError):
    """Base exception for domain layer errors.
    
    Domain errors represent invalid business logic states or violations
    of domain invariants. These are typically non-recoverable errors that
    indicate bugs in the application logic.
    
    Args:
        message: Human-readable error message
        context: Additional context data (must be JSON-serializable)
        original_exception: Original exception that caused this error (if any)
    """
    message: str
    context: Dict[str, Any] = None  # Any: Domain exception context stores JSON-serializable payload values of mixed types.
    original_exception: Optional[Exception] = None

    def __str__(self) -> str:
        """Format exception for human-readable output."""
        base_msg = f"{self.__class__.__name__}: {self.message}"
        if self.context:
            base_msg += f" | Context: {self.context}"
        if self.original_exception:
            base_msg += f" | Caused by: {self.original_exception}"
        return base_msg

    def to_dict(self) -> Dict[str, Any]:  # Any: Generic dictionary for structured logging
        """Convert exception to dictionary for structured logging."""
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context or {},
        }
        if self.original_exception:
            result["original_exception"] = str(self.original_exception)
            result["original_type"] = self.original_exception.__class__.__name__
        return result


@dataclass(frozen=True)
class BioETLValidationError(BioETLDomainError):
    """Exception for validation failures in domain layer.
    
    Validation errors occur when input data violates domain constraints
    or business rules. These are typically recoverable errors that
    should be handled by returning appropriate error responses to callers.
    """
    field_name: Optional[str] = None
    invalid_value: Optional[Any] = None  # Any: Generic invalid value from various sources

    def __post_init__(self):
        """Ensure context includes field and value information."""
        context = self.context or {}
        if self.field_name:
            context["field_name"] = self.field_name
        if self.invalid_value is not None:
            context["invalid_value"] = str(self.invalid_value)
        # Recreate with updated context
        object.__setattr__(self, 'context', context)


@dataclass(frozen=True)
class BioETLConfigurationError(BioETLDomainError):
    """Exception for configuration-related errors.
    
    Configuration errors occur when required configuration is missing,
    invalid, or inconsistent. These typically indicate deployment or
    setup issues.
    """
    config_key: Optional[str] = None

    def __post_init__(self):
        """Ensure context includes configuration key."""
        context = self.context or {}
        if self.config_key:
            context["config_key"] = self.config_key
        object.__setattr__(self, 'context', context)


@dataclass(frozen=True)
class BioETLDataQualityError(BioETLDomainError):
    """Exception for data quality issues.
    
    Data quality errors occur when input data doesn't meet expected
    quality standards but doesn't necessarily violate domain constraints.
    These may be recoverable depending on the context.
    """
    record_id: Optional[str] = None
    severity: str = "warning"

    def __post_init__(self):
        """Validate severity and ensure context includes record info."""
        if self.severity not in ("warning", "error", "critical"):
            raise ValueError(f"Invalid severity: {self.severity}")
        
        context = self.context or {}
        if self.record_id:
            context["record_id"] = self.record_id
        context["severity"] = self.severity
        object.__setattr__(self, 'context', context)


@dataclass(frozen=True)
class BioETLIntegrationError(BioETLDomainError):
    """Exception for integration and external service issues.
    
    Integration errors occur when communicating with external systems
    or services. These may be recoverable through retries or fallback
    mechanisms.
    """
    service_name: Optional[str] = None
    operation: Optional[str] = None
    is_retryable: bool = True

    def __post_init__(self):
        """Ensure context includes service and operation info."""
        context = self.context or {}
        if self.service_name:
            context["service_name"] = self.service_name
        if self.operation:
            context["operation"] = self.operation
        context["is_retryable"] = self.is_retryable
        object.__setattr__(self, 'context', context)


@dataclass(frozen=True)
class BioETLNotFoundError(BioETLDomainError):
    """Exception for resource not found errors.
    
    Not found errors occur when expected resources or entities
    cannot be located. These are typically recoverable by providing
    appropriate user feedback.
    """
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    def __post_init__(self):
        """Ensure context includes entity information."""
        context = self.context or {}
        if self.entity_type:
            context["entity_type"] = self.entity_type
        if self.entity_id:
            context["entity_id"] = self.entity_id
        object.__setattr__(self, 'context', context)


@dataclass(frozen=True)
class BioETLConflictError(BioETLDomainError):
    """Exception for conflict and concurrency errors.
    
    Conflict errors occur when operations cannot be completed due to
    concurrent modifications or version mismatches. These may require
    user intervention to resolve.
    """
    conflicting_entity: Optional[str] = None

    def __post_init__(self):
        """Ensure context includes conflict information."""
        context = self.context or {}
        if self.conflicting_entity:
            context["conflicting_entity"] = self.conflicting_entity
        object.__setattr__(self, 'context', context)
