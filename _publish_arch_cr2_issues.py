#!/usr/bin/env python3
"""Create ARCH-CR2 GitHub issues from residual CodeRabbit architecture audit."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "SatoryKono/BioactivityDataAcquisition"
GH = os.environ.get("GH_BIN", r"C:\Program Files\GitHub CLI\gh.exe")
REPORT = "reports/grok/review_coderabbit_architecture_audit_20260728_1520_FINAL.md"
JSON_AUDIT = "reports/grok/review_coderabbit_architecture_audit_20260728_1520.json"

ISSUES: list[dict] = [
    {
        "code": "ARCH-CR2-00",
        "title": "[meta][architecture] ARCH-CR2: CodeRabbit residual architecture remediation wave 2",
        "labels": ["architecture", "tech-debt", "priority:medium"],
        "body": f"""## Summary

Epic for **second residual wave** after CodeRabbit full architecture audit (CLI 0.7.0).

**Evidence**
- `{REPORT}`
- `{JSON_AUDIT}`
- Playbook: `docs/03-guides/coderabbit-audit-playbook.md`
- Prior closed wave: ARCH-CR #6862–#6870

**Stats:** 111 unique findings (53 major / 20 minor / 38 trivial) across 16 scopes.

## Children

| Code | Pri | Theme |
| --- | --- | --- |
| ARCH-CR2-01 | P0 | Async bronze storage I/O residual |
| ARCH-CR2-02 | P0 | Control-plane hydration + medallion lifecycle |
| ARCH-CR2-03 | P0 | Health server quarantine ordering |
| ARCH-CR2-04 | P1 | Maintenance CLI shared command mutation |
| ARCH-CR2-05 | P1 | Test densification (checkpoint/registry/CLI/composite) |
| ARCH-CR2-06 | P1 | Typing residual (casts / TypedDict) — coord PD |
| ARCH-CR2-07 | P2 | Docs/ADR SSOT residual |
| ARCH-CR2-08 | P2 | Config governance residual |
| ARCH-CR2-09 | P2 | Architecture test honesty |

## Constraints

1. **No tech-debt budget growth.**
2. Domain I/O-free; DI only in composition.
3. Prefer verify-then-fix; drop false positives with code evidence.
4. Do not reopen closed ARCH-CR-01..08 unless regression proven.

## Acceptance

- [ ] All children closed or rejected with evidence
- [ ] Optional CR re-run on fixed scopes
- [ ] Layer violations remain 0
""",
    },
    {
        "code": "ARCH-CR2-01",
        "title": "[P0][architecture] ARCH-CR2-01: Async bronze storage I/O residual (to_thread)",
        "labels": [
            "bug",
            "architecture",
            "layer:infrastructure",
            "performance",
            "priority:high",
        ],
        "body": f"""## Summary

CodeRabbit residual audit still flags **blocking sync I/O inside async bronze paths**. Related to closed ARCH-CR-01 — verify remaining call sites and finish offload.

**Audit:** `{REPORT}` (infra_storage majors)

## Anchors

- `src/bioetl/infrastructure/storage/bronze/io_mixin.py` (~line 133)
- `src/bioetl/infrastructure/storage/bronze/write_execution.py` (~line 172)
- `src/bioetl/infrastructure/storage/bronze/read_cleanup_mixin.py` (~line 81, 168–169)
- Related: `contract_registry_loader.py` ThreadPoolExecutor timeout handling (infra_config)

## Required work

1. Audit async methods for sync disk/network work (checksum, mkdir, read/write, sidecar, list batches).
2. Route blocking work via `asyncio.to_thread` / existing executor helpers used elsewhere.
3. Add/extend unit tests that assert offload path is used (mock/spy pattern preferred).
4. Confirm no domain layer changes.

## Acceptance

- [ ] No intentional blocking FS/CPU on the event loop in listed bronze async APIs
- [ ] Tests cover at least one write + one cleanup/list path
- [ ] No debt-budget growth
""",
    },
    {
        "code": "ARCH-CR2-02",
        "title": "[P0][architecture] ARCH-CR2-02: Control-plane hydration strictness + medallion lifecycle errors",
        "labels": [
            "bug",
            "architecture",
            "layer:application",
            "reproducibility",
            "priority:high",
        ],
        "body": f"""## Summary

Residual correctness findings on **manifest rehydration** and **medallion lifecycle exception mapping**.

**Audit:** `{REPORT}` (app_services majors)

## Anchors

1. **Hydration strictness**  
   `src/bioetl/application/services/control_plane/manifest/_service_hydration.py` (~119–159)  
   Make source-reference / input-snapshot hydration strict and consistent (fail closed on malformed/missing critical refs rather than silent partial state).

2. **Lifecycle errors**  
   `src/bioetl/application/services/medallion/medallion_lifecycle.py` (~51–58)  
   Remove broad `RuntimeError` bucket from `_LIFECYCLE_OPERATION_ERRORS`; map specific runtime failures intentionally.

3. **Related coverage**  
   - `historical_corpus_models.py` scalar serialization regression tests  
   - `medallion_maintenance_mixin.py` vacuum/archive nominal tests (may share ARCH-CR2-05)

## Acceptance

- [ ] Hydration rejects invalid critical payloads with explicit errors
- [ ] Lifecycle error map does not treat all RuntimeError identically without taxonomy
- [ ] Unit tests for hydration happy + failure paths
- [ ] No budget growth
""",
    },
    {
        "code": "ARCH-CR2-03",
        "title": "[P0][architecture] ARCH-CR2-03: Health server lifecycle resolves quarantine before build",
        "labels": [
            "bug",
            "architecture",
            "layer:interfaces",
            "priority:high",
        ],
        "body": f"""## Summary

CodeRabbit flags health-server lifecycle assembling health deps **before** quarantine service is resolved.

**Audit:** `{REPORT}` (interfaces)

## Anchors

- `src/bioetl/interfaces/cli/commands/domains/health/server_integration_lifecycle.py` (~58–74)  
  `_run_health_server` should resolve quarantine service before `_deps.build_health...` if quarantine is a required dependency of the health surface.

- Tests: `server_integration_observability.py`, `server_integration_options.py` (nominal coverage — may land in ARCH-CR2-05)

## Acceptance

- [ ] Ordering fixed: quarantine available when health graph is built
- [ ] Regression test for startup path with quarantine enabled/disabled
- [ ] No silent None quarantine when config expects quarantine features
""",
    },
    {
        "code": "ARCH-CR2-04",
        "title": "[P1][architecture] ARCH-CR2-04: Maintenance CLI must not mutate shared command objects",
        "labels": [
            "bug",
            "architecture",
            "layer:interfaces",
            "priority:medium",
        ],
        "body": f"""## Summary

`_load_maintenance_command` must not mutate shared command objects returned by eager registries.

**Audit:** `{REPORT}`  
**Anchor:** `src/bioetl/interfaces/cli/commands/domains/maintenance/command_group.py` (~69–89)

## Acceptance

- [ ] Commands returned by registry are not mutated in place (copy / factory pattern)
- [ ] Unit test proves two loads do not cross-contaminate options/state
""",
    },
    {
        "code": "ARCH-CR2-05",
        "title": "[P1][architecture] ARCH-CR2-05: Test densification for checkpoint, registry, CLI, composite, CP helpers",
        "labels": [
            "enhancement",
            "architecture",
            "tests",
            "priority:medium",
        ],
        "body": f"""## Summary

Largest residual class: **missing nominal-path unit tests** for architecture-program helpers. Bundle — do not open one issue per file.

**Audit:** `{REPORT}` (composition, app_*, interfaces majors)

## Target surfaces (representative)

### Composition / checkpoint / registry
- `composition/factories/pipeline_support/checkpoint_metadata_helpers.py`
- `checkpoint_policy_helpers.py`
- `checkpoint_metadata_resolution.py`
- `registry_validation_helpers.py`
- `pipeline/_runner_assembly_support.py` (observer identity assembly)
- `runtime_builders/_run_manifest_refs.py` (lazy facade)

### Application
- `application/composite/_coalesce_timestamp_support.py` (Polars nominal path)
- `application/pipelines/common/publication_transformer_hooks_mixin.py`
- `application/services/protein/classification_resolution.py`
- `application/services/medallion/medallion_maintenance_mixin.py` (vacuum/archive)
- control-plane replay/manifest helpers flagged as test-only majors

### Interfaces
- health server options/observability helpers
- `_workflow_run_support.py` metrics publish paths
- `cli/main.py` maintenance command mapping

## Acceptance

- [ ] At least one focused unit test module/group per bullet family above (or explicit reject if already covered)
- [ ] Prefer pure unit tests; no debt-budget growth
- [ ] Refresh `module-coverage-inventory.json` `source_tree_sha256` if `src/bioetl/**` changes inventory expectations
""",
    },
    {
        "code": "ARCH-CR2-06",
        "title": "[P1][architecture] ARCH-CR2-06: Typing residual — cast(Any,None) storage mixins + entity TypedDict",
        "labels": [
            "architecture",
            "layer:composition",
            "layer:domain",
            "priority:medium",
        ],
        "body": f"""## Summary

Typing residuals from CR that overlap Project Diagnostics / basedpyright work.

**Audit:** `{REPORT}`  
**Coordinate with:** open types/PD epics (e.g. PD residual issues) — avoid duplicate fixes.

## Anchors

- `composition/health_service_access.py` — remove broad `reportInvalidCast=false` if safe
- `composition/factories/storage/{{clear,merged,health,maintenance}}_mixin.py` — replace `cast(Any, None)` writer defaults with typed init contracts
- `domain/entities/bioactivity/_entity.py` — tighten constructor mapping typing (TypedDict / exact cast)
- `interfaces/cli/commands/__init__.py` — remove module-wide pyright suppression if cycles resolved

## Acceptance

- [ ] Invalid-cast suppressions reduced only where type graph is honest
- [ ] Storage mixins no longer use `cast(Any, None)` as default dependency placeholders without typed Optional protocol
- [ ] No new `# type: ignore` sprawl
- [ ] Aligns with basedpyright/PD budget policy (no budget growth)
""",
    },
    {
        "code": "ARCH-CR2-07",
        "title": "[P2][architecture] ARCH-CR2-07: Docs/ADR residual SSOT after CR re-audit",
        "labels": [
            "documentation",
            "architecture",
            "priority:low",
        ],
        "body": f"""## Summary

Documentation residuals from CR residual audit (not product behavior).

**Audit:** `{REPORT}` (docs_00_project, docs_decisions)

## Anchors

- `docs/00-project/rules-summary.md` — sync annotation to RULES **6.1.6** if still drifting
- `docs/00-project/NORMATIVE_SOURCES.md` — `docs/05-engineering/**` ownership row vs RULES
- `docs/00-project/TOOLS.md` — CodeRabbit section: real workflow/install pointers
- `ADR-052` — Migration + Rollback sections
- `ADR-053` — explicit rollback/parity-failure procedure for Scenes UID cutover
- `ADR-040` / decisions README — minor consistency notes if still open

## Acceptance

- [ ] RULES version references consistent across summary/ownership surfaces
- [ ] ADR-052/053 have explicit Migration/Rollback
- [ ] No second SSOT invented
""",
    },
    {
        "code": "ARCH-CR2-08",
        "title": "[P2][architecture] ARCH-CR2-08: Config governance residual (scorecard, allowlists, shards)",
        "labels": [
            "config",
            "architecture",
            "priority:low",
        ],
        "body": f"""## Summary

Config governance hygiene findings — **verify before changing counters** (must not grow debt budgets incorrectly).

**Audit:** `{REPORT}` (configs_quality)

## Anchors

- `configs/quality/debt_scorecard.yaml` — classification counters consistency
- `configs/quality/dashboard_query_duplicate_allowlist.yaml` — remove unjustified exact duplicates
- `configs/quality/generated_artifact_routing.yaml` — allowlist roots for dashboard docs paths if navigable
- `configs/quality/test_governance_audit.yaml` — markerless drift max must not ratchet up without cause
- `configs/quality/internal_compatibility_shim_inventory.yaml` — exit criteria first-party importers
- `configs/quality/pytest_shards.yaml` — ignore-glob for closeout tests under `tests/architecture/`

## Acceptance

- [ ] Each change justified with evidence (no silent budget growth)
- [ ] Gates still pass
- [ ] Explicit reject acceptable if CR misread generated counters
""",
    },
    {
        "code": "ARCH-CR2-09",
        "title": "[P2][architecture] ARCH-CR2-09: Architecture test honesty (closeout / live residual / any-budget)",
        "labels": [
            "tests",
            "architecture",
            "priority:low",
        ],
        "body": f"""## Summary

CR flagged architecture tests that can **pass while governance signals weaken**.

**Audit:** `{REPORT}` (tests_architecture)

## Anchors (representative)

- `test_live_residual_snapshot.py` — historical tech-debt JSON presence should use committed snapshot/manifest, not only path existence
- `test_unit_fast_lane_fs_policy.py` — exact ignore matching
- `test_coverage_verify_lane_contract.py` — parse named job only
- `test_any_budget.py` — bind exemption markers to specific Any statements
- `test_observability_dashboard_tooling.py` — avoid whole-script skip of generators
- tech-debt closeout tests (`5657`, `5677`, `5564`, `5651`, `5618`, …) — strengthen disposition/date assertions without expanding budgets

## Acceptance

- [ ] Weak assertions tightened or justified
- [ ] No debt-budget growth
- [ ] Closeout tests remain deterministic on clean checkout
""",
    },
]


def gh(*args: str) -> str:
    env = os.environ.copy()
    token = env.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN") or env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if token:
        env["GH_TOKEN"] = token
    r = subprocess.run(
        [GH, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr or r.stdout}")
    return r.stdout.strip()


def main() -> int:
    dry = "--dry-run" in sys.argv
    publish: dict = {
        "audit_report": REPORT,
        "audit_json": JSON_AUDIT,
        "stamp": "20260728_1520",
        "base": "f7ec4386fda4549fa44faa071ab6627e219ba6c1",
        "issues": [],
    }
    epic_number: int | None = None

    for item in ISSUES:
        title = item["title"]
        body = item["body"]
        labels = item["labels"]
        code = item["code"]
        print(f"Creating {code}: {title[:70]}...", flush=True)
        if dry:
            publish["issues"].append({"code": code, "title": title, "dry_run": True})
            continue
        args = [
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            title,
            "--body",
            body,
        ]
        for lab in labels:
            args.extend(["--label", lab])
        try:
            url = gh(*args)
        except RuntimeError as e:
            # retry without labels that may not exist
            print(f"  label retry: {e}", flush=True)
            args = [
                "issue",
                "create",
                "--repo",
                REPO,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "architecture",
            ]
            url = gh(*args)
        num = int(url.rstrip("/").split("/")[-1])
        print(f"  -> #{num} {url}", flush=True)
        publish["issues"].append({"code": code, "number": num, "url": url, "title": title})
        if code == "ARCH-CR2-00":
            epic_number = num

    # link children to epic via comments
    if epic_number and not dry:
        child_lines = [
            f"- [{i['code']}]({i['url']})"
            for i in publish["issues"]
            if i.get("code") != "ARCH-CR2-00" and i.get("url")
        ]
        if child_lines:
            comment = "## Published children\n\n" + "\n".join(child_lines) + f"\n\nAudit: `{REPORT}`\n"
            gh(
                "issue",
                "comment",
                str(epic_number),
                "--repo",
                REPO,
                "--body",
                comment,
            )

    out = ROOT / "reports" / "quality" / "architecture-coderabbit-2026-07-29-issue-publish.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(publish, indent=2), encoding="utf-8")
    print(f"Publish record: {out}", flush=True)

    # update issue pack table if not dry
    pack = ROOT / ".github" / "ISSUES" / "ARCH-CR2-2026-07-29-ISSUE-PACK.md"
    if pack.exists() and not dry and publish["issues"]:
        text = pack.read_text(encoding="utf-8")
        rows = [
            "| Code | Pri | Issue | URL |",
            "|------|-----|------:|-----|",
        ]
        pri = {
            "ARCH-CR2-00": "meta",
            "ARCH-CR2-01": "P0",
            "ARCH-CR2-02": "P0",
            "ARCH-CR2-03": "P0",
            "ARCH-CR2-04": "P1",
            "ARCH-CR2-05": "P1",
            "ARCH-CR2-06": "P1",
            "ARCH-CR2-07": "P2",
            "ARCH-CR2-08": "P2",
            "ARCH-CR2-09": "P2",
        }
        for i in publish["issues"]:
            code = i["code"]
            rows.append(
                f"| {code} | {pri.get(code, '?')} | #{i.get('number', '?')} | {i.get('url', '')} |"
            )
        block = (
            "## Issue codes — published\n\n"
            + "\n".join(rows)
            + f"\n\nPublish record: `{out.relative_to(ROOT).as_posix()}`\n"
        )
        if "## Issue codes — published" not in text:
            text = text.replace("## Issue codes\n", "## Issue codes\n\n" + block + "\n", 1)
        else:
            # replace existing published section roughly
            text = text
        pack.write_text(text, encoding="utf-8")
        print(f"Updated pack {pack}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
