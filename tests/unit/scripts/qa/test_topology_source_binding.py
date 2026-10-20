"""A current-source projection must not impersonate or overwrite a capture."""

import pytest

from scripts.engineering.qa.report_topology_source_binding import (
    END,
    START,
    render_binding,
)

pytestmark = pytest.mark.unit


def test_source_binding_preserves_history_and_is_idempotent():
    historical = "Historical capture: 2026-01-01, coverage 90%, commit original\n"
    result = render_binding(historical, "a" * 64, 3)
    assert result.startswith(historical)
    assert "not a\nnew coverage measurement" in result
    assert render_binding(result, "a" * 64, 3) == result
    revised = render_binding(result, "b" * 64, 4)
    assert revised.startswith(historical)
    assert revised.count(START) == revised.count(END) == 1
    assert "a" * 64 not in revised


def test_source_binding_does_not_relabel_distinct_historical_hashes():
    historical = (
        "Refresh note (2026-10-08): previous accepted capture.\n"
        "`source_tree_sha256=02358f050d0c78c5b18a3c0fb59f7a55f0cda7a80591fb7db505405466c11625`\n"
        "\n"
        "Refresh note (2026-10-07): earlier raw capture.\n"
        "`source_tree_sha256=54049305075ccc3e44a24c65a2c6250e5f1265ad4af28065fe3a86bcc63e1029`\n"
    )
    existing = historical + START + "\nold current binding\n" + END + "\n"

    updated = render_binding(existing, "a" * 64, 3)

    assert updated.split(START, maxsplit=1)[0] == historical
    assert (
        "`source_tree_sha256=02358f050d0c78c5b18a3c0fb59f7a55f0cda7a80591fb7db505405466c11625`"
        in updated
    )
    assert (
        "`source_tree_sha256=54049305075ccc3e44a24c65a2c6250e5f1265ad4af28065fe3a86bcc63e1029`"
        in updated
    )


def test_source_binding_rejects_ambiguous_history():
    with pytest.raises(ValueError, match="delimiters"):
        render_binding(START, "a" * 64, 3)


def test_source_binding_rejects_invalid_inventory():
    with pytest.raises(ValueError, match="identity"):
        render_binding("historical", "unknown", 3)
