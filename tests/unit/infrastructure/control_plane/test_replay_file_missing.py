"""An unavailable replay object stays unknown rather than matching or failing."""

from __future__ import annotations

import pytest
from bioetl.infrastructure.control_plane.replay_object_verifier import verify_file

pytestmark = pytest.mark.unit


def test_missing_original_bytes_cannot_prove_a_digest(tmp_path):
    assert verify_file(tmp_path / "missing.bin", "a" * 64) is None


@pytest.mark.parametrize("expected", [None, "", "not-a-digest", "sha256:short"])
def test_untrusted_digest_never_opens_original_bytes(expected):
    from unittest.mock import Mock

    original = Mock()
    assert verify_file(original, expected) is None
    original.open.assert_not_called()
