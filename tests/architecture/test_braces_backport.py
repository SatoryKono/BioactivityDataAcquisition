"""Bind the security backport's installed archive to reviewed source bytes."""

from __future__ import annotations

import pytest

from tests.architecture.backport_tarball import (
    ROOT,
    assert_archive_matches_provenance,
    assert_consumers_pin_archive,
)

pytestmark = pytest.mark.architecture
BACKPORT = ROOT / ".github/tooling/braces-backport"
CONSUMERS = (
    ".github/tooling/jscpd",
    "grafana/plugins/bioetl-scenes-app",
    "grafana/plugins/bioetl-selectorshell-panel",
)
ARCHIVE = BACKPORT / "braces-3.0.4-bioetl.1.tgz"


def test_backport_archive_matches_reviewed_source() -> None:
    assert_archive_matches_provenance(
        BACKPORT,
        archive_name=ARCHIVE.name,
        expected={"upstream_commit": "28d440b5dd449dbf1fe6f3506cf94ecca4d02660"},
    )


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_consumers_install_the_verified_backport(consumer: str) -> None:
    assert_consumers_pin_archive(
        [consumer],
        package_name="braces",
        version="3.0.4-bioetl.1",
        archive=ARCHIVE,
    )
