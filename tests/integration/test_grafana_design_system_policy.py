"""Grafana design-system documentation policy."""

from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_design_system_documents_technical_configuration_policy() -> None:
    """Distinguish governed root config from benign export noise."""
    text = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    required_tokens = {
        "Technical configuration policy: governed fields vs export noise",
        '`style` MUST be `"dark"`',
        "`editable` MUST remain `true`",
        "`graphTooltip` MUST remain `1`",
        "`hideControls` is optional",
        "Mixed panel-level `pluginVersion` values are NOT a standalone correctness failure",
        "MUST NOT bulk-rewrite shipped dashboard JSON",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        "dashboard design-system must document technical configuration policy; "
        f"missing={missing}"
    )
