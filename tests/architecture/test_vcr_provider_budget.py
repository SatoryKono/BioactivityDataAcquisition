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
"""Per-provider VCR cassette count/size ceilings (TEST-SYS-06 / #7028)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_BUDGET = _REPO / "configs/quality/vcr_provider_budget.yaml"
_VCR_ROOT = _REPO / "tests/fixtures/vcr"


def _load_budget() -> dict[str, object]:
    payload = yaml.safe_load(_BUDGET.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _provider_stats() -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for prov_dir in sorted(p for p in _VCR_ROOT.iterdir() if p.is_dir()):
        files = [
            f
            for f in prov_dir.rglob("*")
            if f.is_file()
            and f.suffix in {".yaml", ".yml"}
            and not f.name.endswith("_meta.yaml")
        ]
        stats[prov_dir.name] = {
            "cassette_count": len(files),
            "total_bytes": sum(f.stat().st_size for f in files),
        }
    return stats


@pytest.mark.architecture
def test_vcr_provider_budget_is_flat_or_decreasing() -> None:
    """Provider cassette counts/bytes must not grow above committed ceilings."""
    budget = _load_budget()
    policy = budget["policy"]
    assert isinstance(policy, dict)
    providers = policy["providers"]
    assert isinstance(providers, dict)

    live = _provider_stats()
    regressions: list[str] = []
    for name, ceilings in providers.items():
        assert isinstance(ceilings, dict)
        max_count = int(ceilings["max_cassette_count"])
        max_bytes = int(ceilings["max_total_bytes"])
        current = live.get(name, {"cassette_count": 0, "total_bytes": 0})
        if current["cassette_count"] > max_count:
            regressions.append(
                f"{name}: count {current['cassette_count']} > max {max_count}"
            )
        if current["total_bytes"] > max_bytes:
            regressions.append(
                f"{name}: bytes {current['total_bytes']} > max {max_bytes}"
            )

    # New provider directories require an explicit ceiling entry.
    for name in live:
        if name not in providers:
            regressions.append(f"{name}: missing provider budget entry")

    assert not regressions, "VCR provider budget regressions:\n" + "\n".join(
        regressions
    )


@pytest.mark.architecture
def test_vcr_provider_budget_ceilings_are_non_negative() -> None:
    budget = _load_budget()
    policy = budget["policy"]
    assert isinstance(policy, dict)
    providers = policy["providers"]
    assert isinstance(providers, dict)
    assert providers, "provider budget map must not be empty"
    for name, ceilings in providers.items():
        assert isinstance(ceilings, dict)
        assert int(ceilings["max_cassette_count"]) >= 0, name
        assert int(ceilings["max_total_bytes"]) >= 0, name
