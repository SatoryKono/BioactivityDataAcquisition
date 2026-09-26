# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Drift guard for generated config discrepancy artifacts."""

from __future__ import annotations

import pytest

from scripts.schema.analysis.generate_config_matrix import (
    _render_parameter_matrix,
    main,
)

pytestmark = [pytest.mark.architecture, pytest.mark.timeout(300)]


def test_config_discrepancy_report_matches_deterministic_generator() -> None:
    """The config discrepancy report must be executable governance, not stale docs.

    Call the generator in-process. A subprocess cold-start of bioetl filter
    stacks on Windows cloud-synced checkouts routinely exceeds 180s even when
    the check work itself finishes in a few seconds.
    """
    assert main(["--check"]) == 0, (
        "Config comparison matrix/discrepancy report drifted from the generator. "
        "Regenerate with: python -m scripts.schema generate-config-matrix --update"
    )


def test_config_matrix_uses_repository_canonical_lf_newlines() -> None:
    """Generated CSV bytes must survive Git's eol=lf normalization unchanged."""
    matrix = _render_parameter_matrix(
        active_configs={"example": {"field": "value"}},
        all_keys=["field"],
        config_names=["example"],
    )

    assert "\r" not in matrix
    assert matrix == "Parameter Path,example\nfield,value\n"
