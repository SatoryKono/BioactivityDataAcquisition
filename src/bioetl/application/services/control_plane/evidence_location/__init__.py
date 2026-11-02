"""Evidence-location resolve (RF-003) and registration (RF-004) seams.

Owns bounded lookup-to-data-root resolution, legacy standard-root policy,
and automatic locator registration after durable manifest save.
Ops/Run Explorer wiring of the resolver remains RF-005.
"""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence_location.registration import (
    EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
    EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS,
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationRegistrationService,
    EvidenceLocationVerifyOutcome,
    record_registration_exception_observation,
    record_registration_outcome_observation,
    record_registration_soft_failure_observation,
    record_verify_exception_observation,
    soft_failure_exception_detail,
    soft_invoke_evidence_location_verify,
)
from bioetl.application.services.control_plane.evidence_location.resolver import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolver,
    EvidenceLocationResolveResult,
    EvidenceReadContext,
    EvidenceReadContextFactoryProtocol,
)

__all__ = [
    "EVIDENCE_LOCATION_OBSERVATION_DOMAIN",
    "EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS",
    "EvidenceLocationLegacyRootPolicy",
    "EvidenceLocationRegisterRequest",
    "EvidenceLocationRegistrationOutcome",
    "EvidenceLocationRegistrationService",
    "EvidenceLocationResolveResult",
    "EvidenceLocationResolver",
    "EvidenceLocationVerifyOutcome",
    "EvidenceReadContext",
    "EvidenceReadContextFactoryProtocol",
    "record_registration_exception_observation",
    "record_registration_outcome_observation",
    "record_registration_soft_failure_observation",
    "record_verify_exception_observation",
    "soft_failure_exception_detail",
    "soft_invoke_evidence_location_verify",
]
