"""Security regressions for deterministic salted PII hashing."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.security.pii_hasher import SaltConfig, Sha256PiiHasher

pytestmark = [pytest.mark.security, pytest.mark.unit]


def test_pii_hasher_never_returns_plaintext_and_normalizes_equivalent_values() -> None:
    secret_salt = "security-regression-salt-material-0001"
    hasher = Sha256PiiHasher(SaltConfig(current_salt=secret_salt))

    canonical = hasher.hash_value("Jane Doe")
    equivalent = hasher.hash_value("  JANE DOE  ")

    assert canonical == equivalent
    assert canonical is not None
    assert len(canonical) == 64
    assert "jane" not in canonical.lower()
    assert secret_salt not in canonical


def test_pii_hasher_rejects_weak_salt_material() -> None:
    with pytest.raises(ValueError, match="at least 32 characters"):
        SaltConfig(current_salt="too-short")
