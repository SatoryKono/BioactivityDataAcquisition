"""Build CR-FULL scope matrix for 20260806-full campaign."""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "reports/quality/coderabbit/20260806-full"
OUT.mkdir(parents=True, exist_ok=True)
CAP = 300


def git_ls(*paths: str) -> list[str]:
    r = subprocess.run(
        ["git", "ls-files", "-z", "--", *paths],
        capture_output=True,
        check=False,
    )
    if r.returncode != 0:
        return []
    return [x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x]


def write_list(name: str, files: list[str]) -> Path:
    p = OUT / name
    p.write_text("\n".join(files) + ("\n" if files else ""), encoding="utf-8")
    return p


def main() -> None:
    leaves: list[dict[str, object]] = []

    def add_dir(leaf_id: str, wave: str, rel: str, note: str = "") -> None:
        files = git_ls(rel)
        n = len(files)
        if n == 0:
            return
        if n <= CAP:
            leaves.append(
                {
                    "id": leaf_id,
                    "wave": wave,
                    "globs": [rel],
                    "files": n,
                    "under_cap": True,
                    "dir": rel,
                    "note": note,
                }
            )
            return
        # split by subdir
        d = Path(rel)
        subdirs = sorted([p for p in d.iterdir() if p.is_dir()]) if d.is_dir() else []
        if subdirs:
            child_files: set[str] = set()
            for sd in subdirs:
                srel = sd.as_posix()
                sfiles = git_ls(srel)
                child_files |= set(sfiles)
                if not sfiles:
                    continue
                if len(sfiles) <= CAP:
                    leaves.append(
                        {
                            "id": f"{leaf_id}-{sd.name}",
                            "wave": wave,
                            "globs": [srel],
                            "files": len(sfiles),
                            "under_cap": True,
                            "dir": srel,
                            "note": f"split from {leaf_id}",
                        }
                    )
                else:
                    mid = len(sfiles) // 2
                    for i, chunk in enumerate([sfiles[:mid], sfiles[mid:]]):
                        lp = write_list(f"_{leaf_id}_{sd.name}_{i + 1}.txt", chunk)
                        leaves.append(
                            {
                                "id": f"{leaf_id}-{sd.name}-{i + 1}",
                                "wave": wave,
                                "globs": [f"{srel} half{i + 1}"],
                                "files": len(chunk),
                                "under_cap": True,
                                "dir": None,
                                "use_file_list": str(lp),
                                "note": f"half split {srel}",
                            }
                        )
            parent = sorted(set(git_ls(rel)) - child_files)
            if parent:
                for i in range(0, len(parent), CAP):
                    chunk = parent[i : i + CAP]
                    idx = i // CAP + 1
                    lid = f"{leaf_id}-root" if len(parent) <= CAP else f"{leaf_id}-root-{idx}"
                    lp = write_list(f"_{lid}.txt", chunk)
                    leaves.append(
                        {
                            "id": lid,
                            "wave": wave,
                            "globs": [f"{rel} root"],
                            "files": len(chunk),
                            "under_cap": True,
                            "dir": None,
                            "use_file_list": str(lp),
                            "note": f"root files of {rel}",
                        }
                    )
            return
        # half file list
        mid = n // 2
        for i, chunk in enumerate([files[:mid], files[mid:]]):
            lp = write_list(f"_{leaf_id}_{i + 1}.txt", chunk)
            leaves.append(
                {
                    "id": f"{leaf_id}-{i + 1}",
                    "wave": wave,
                    "globs": [f"{rel} half{i + 1}"],
                    "files": len(chunk),
                    "under_cap": True,
                    "dir": None,
                    "use_file_list": str(lp),
                    "note": f"half split {rel}",
                }
            )

    def add_file_list(leaf_id: str, wave: str, files: list[str], note: str = "") -> None:
        files = sorted(files)
        if not files:
            return
        for i in range(0, len(files), CAP):
            chunk = files[i : i + CAP]
            idx = i // CAP + 1
            lid = leaf_id if len(files) <= CAP else f"{leaf_id}-{idx}"
            lp = write_list(f"_{lid}.txt", chunk)
            leaves.append(
                {
                    "id": lid,
                    "wave": wave,
                    "globs": [note or leaf_id],
                    "files": len(chunk),
                    "under_cap": True,
                    "dir": None,
                    "use_file_list": str(lp),
                    "note": note,
                }
            )

    # Wave A — domain packages
    domain = Path("src/bioetl/domain")
    domain_pkgs = (
        sorted([p.name for p in domain.iterdir() if p.is_dir() and p.name != "__pycache__"])
        if domain.exists()
        else []
    )
    all_domain = set(git_ls("src/bioetl/domain"))
    pkg_files: set[str] = set()
    for pkg in domain_pkgs:
        rel = f"src/bioetl/domain/{pkg}"
        add_dir(f"S01-domain-{pkg}", "A", rel)
        pkg_files |= set(git_ls(rel))
    add_file_list(
        "S01-domain-residual-root",
        "A",
        sorted(all_domain - pkg_files),
        "domain residual root",
    )

    add_dir("S02-app-core", "A", "src/bioetl/application/core")
    add_dir("S03-app-control-plane", "A", "src/bioetl/application/services/control_plane")
    svc_all = set(git_ls("src/bioetl/application/services"))
    svc_cp = set(git_ls("src/bioetl/application/services/control_plane"))
    add_file_list("S04-app-services-other", "A", sorted(svc_all - svc_cp), "services excl CP")

    app_all = set(git_ls("src/bioetl/application"))
    app_known = (
        set(git_ls("src/bioetl/application/core"))
        | set(git_ls("src/bioetl/application/services"))
        | set(git_ls("src/bioetl/application/pipelines"))
    )
    add_file_list("S04b-app-residual", "A", sorted(app_all - app_known), "application residual")

    add_dir("S09-composition", "A", "src/bioetl/composition")
    add_dir("S10-interfaces-cli", "A", "src/bioetl/interfaces/cli")
    add_dir("S11-interfaces-http", "A", "src/bioetl/interfaces/http")
    iface_all = set(git_ls("src/bioetl/interfaces"))
    iface_known = set(git_ls("src/bioetl/interfaces/cli")) | set(
        git_ls("src/bioetl/interfaces/http")
    )
    add_file_list(
        "S11b-interfaces-residual",
        "A",
        sorted(iface_all - iface_known),
        "interfaces residual",
    )

    # Wave B
    add_dir("S05-app-pipelines", "B", "src/bioetl/application/pipelines")
    add_dir("S07-infra-http", "B", "src/bioetl/infrastructure/http")
    add_dir("S07-infra-storage", "B", "src/bioetl/infrastructure/storage")
    add_dir("S07-infra-delta", "B", "src/bioetl/infrastructure/delta")
    add_dir("S16-configs-quality", "B", "configs/quality")
    cfg_all = set(git_ls("configs"))
    cfg_q = set(git_ls("configs/quality"))
    add_file_list("S16b-configs-other", "B", sorted(cfg_all - cfg_q), "configs excl quality")

    # Wave C
    add_dir("S06-infra-adapters", "C", "src/bioetl/infrastructure/adapters")
    add_dir("S08-infra-observability", "C", "src/bioetl/infrastructure/observability")
    infra_all = set(git_ls("src/bioetl/infrastructure"))
    infra_known: set[str] = set()
    for p in ("adapters", "observability", "http", "storage", "delta"):
        infra_known |= set(git_ls(f"src/bioetl/infrastructure/{p}"))
    add_file_list(
        "S08b-infra-residual",
        "C",
        sorted(infra_all - infra_known),
        "infra residual",
    )

    # Wave D — security-adjacent scripts (if present)
    for name, path in (
        ("S-D-scripts-security", "scripts/security"),
        ("S-D-scripts-ops", "scripts/ops"),
        ("S-D-scripts-ci", "scripts/ci"),
    ):
        add_dir(name, "D", path)

    # Wave E
    add_dir("S17-docs-00-project", "E", "docs/00-project")
    add_dir("S17-docs-decisions", "E", "docs/02-architecture/decisions")
    add_dir("S18-grafana", "E", "grafana")
    add_dir("S19-github-workflows", "E", ".github/workflows")

    # Wave F
    add_dir("S12-tests-architecture", "F", "tests/architecture")
    add_dir("S13-tests-unit-domain", "F", "tests/unit/domain")
    add_dir("S14-tests-unit-application", "F", "tests/unit/application")
    add_dir("S14b-tests-unit-infrastructure", "F", "tests/unit/infrastructure")
    add_dir("S15-tests-integration", "F", "tests/integration")
    add_dir("S15b-tests-unit-scripts", "F", "tests/unit/scripts")
    tests_all = set(git_ls("tests"))
    tests_known: set[str] = set()
    for p in (
        "architecture",
        "unit/domain",
        "unit/application",
        "unit/infrastructure",
        "integration",
        "unit/scripts",
    ):
        tests_known |= set(git_ls(f"tests/{p}"))
    add_file_list(
        "S15c-tests-residual",
        "F",
        sorted(tests_all - tests_known),
        "tests residual",
    )

    # Residual R
    add_dir("S20-scripts", "R", "scripts")
    src_all = set(git_ls("src/bioetl"))
    src_known: set[str] = set()
    for p in ("domain", "application", "composition", "interfaces", "infrastructure"):
        src_known |= set(git_ls(f"src/bioetl/{p}"))
    add_file_list(
        "S00-src-bioetl-residual",
        "R",
        sorted(src_all - src_known),
        "src/bioetl residual",
    )

    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    try:
        cr_ver = subprocess.check_output(
            ["coderabbit", "--version"], text=True, stderr=subprocess.STDOUT
        ).strip()
    except Exception as exc:
        cr_ver = f"error: {exc}"

    over = [leaf for leaf in leaves if not leaf.get("under_cap")]
    matrix = {
        "campaign": "CR-FULL-20260806-full",
        "base_sha": sha,
        "created_utc": datetime.now(UTC).isoformat(),
        "coderabbit": cr_ver,
        "cap": CAP,
        "leaf_count": len(leaves),
        "total_files_assigned": sum(
            int(leaf["files"]) if isinstance(leaf["files"], int) else 0 for leaf in leaves
        ),
        "leaves": leaves,
    }
    (OUT / "01-scope-matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        "# CodeRabbit full scope matrix — 20260806-full",
        "",
        f"**BASE_SHA:** `{sha}`",
        f"**CodeRabbit:** {cr_ver}",
        f"**Cap:** ≤{CAP} files per leaf",
        f"**Leaves:** {len(leaves)} (non-empty)",
        f"**Sum file assignments:** {sum(int(leaf['files']) if isinstance(leaf['files'], int) else 0 for leaf in leaves)}",
        "",
        "| id | wave | files | under_cap | dir / selection |",
        "|----|------|------:|-----------|-----------------|",
    ]
    for leaf in sorted(leaves, key=lambda x: (x["wave"], x["id"])):
        globs_raw = leaf.get("globs")
        globs_list: list[object] = globs_raw if isinstance(globs_raw, list) else []
        sel = leaf.get("dir") or (
            Path(str(leaf["use_file_list"])).name
            if leaf.get("use_file_list")
            else ",".join(str(g) for g in globs_list[:60])
        )
        lines.append(
            f"| `{leaf['id']}` | {leaf['wave']} | {leaf['files']} | {leaf['under_cap']} | `{sel}` |"
        )
    lines.append("")
    if over:
        lines.append("## OVER_CAP")
        for leaf in over:
            lines.append(f"- {leaf['id']}: {leaf['files']}")
        lines.append("")
    (OUT / "01-scope-matrix.md").write_text("\n".join(lines), encoding="utf-8")

    pre = f"""# CR-FULL preflight — 20260806-full

- **UTC:** {datetime.now(UTC).isoformat()}
- **BASE_SHA:** `{sha}`
- **Branch:** main
- **CodeRabbit CLI:** {cr_ver}
- **Auth:** API key (preflight)
- **Artifacts:** `reports/quality/coderabbit/20260806-full/`
- **Prior de-dupe ref:** `reports/quality/coderabbit/20260806/`
- **Config:** `.coderabbit.yaml` assertive
- **Leaves planned:** {len(leaves)}
- **Over cap remaining:** {len(over)}

## Constraints
- ≤{CAP} files/leaf; sequential CLI; no tech-debt budget growth; no .env edits
- GH issue for every accepted finding (all severities)

## Next
Phase 1: sequential coderabbit review per leaf
"""
    (OUT / "00-preflight.md").write_text(pre, encoding="utf-8")

    print(
        f"leaves={len(leaves)} over_cap={len(over)} "
        f"sum={sum(int(leaf['files']) if isinstance(leaf['files'], int) else 0 for leaf in leaves)}"
    )
    for w, n in sorted(Counter(str(leaf["wave"]) for leaf in leaves).items()):
        print(f"  wave {w}: {n}")
    if over:
        print("OVER:")
        for leaf in over:
            print(f"  {leaf['id']} {leaf['files']}")


if __name__ == "__main__":
    main()
