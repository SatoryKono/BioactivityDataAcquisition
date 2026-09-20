"""Lock AUD-012: every src/ bandit suppression is registered with rationale."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_YAML = ROOT / "configs" / "quality" / "security_suppression_registry.yaml"
POLICY_TODAY = date(2026, 9, 18)
SUPPRESSION_RE = re.compile(r"#\s*nosec\s+(B40[45]|B60[34])\b")
POINTER_TEXT = "suppression registry"
ALLOWED_OWNERS = frozenset({"stream-a", "stream-b"})


def _load_registry() -> dict:
    payload = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _scan_src_suppressions() -> dict[tuple[str, str], list[str]]:
    """Map (path, rule) -> suppression lines for the registry scope."""
    found: dict[tuple[str, str], list[str]] = {}
    for path in sorted((ROOT / "src").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = SUPPRESSION_RE.search(line)
            if match:
                found.setdefault((rel, match.group(1)), []).append(line)
    return found


@pytest.mark.architecture
def test_suppression_registry_has_expected_shape() -> None:
    payload = _load_registry()
    assert payload["version"] == 1
    assert payload["policy_scope"] == "security_suppressions"
    assert payload["scope"]["roots"] == ["src/"]
    assert set(payload["scope"]["rules"]) >= {"B404", "B405", "B603"}

    seen_ids: set[str] = set()
    for entry in payload["entries"]:
        assert entry["id"] not in seen_ids, f"duplicate id {entry['id']}"
        seen_ids.add(entry["id"])
        assert entry["path"].startswith("src/")
        assert (ROOT / entry["path"]).exists(), entry["id"]
        assert entry["rule"] in payload["scope"]["rules"], entry["id"]
        assert str(entry["rationale"]).strip(), entry["id"]
        assert entry["owner"] in ALLOWED_OWNERS, entry["id"]
        assert date.fromisoformat(str(entry["review_date"])) >= POLICY_TODAY, (
            entry["id"]
        )


@pytest.mark.architecture
def test_every_src_suppression_is_registered() -> None:
    payload = _load_registry()
    registered = {(e["path"], e["rule"]) for e in payload["entries"]}
    live = _scan_src_suppressions()
    unregistered = sorted(set(live) - registered)
    assert unregistered == [], (
        "Bandit suppressions missing from the security registry:\n"
        + "\n".join(f"{path} {rule}" for path, rule in unregistered)
    )


@pytest.mark.architecture
def test_registry_has_no_stale_entries() -> None:
    payload = _load_registry()
    live = _scan_src_suppressions()
    stale = [
        entry["id"]
        for entry in payload["entries"]
        if (entry["path"], entry["rule"]) not in live
    ]
    assert stale == []


@pytest.mark.architecture
def test_suppression_lines_point_at_registry() -> None:
    live = _scan_src_suppressions()
    missing = sorted(
        f"{path} {rule}: {lines[0].strip()}"
        for (path, rule), lines in live.items()
        if not any(POINTER_TEXT in line for line in lines)
    )
    assert missing == [], (
        "Suppression lines must point at the registry:\n" + "\n".join(missing)
    )
