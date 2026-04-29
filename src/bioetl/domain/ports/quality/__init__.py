"""Data quality and validation port sub-facade."""

from __future__ import annotations

from bioetl.domain.ports.quality.contract_policy import ContractPolicyProtocol
from bioetl.domain.ports.quality.dq_config import (
    BronzeDQConfigPort,
    GoldDQConfigPort,
    SilverDQConfigPort,
)
from bioetl.domain.ports.quality.dq_report import (
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzeRequest,
    SilverDQAnalyzerPort,
    coerce_silver_dq_analyze_request,
)
from bioetl.domain.ports.quality.error_classifier import ErrorClassifierPort
from bioetl.domain.ports.quality.error_handler import ErrorHandlerPort
from bioetl.domain.ports.quality.fallback_policy import FallbackPolicyPort
from bioetl.domain.ports.quality.quarantine import (
    QuarantinePort,
    QuarantineWriteRequest,
)
from bioetl.domain.ports.quality.validation import (
    GoldValidatorPort,
    SilverValidatorPort,
)

__all__ = [
    "BronzeDQAnalyzerPort",
    "BronzeDQConfigPort",
    "ContractPolicyProtocol",
    "DQReportWriterPort",
    "ErrorClassifierPort",
    "ErrorHandlerPort",
    "FallbackPolicyPort",
    "GoldDQAnalyzerPort",
    "GoldDQConfigPort",
    "GoldValidatorPort",
    "QuarantinePort",
    "QuarantineWriteRequest",
    "SilverDQAnalyzeRequest",
    "SilverDQAnalyzerPort",
    "SilverDQConfigPort",
    "SilverValidatorPort",
    "coerce_silver_dq_analyze_request",
]
