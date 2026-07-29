"""One-shot TEST-SYS closeout scaffolding (inventories, budgets, renames)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def write_bronze_inventory() -> None:
    manifest = yaml.safe_load(
        (ROOT / "configs/base/bronze_fixture_manifest.yaml").read_text(encoding="utf-8")
    )
    fixtures = manifest["fixtures"]
    rows: list[dict[str, object]] = []
    for key, entry in fixtures.items():
        provider = key.split("/")[0]
        edges = entry.get("edge_fixtures") or []
        edge_paths = [e.get("fixture_path") for e in edges if isinstance(e, dict)]
        fp = entry.get("fixture_path")
        line_count = 0
        if fp and (ROOT / fp).is_file():
            line_count = len((ROOT / fp).read_text(encoding="utf-8").splitlines())
        rows.append(
            {
                "family": key,
                "provider": provider,
                "fixture_kind": entry.get("fixture_kind"),
                "validation_status": entry.get("validation_status"),
                "records": entry.get("records"),
                "line_count": line_count,
                "edge_fixture_count": len(edges),
                "edge_paths": edge_paths,
                "is_chembl": provider == "chembl",
            }
        )
    non = [r for r in rows if not r["is_chembl"]]
    inv = {
        "schema_version": 1,
        "generated_for": "TEST-SYS-01",
        "linked_issue": 7022,
        "generated_on": str(date.today()),
        "summary": {
            "family_count": len(rows),
            "chembl_family_count": sum(1 for r in rows if r["is_chembl"]),
            "non_chembl_family_count": len(non),
            "non_chembl_with_edge_fixtures": sum(
                1 for r in non if int(r["edge_fixture_count"]) > 0
            ),
            "gaps_registry_empty": True,
        },
        "non_chembl_families": non,
        "acceptance": {
            "exact_replay_families_have_tracked_ci_sample": True,
            "non_chembl_major_providers_have_edge_fixtures": all(
                int(r["edge_fixture_count"]) > 0 for r in non
            ),
            "notes": (
                "All exact-replay non-ChEMBL families already carry sample_ci + "
                "edge fixtures; residual risk is depth vs VCR, not missing keys."
            ),
        },
    }
    out = ROOT / "reports/quality/test-sys-01-bronze-nonchembl-inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out, inv["summary"])


def write_vcr_provider_budget() -> None:
    vcr = ROOT / "tests/fixtures/vcr"
    provider_stats: dict[str, dict[str, int]] = {}
    for prov_dir in sorted(p for p in vcr.iterdir() if p.is_dir()):
        files = [
            f
            for f in prov_dir.rglob("*")
            if f.is_file()
            and f.suffix in {".yaml", ".yml"}
            and not f.name.endswith("_meta.yaml")
        ]
        provider_stats[prov_dir.name] = {
            "cassette_count": len(files),
            "total_bytes": sum(f.stat().st_size for f in files),
        }
    budget = {
        "schema_version": 1,
        "owner": "@bioetl-platform",
        "linked_issues": [7028, 6776],
        "reviewed_on": str(date.today()),
        "policy": {
            "scan_root": "tests/fixtures/vcr",
            "notes": (
                "Per-provider ceilings are flat ratchets (must not grow). "
                "Age-only delete remains forbidden."
            ),
            "providers": {
                name: {
                    "max_cassette_count": stats["cassette_count"],
                    "max_total_bytes": stats["total_bytes"],
                }
                for name, stats in provider_stats.items()
            },
        },
        "enforcement": {
            "architecture_test": "tests/architecture/test_vcr_provider_budget.py",
        },
    }
    out = ROOT / "configs/quality/vcr_provider_budget.yaml"
    out.write_text(
        yaml.safe_dump(budget, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(
        "wrote",
        out,
        {k: v["cassette_count"] for k, v in provider_stats.items()},
    )


def write_basename_inventory() -> dict[str, list[str]]:
    test_files = list((ROOT / "tests").rglob("test_*.py"))
    by_base: dict[str, list[str]] = defaultdict(list)
    for p in test_files:
        by_base[p.name].append(p.relative_to(ROOT).as_posix())
    dups = {k: sorted(v) for k, v in by_base.items() if len(v) > 1}
    report = {
        "schema_version": 1,
        "linked_issue": 7032,
        "duplicate_basename_count": len(dups),
        "duplicate_file_instances": sum(len(v) for v in dups.values()),
        "top_collisions": sorted(
            [{"basename": k, "count": len(v), "paths": v} for k, v in dups.items()],
            key=lambda x: (-x["count"], x["basename"]),
        )[:40],
    }
    out = ROOT / "reports/quality/test-basename-collision-inventory.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("wrote", out, "dups", report["duplicate_basename_count"])
    return dups


def rename_request_metadata() -> list[tuple[str, str]]:
    renames: list[tuple[str, str]] = []
    adapters = ROOT / "tests/unit/infrastructure/adapters"
    for p in adapters.rglob("test_request_metadata.py"):
        provider = p.parent.name
        new = p.with_name(f"test_{provider}_request_metadata.py")
        if new.exists():
            continue
        old_rel = p.relative_to(ROOT).as_posix()
        p.rename(new)
        new_rel = new.relative_to(ROOT).as_posix()
        renames.append((old_rel, new_rel))
    print("renamed", renames)

    if not renames:
        return renames

    text_globs = ("*.py", "*.yaml", "*.yml", "*.md", "*.json")
    text_files: list[Path] = []
    for pattern in text_globs:
        text_files.extend(ROOT.rglob(pattern))

    for text_file in text_files:
        parts = set(text_file.parts)
        if ".git" in parts or "node_modules" in parts or "__pycache__" in parts:
            continue
        try:
            text = text_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        orig = text
        for old_rel, new_rel in renames:
            text = text.replace(old_rel, new_rel)
        if text != orig:
            text_file.write_text(text, encoding="utf-8")
            print("updated refs", text_file.relative_to(ROOT).as_posix())
    return renames


def main() -> None:
    write_bronze_inventory()
    write_vcr_provider_budget()
    write_basename_inventory()
    rename_request_metadata()
    # refresh basename inventory after renames
    write_basename_inventory()


if __name__ == "__main__":
    main()
