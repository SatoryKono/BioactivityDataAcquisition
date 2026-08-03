"""Tests for the central persistent-memory operating mode."""

from __future__ import annotations

import pytest

from memory.persistence import (
    MEMORY_MODE_ENV_VAR,
    PersistenceDisabledError,
    PersistenceMode,
    resolve_persistence_policy,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("off", PersistenceMode.OFF),
        ("disabled", PersistenceMode.OFF),
        ("read-only", PersistenceMode.READ_ONLY),
        ("RO", PersistenceMode.READ_ONLY),
        ("read-write", PersistenceMode.READ_WRITE),
        ("rw", PersistenceMode.READ_WRITE),
    ],
)
def test_resolve_persistence_policy_supports_canonical_modes_and_aliases(
    raw_value: str,
    expected: PersistenceMode,
) -> None:
    assert resolve_persistence_policy(raw_value).mode is expected


def test_default_mode_preserves_existing_read_write_behavior() -> None:
    policy = resolve_persistence_policy(environ={})

    assert policy.mode is PersistenceMode.READ_WRITE
    assert policy.can_read is True
    assert policy.can_write is True


def test_environment_selects_read_only_mode() -> None:
    policy = resolve_persistence_policy(environ={MEMORY_MODE_ENV_VAR: "read-only"})

    assert policy.can_read is True
    assert policy.can_write is False
    policy.require_read()
    with pytest.raises(PersistenceDisabledError, match="writes are disabled"):
        policy.require_write()


def test_off_mode_disables_reads_and_writes() -> None:
    policy = resolve_persistence_policy("off")

    assert policy.can_read is False
    assert policy.can_write is False
    with pytest.raises(PersistenceDisabledError, match="reads are disabled"):
        policy.require_read()
    with pytest.raises(PersistenceDisabledError, match="writes are disabled"):
        policy.require_write()


def test_explicit_value_overrides_environment() -> None:
    policy = resolve_persistence_policy(
        "read-write",
        environ={MEMORY_MODE_ENV_VAR: "off"},
    )

    assert policy.mode is PersistenceMode.READ_WRITE


def test_unknown_mode_fails_closed_without_echoing_environment() -> None:
    invalid = "secret-unsupported-mode"

    with pytest.raises(ValueError) as caught:
        resolve_persistence_policy(invalid)

    assert invalid not in str(caught.value)
    assert MEMORY_MODE_ENV_VAR in str(caught.value)
