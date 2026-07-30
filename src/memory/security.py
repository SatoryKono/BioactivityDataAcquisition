"""Security and trust-boundary primitives for persistent agent memory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from memory.records import TrustLevel


class SecurityClassification(StrEnum):
    """Repository-neutral classification for memory content."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"  # pragma: allowlist secret


class FindingKind(StrEnum):
    """Kinds of content that must not silently cross a persistence boundary."""

    PROMPT_INJECTION = "prompt_injection"
    SECRET = "secret"  # pragma: allowlist secret
    PII = "pii"


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    """A location-free finding safe to include in logs and validation output."""

    kind: FindingKind
    rule_id: str


class UnsafeMemoryContentError(ValueError):
    """Raised when unsafe content is presented for persistent storage."""

    def __init__(self, findings: tuple[SecurityFinding, ...]) -> None:
        self.findings = findings
        rule_ids = ", ".join(finding.rule_id for finding in findings)
        super().__init__(f"memory content failed security checks: {rule_ids}")


_RULES: tuple[tuple[FindingKind, str, re.Pattern[str]], ...] = (
    (
        FindingKind.PROMPT_INJECTION,
        "prompt-ignore-instructions",
        re.compile(
            r"\b(?:ignore|disregard|override)\s+(?:all\s+)?"
            r"(?:previous|prior|system|developer)\s+instructions?\b",
            re.IGNORECASE,
        ),
    ),
    (
        FindingKind.PROMPT_INJECTION,
        "prompt-role-directive",
        re.compile(
            r"(?:^|\n)\s*(?:system|developer)\s*:\s*",
            re.IGNORECASE,
        ),
    ),
    (
        FindingKind.SECRET,
        "secret-private-key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        FindingKind.SECRET,
        "secret-github-token",
        re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        FindingKind.SECRET,
        "secret-bearer-token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    ),
    (
        FindingKind.PII,
        "pii-email-address",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        FindingKind.PII,
        "pii-international-phone-number",
        re.compile(r"(?<!\w)\+(?:[0-9][ -]?){7,14}[0-9](?!\w)"),
    ),
)


def inspect_memory_content(content: str) -> tuple[SecurityFinding, ...]:
    """Return deterministic, redacted findings for unsafe persistent content."""
    return tuple(
        SecurityFinding(kind=kind, rule_id=rule_id)
        for kind, rule_id, pattern in _RULES
        if pattern.search(content)
    )


def assert_safe_for_persistence(
    content: str,
    *,
    trust: TrustLevel,
    allow_reviewed_external: bool = False,
) -> None:
    """Fail closed before content crosses a persistent-memory boundary.

    Untrusted content is never eligible for direct persistence. Reviewed
    external content requires an explicit opt-in. Content inspection never
    includes matched values in the resulting exception.
    """
    findings = inspect_memory_content(content)
    if trust is TrustLevel.UNTRUSTED:
        findings = (
            SecurityFinding(FindingKind.PROMPT_INJECTION, "trust-untrusted-source"),
            *findings,
        )
    elif trust is TrustLevel.REVIEWED_EXTERNAL and not allow_reviewed_external:
        findings = (
            SecurityFinding(
                FindingKind.PROMPT_INJECTION,
                "trust-reviewed-external-requires-opt-in",
            ),
            *findings,
        )
    if findings:
        raise UnsafeMemoryContentError(findings)
