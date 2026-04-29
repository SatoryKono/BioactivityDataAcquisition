"""Fast architecture guardrail for scripts lifecycle registry coverage."""

from __future__ import annotations

import json
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_lifecycle_registry_covers_non_active_inventory_scripts() -> None:
    """All non-active scripts in inventory must have lifecycle entries."""
    root = _project_root()
    manifest_path = root / "configs" / "quality" / "scripts_inventory_manifest.json"
    registry_path = root / "configs" / "quality" / "scripts_lifecycle_registry.json"

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

    scripts = manifest_payload.get("scripts")
    assert isinstance(scripts, list), "Manifest key 'scripts' must be a list."

    registry_entries = registry_payload.get("entries")
    assert isinstance(registry_entries, dict), (
        "Lifecycle registry key 'entries' must be a dict."
    )

    tracked_statuses = {
        "unknown",
        "orphan",
        "temporary_diagnostic",
        "supporting",
        "legacy",
    }
    required_paths = sorted(
        {
            script["path"]
            for script in scripts
            if isinstance(script, dict)
            and isinstance(script.get("path"), str)
            and script.get("status") in tracked_statuses
        }
    )
    missing_entries = [path for path in required_paths if path not in registry_entries]

    assert not missing_entries, (
        "Missing lifecycle registry entries for non-active scripts "
        "(status in {'unknown', 'orphan', 'temporary_diagnostic', 'supporting', 'legacy'}):\n- "
        + "\n- ".join(missing_entries)
    )
