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
"""Integration tests for Grafana dashboard technical configuration policy."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_design_system_documents_technical_configuration_policy() -> None:
    """Design docs must distinguish governed root config from benign export noise."""
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


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_root_technical_configuration_policy(dashboard_path: Path) -> None:
    """Shipped dashboards must preserve governed root technical settings."""
    dashboard = load_dashboard(dashboard_path)
    assert dashboard.get("style") == "dark", (
        f"{dashboard_path.name} must keep style='dark'"
    )
    assert dashboard.get("editable") is True, (
        f"{dashboard_path.name} must keep editable=true"
    )
    assert dashboard.get("graphTooltip") == 1, (
        f"{dashboard_path.name} must keep graphTooltip=1"
    )
    if "hideControls" in dashboard:
        assert dashboard.get("hideControls") is False, (
            f"{dashboard_path.name} hideControls, when exported, must be false"
        )
