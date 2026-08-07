"""ORCID researcher identifier value object."""

from __future__ import annotations

import re

from bioetl.domain.value_objects.base import ValueObject

__all__ = ["ORCID"]


class ORCID(ValueObject[str]):
    """Validated Open Researcher and Contributor identifier."""

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dXx])$")
    _URL_PREFIXES = (
        *(f"{scheme}://orcid.org/" for scheme in ("https", "http")),
        "orcid.org/",
    )

    def _strip_url_prefix(self, value: str) -> str:
        for prefix in self._URL_PREFIXES:
            if value.lower().startswith(prefix.lower()):
                return value[len(prefix) :]
        return value

    @staticmethod
    def _require_str(value: object) -> str:
        if isinstance(value, str):
            return value
        raise ValueError(f"ORCID must be str, got {type(value).__name__}")

    @staticmethod
    def _orcid_check_digit(body: str) -> str:
        total = 0
        for digit in body:
            total = (total + int(digit)) * 2
        result = (12 - total % 11) % 11
        return "X" if result == 10 else str(result)

    def _match_orcid_parts(self, normalized: str, original: str) -> list[str]:
        match = self._PATTERN.match(normalized)
        if match is None:
            raise ValueError(
                f"Invalid ORCID format: {original!r}. Expected: NNNN-NNNN-NNNN-NNNN"
            )
        parts = list(match.groups())
        parts[-1] = parts[-1].upper()
        return parts

    def _validate(self, value: str) -> str:
        text = self._require_str(value)
        normalized = text.strip()
        if not normalized:
            raise ValueError("ORCID cannot be empty")
        parts = self._match_orcid_parts(
            self._strip_url_prefix(normalized).strip(), text
        )
        digits = "".join(parts)
        expected = self._orcid_check_digit(digits[:15])
        if digits[15] != expected:
            raise ValueError(
                f"Invalid ORCID checksum: {value!r} (expected check digit {expected})"
            )
        return "-".join(parts)

    @property
    def url(self) -> str:
        """Return the canonical ORCID URL."""
        return f"https://orcid.org/{self._value}"

    @property
    def compact(self) -> str:
        """Return the identifier without hyphens."""
        return self._value.replace("-", "")

    @classmethod
    def from_raw(cls, raw: str | None) -> ORCID | None:
        """Normalize a non-empty raw identifier, returning None when invalid."""
        if raw is None or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None
