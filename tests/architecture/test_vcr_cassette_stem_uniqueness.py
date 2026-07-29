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
"""Architecture guard for duplicate VCR cassette scenario stems."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"


def _iter_cassette_files() -> list[Path]:
    return sorted(
        path
        for path in VCR_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


@pytest.mark.architecture
def test_vcr_cassette_stems_are_unique_across_fixture_tree() -> None:
    """Scenario stems must map to exactly one cassette path."""
    stems: dict[str, list[str]] = defaultdict(list)
    for path in _iter_cassette_files():
        stems[path.stem].append(path.relative_to(ROOT).as_posix())

    duplicates = {
        stem: paths for stem, paths in sorted(stems.items()) if len(paths) > 1
    }

    assert duplicates == {}
