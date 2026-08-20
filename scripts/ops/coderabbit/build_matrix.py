"""Build an exact-cover leaf matrix for a CodeRabbit residual campaign."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DATE = os.environ.get(
    "CODERABBIT_CAMPAIGN_DATE", datetime.now(UTC).strftime("%Y%m%d")
)
OUT = ROOT / "reports" / "quality" / "coderabbit" / CAMPAIGN_DATE
CAP = int(os.environ.get("CODERABBIT_LEAF_CAP", "300"))
BASE_REF = os.environ.get("CODERABBIT_BASE_REF", "origin/main")


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def tracked_files(base_sha: str) -> list[str]:
    payload = _git("ls-tree", "-rz", "--name-only", base_sha)
    return [
        item.decode("utf-8", "surrogateescape") for item in payload.split(b"\0") if item
    ]


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")


class LeafCollector:
    """Accumulate an exact-cover, capped set of campaign leaves."""

    def __init__(self, files: list[str]) -> None:
        self.files = files
        self.assigned: set[str] = set()
        self.leaves: list[dict[str, object]] = []
        self._residual_index = 1

    def add_files(
        self,
        leaf_id: str,
        wave: str,
        selected: list[str],
        note: str,
    ) -> None:
        available = sorted(set(selected) - self.assigned)
        if not available:
            return
        total_parts = (len(available) + CAP - 1) // CAP
        for index, start in enumerate(range(0, len(available), CAP), 1):
            chunk = available[start : start + CAP]
            part_id = leaf_id if total_parts == 1 else f"{leaf_id}-{index:02d}"
            manifest = OUT / f"_{safe_id(part_id)}.txt"
            manifest.write_text("\n".join(chunk) + "\n", encoding="utf-8")
            self.leaves.append(
                {
                    "id": part_id,
                    "wave": wave,
                    "files": len(chunk),
                    "under_cap": len(chunk) <= CAP,
                    "selection": note,
                    "file_list": str(manifest.relative_to(ROOT)),
                }
            )
            self.assigned.update(chunk)

    def prefix(
        self,
        leaf_id: str,
        wave: str,
        *roots: str,
        note: str = "",
    ) -> None:
        selected = [
            path
            for path in self.files
            if any(path == root or path.startswith(f"{root}/") for root in roots)
        ]
        self.add_files(leaf_id, wave, selected, note or ", ".join(roots))

    def add_remaining(self, universe: set[str]) -> None:
        groups: dict[str, list[str]] = {}
        for path in sorted(universe - self.assigned):
            parts = path.split("/")
            key = "/".join(parts[:2]) if len(parts) > 1 else "root-files"
            groups.setdefault(key, []).append(path)

        packed: list[str] = []
        packed_groups: list[str] = []
        for group, grouped_files in sorted(groups.items()):
            if len(grouped_files) > CAP:
                self._flush_packed(packed, packed_groups)
                self.add_files(
                    f"S-R-{safe_id(group)}",
                    "R",
                    grouped_files,
                    f"residual catch-all: {group}",
                )
                continue
            if packed and len(packed) + len(grouped_files) > CAP:
                self._flush_packed(packed, packed_groups)
            packed.extend(grouped_files)
            packed_groups.append(group)
        self._flush_packed(packed, packed_groups)

    def _flush_packed(self, packed: list[str], groups: list[str]) -> None:
        if not packed:
            return
        self.add_files(
            f"S-R-catchall-{self._residual_index:02d}",
            "R",
            list(packed),
            "residual catch-all: " + ", ".join(groups),
        )
        self._residual_index += 1
        packed.clear()
        groups.clear()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base_sha = _git("rev-parse", BASE_REF).decode().strip()
    files = tracked_files(base_sha)
    universe = set(files)
    collector = LeafCollector(files)

    # Wave D is carved out first so security-sensitive paths are reviewed once,
    # not duplicated in their architecture/data-plane leaves.
    security_name = re.compile(
        r"(?:secret|credential|auth|token|redact|ssrf|pickle|subprocess|path_safety|salt)",
        re.IGNORECASE,
    )
    security_roots = (
        "src/bioetl/interfaces",
        "src/bioetl/composition/bootstrap",
        "src/bioetl/infrastructure/http",
        "src/bioetl/infrastructure/storage",
        "scripts",
    )
    security_files = [
        path
        for path in files
        if path.startswith("tests/security/")
        or (
            any(path == root or path.startswith(f"{root}/") for root in security_roots)
            and security_name.search(path) is not None
        )
    ]
    add_files(
        "S-D-security-residual",
        "D",
        security_files,
        "security-relevant interfaces/composition/infra/scripts plus tests/security",
    )

    # Wave A — architecture and core code.
    domain_roots = sorted(
        {
            "/".join(path.split("/")[:4])
            for path in files
            if path.startswith("src/bioetl/domain/") and len(path.split("/")) >= 5
        }
    )
    for root in domain_roots:
        prefix(f"S01-domain-{safe_id(Path(root).name)}", "A", root)
    prefix("S01-domain-residual-root", "A", "src/bioetl/domain")
    # Reserve the data-plane pipeline subtree before the application catch-all.
    prefix("S05-app-pipelines", "B", "src/bioetl/application/pipelines")
    prefix("S02-app-core", "A", "src/bioetl/application/core")
    prefix(
        "S03-app-control-plane", "A", "src/bioetl/application/services/control_plane"
    )
    prefix("S04-app-services-other", "A", "src/bioetl/application/services")
    prefix("S04b-app-residual", "A", "src/bioetl/application")
    prefix("S09-composition", "A", "src/bioetl/composition")
    prefix("S10-interfaces-cli", "A", "src/bioetl/interfaces/cli")
    prefix("S11-interfaces-http", "A", "src/bioetl/interfaces/http")
    prefix("S11b-interfaces-residual", "A", "src/bioetl/interfaces")

    # Wave B — data plane and configuration.
    prefix("S07-infra-http", "B", "src/bioetl/infrastructure/http")
    prefix("S07-infra-storage", "B", "src/bioetl/infrastructure/storage")
    prefix("S07-infra-delta", "B", "src/bioetl/infrastructure/delta")
    prefix("S16-configs-quality", "B", "configs/quality")
    prefix("S16b-configs-other", "B", "configs")

    # Wave C — adapters, resilience, observability, infrastructure residual.
    prefix("S06-infra-adapters", "C", "src/bioetl/infrastructure/adapters")
    prefix("S08-infra-observability", "C", "src/bioetl/infrastructure/observability")
    prefix("S08b-infra-residual", "C", "src/bioetl/infrastructure")

    # Wave E — normative contracts, dashboards, and CI quality surfaces.
    prefix("S17-docs-00-project", "E", "docs/00-project")
    prefix("S17-docs-decisions", "E", "docs/02-architecture/decisions")
    dashboard_docs = [
        path
        for path in files
        if path.startswith("docs/")
        and (
            path.startswith("docs/03-guides/dashboards/")
            or "grafana" in path.lower()
            or "dashboard" in path.lower()
        )
    ]
    add_files(
        "S18-dashboard-docs", "E", dashboard_docs, "dashboard/grafana documentation"
    )
    prefix("S18-grafana", "E", "grafana")
    prefix("S19-github-workflows", "E", ".github/workflows")
    prefix("S19b-github-actions", "E", ".github/actions")

    # Wave F — test honesty.
    prefix("S12-tests-architecture", "F", "tests/architecture")
    prefix("S13-tests-unit-domain", "F", "tests/unit/domain")
    prefix("S14-tests-unit-application", "F", "tests/unit/application")
    prefix("S14b-tests-unit-infrastructure", "F", "tests/unit/infrastructure")
    prefix("S15-tests-integration", "F", "tests/integration")
    prefix("S15b-tests-unit-scripts", "F", "tests/unit/scripts")
    prefix("S15c-tests-residual", "F", "tests")

    # Residual scripts are kept as semantic subtrees.
    for script_root in (
        "scripts/engineering",
        "scripts/ai",
        "scripts/ops",
        "scripts/docs",
        "scripts/schema",
        "scripts/memory",
        "scripts/diagrams",
    ):
        prefix(f"S-R-{safe_id(script_root)}", "R", script_root)
    prefix("S-R-scripts-residual", "R", "scripts")

    # Exact catch-all: group remaining paths by top-level/second-level prefix,
    # then cap each leaf. This covers src/memory, remaining docs/reports,
    # agent runtimes, packaging, root files, and any new surface.
    remaining = sorted(universe - assigned)
    groups: dict[str, list[str]] = {}
    for path in remaining:
        parts = path.split("/")
        key = "/".join(parts[:2]) if len(parts) > 1 else "root-files"
        groups.setdefault(key, []).append(path)
    residual_index = 1
    packed: list[str] = []
    packed_groups: list[str] = []

    def flush_packed() -> None:
        nonlocal residual_index, packed, packed_groups
        if not packed:
            return
        add_files(
            f"S-R-catchall-{residual_index:02d}",
            "R",
            packed,
            "residual catch-all: " + ", ".join(packed_groups),
        )
        residual_index += 1
        packed = []
        packed_groups = []

    for group, grouped_files in sorted(groups.items()):
        if len(grouped_files) > CAP:
            flush_packed()
            add_files(
                f"S-R-{safe_id(group)}",
                "R",
                grouped_files,
                f"residual catch-all: {group}",
            )
            continue
        if packed and len(packed) + len(grouped_files) > CAP:
            flush_packed()
        packed.extend(grouped_files)
        packed_groups.append(group)
    flush_packed()

    duplicates = sum(int(leaf["files"]) for leaf in leaves) - len(assigned)
    missing = sorted(universe - assigned)
    extra = sorted(assigned - universe)
    over_cap = [leaf["id"] for leaf in leaves if not leaf["under_cap"]]
    coverage_ok = not missing and not extra and duplicates == 0 and not over_cap
    if not coverage_ok:
        raise RuntimeError(
            f"matrix coverage failure missing={len(missing)} extra={len(extra)} "
            f"duplicates={duplicates} over_cap={over_cap}"
        )

    try:
        cr_version = subprocess.check_output(
            ["/home/fedor/.local/bin/coderabbit", "--version"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        cr_version = f"unavailable: {exc}"

    matrix = {
        "campaign": f"CR-FULL-{CAMPAIGN_DATE}",
        "base_ref": BASE_REF,
        "base_sha": base_sha,
        "created_utc": datetime.now(UTC).isoformat(),
        "coderabbit": cr_version,
        "cap": CAP,
        "tracked_files": len(files),
        "assigned_files": len(assigned),
        "duplicate_assignments": duplicates,
        "missing_files": missing,
        "coverage_ok": coverage_ok,
        "leaf_count": len(leaves),
        "leaves": leaves,
    }
    (OUT / "01-scope-matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        f"# CodeRabbit full scope matrix — {CAMPAIGN_DATE}",
        "",
        f"- **BASE_SHA:** `{base_sha}`",
        f"- **CodeRabbit:** `{cr_version}`",
        f"- **Cap:** ≤{CAP} files per leaf",
        f"- **Leaves:** {len(leaves)}",
        f"- **Tracked / assigned:** {len(files)} / {len(assigned)}",
        f"- **Duplicate assignments:** {duplicates}",
        f"- **Coverage exact:** `{coverage_ok}`",
        "",
        "| leaf_id | wave | files | under_cap | selection |",
        "|---|---:|---:|---|---|",
    ]
    for leaf in sorted(leaves, key=lambda item: (str(item["wave"]), str(item["id"]))):
        selection = str(leaf["selection"]).replace("|", "\\|")
        lines.append(
            f"| `{leaf['id']}` | {leaf['wave']} | {leaf['files']} | "
            f"`{str(leaf['under_cap']).lower()}` | {selection} |"
        )
    (OUT / "01-scope-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    max_leaf = max(int(leaf["files"]) for leaf in leaves)
    print(
        f"base={base_sha} tracked={len(files)} assigned={len(assigned)} "
        f"leaves={len(leaves)} max_leaf={max_leaf} duplicates={duplicates} coverage={coverage_ok}"
    )
    for wave, count in sorted(Counter(str(leaf["wave"]) for leaf in leaves).items()):
        print(f"wave {wave}: {count}")


if __name__ == "__main__":
    main()
