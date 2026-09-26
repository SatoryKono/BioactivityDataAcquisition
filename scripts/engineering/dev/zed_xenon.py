#!/usr/bin/env python3
"""Zed-safe xenon complexity gate matching CI production thresholds.

Canonical CI command lives in
``.github/workflows/duplication-complexity.yml``::

    xenon --max-absolute B --max-modules B --max-average A \\
      --exclude \"...\" src

Exclude patterns MUST stay byte-synced with that workflow (and therefore with
``configs/quality/duplication_complexity_exemptions.yaml`` xenon scope via
``python -m scripts.engineering.qa check-duplication-complexity-exemptions``).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.dev.zed_env_doctor import ensure_ready

WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "duplication-complexity.yml"


def _xenon_exclude_from_workflow() -> str:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(r'--exclude "([^"]+)" src', text)
    if match is None:
        raise SystemExit(
            f"[zed_xenon] could not parse xenon --exclude list from {WORKFLOW_PATH}"
        )
    exclude = match.group(1).strip()
    if not exclude:
        raise SystemExit(f"[zed_xenon] empty xenon --exclude list in {WORKFLOW_PATH}")
    return exclude


def _platform_xenon_exclude(
    exclude: str,
    *,
    separator: str | None = None,
) -> str:
    """Adapt canonical POSIX exclude patterns to Xenon's host path format."""
    if (separator or os.sep) == "\\":
        return exclude.replace("/", "\\")
    return exclude


def _xenon_cli(*, executable: str | None = None, platform: str | None = None) -> Path:
    """Return the console-script next to the active interpreter (CI uses ``xenon``)."""
    bindir = Path(sys.executable if executable is None else executable).resolve().parent
    name = "xenon.exe" if (platform or sys.platform) == "win32" else "xenon"
    return bindir / name


def _xenon_command(exclude: str) -> list[str]:
    """Build the CI-aligned xenon argv. Xenon has no ``python -m xenon`` entry."""
    cli = _xenon_cli()
    if not cli.is_file():
        raise SystemExit(
            "[zed_xenon] xenon CLI is missing next to the interpreter: "
            f"{cli}. Refresh with: .\\scripts\\engineering\\dev\\setup_env_windows.ps1"
        )
    return [
        str(cli),
        "--max-absolute",
        "B",
        "--max-modules",
        "B",
        "--max-average",
        "A",
        "--exclude",
        exclude,
        "src",
    ]


def main(argv: list[str] | None = None) -> int:
    del argv
    os.chdir(REPO_ROOT)
    ensure_ready(modules=("xenon",))
    canonical_exclude = _xenon_exclude_from_workflow()
    exclude = _platform_xenon_exclude(canonical_exclude)
    cmd = _xenon_command(exclude)
    print("[zed_xenon] running CI-aligned complexity gate", flush=True)
    print(f"[zed_xenon] exclude={exclude}", flush=True)
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if completed.returncode == 0:
        print(
            "[zed_xenon] OK (max-absolute B, max-modules B, max-average A)", flush=True
        )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
