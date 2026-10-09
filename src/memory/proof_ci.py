"""Run each closeout producer once; assemble only transported, verified evidence."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from memory.proof import (
    ReceiptInput,
    assemble_bundle,
    build_receipt,
    canonical_digest,
    discover_context,
    file_digest,
    load_policy,
    load_schema,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "configs/quality/proof_closeout_checks.yaml"
EVIDENCE = ROOT / "reports/quality/proof-or-stop/shared"
EXECUTION_FILE = "execution.json"
PRODUCER_LOG = "producer.log"
SYMLINK_ERROR = "Symlink in producer evidence"


def receive(workspace: Path | None = None) -> None:
    """Copy only proof evidence; classifier workspace files must not dirty checkout."""
    workspace = workspace or Path.home() / ".bioetl-proof-workspace"
    source = workspace / "reports/quality/proof-or-stop/shared"
    if source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Symlink in transported evidence")
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, EVIDENCE)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def catalog() -> dict[str, Any]:
    payload = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Invalid closeout command catalog")
    return payload


def enabled() -> bool:
    lane = os.environ.get("PROOF_CI_LANE", "pr-gate")
    branch = os.environ.get("CIRCLE_BRANCH", "")
    return (lane == "coverage-closeout" and branch == "main") or (
        lane == "pr-gate" and branch in catalog()["branches"]
    )


def ci_identity() -> str:
    """Use workflow identity, never a producer-specific build URL as shared scope."""
    if os.environ.get("CIRCLECI") != "true":
        raise ValueError("CI receipts require a CircleCI execution")
    workflow = os.environ["CIRCLE_WORKFLOW_ID"]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if not workflow or head != os.environ["CIRCLE_SHA1"]:
        raise ValueError("Missing workflow identity or mismatched source SHA")
    if (
        os.environ["CIRCLE_PROJECT_USERNAME"],
        os.environ["CIRCLE_PROJECT_REPONAME"],
    ) != ("SatoryKono", "BioactivityDataAcquisition"):
        raise ValueError("Unexpected CircleCI repository")
    return "circleci-workflow:" + workflow


def command_for(name: str) -> list[str]:
    substitutions = {"out": str(EVIDENCE / name), "root": str(EVIDENCE)}
    return [arg.format(**substitutions) for arg in catalog()["checks"][name]["argv"]]


def _sanitize_file(path: Path, secrets: list[str]) -> None:
    with path.open("r+", encoding="utf-8", errors="replace") as stream:
        original = stream.read()
        text = original
        for secret in secrets:
            text = text.replace(secret, "[REDACTED_CI_SECRET]")
        if text != original:
            stream.seek(0)
            stream.write(text)
            stream.truncate()


def sanitize_outputs(folder: Path) -> None:
    if folder.is_symlink():
        raise ValueError(SYMLINK_ERROR)
    folder = folder.resolve()
    evidence_root = EVIDENCE.resolve()
    evidence_root.relative_to(ROOT.resolve())
    folder.relative_to(evidence_root)
    secrets = sorted(
        {
            v
            for k, v in os.environ.items()
            if len(v) >= 8
            and any(
                part in k.upper()
                for part in ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "ACCESS_KEY")
            )
        },
        key=len,
        reverse=True,
    )
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError(SYMLINK_ERROR)
        path = path.resolve()
        path.relative_to(folder)
        if path.is_file() and path.suffix in {".json", ".xml", ".log"}:
            _sanitize_file(path, secrets)


def artifact_hashes(folder: Path) -> dict[str, str]:
    """Transfer evidence only, excluding interpreter and Hypothesis caches."""
    result = {}
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if any(part in {"pycache", "hypothesis"} for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(SYMLINK_ERROR)
        if path.is_file() and relative.as_posix() != EXECUTION_FILE:
            result[relative.as_posix()] = file_digest(path)
    return result


def executor_elapsed_ms() -> int | None:
    """Return elapsed executor time when the CircleCI start command is present."""
    raw = os.environ.get("BIOETL_CI_JOB_STARTED_EPOCH_MS")
    if raw is None:
        if os.environ.get("CIRCLECI") == "true":
            raise ValueError("Missing proof executor start timestamp")
        return None
    try:
        started_ms = int(raw)
    except ValueError as exc:
        raise ValueError("Invalid proof executor start timestamp") from exc
    elapsed = time.time_ns() // 1_000_000 - started_ms
    if elapsed < 0:
        raise ValueError("Proof executor start timestamp is in the future")
    return elapsed


def produce(name: str) -> int:
    ci_run = ci_identity()
    plan = catalog()
    spec = plan["checks"][name]
    folder = EVIDENCE / name
    folder.mkdir(parents=True, exist_ok=False)
    policy = load_policy()
    repository, source = discover_context(
        ROOT, policy=policy, claim=plan["claim"], ci_run_id=ci_run
    )
    prerequisites = []
    if name == "coverage":
        prerequisites = [key for key in plan["checks"] if key.startswith("coverage-")]
    elif name == "quality":
        prerequisites = ["coverage", "architecture"]
    for prerequisite in prerequisites:
        validate_execution(prerequisite, ci_run, source)
    command = command_for(name)
    started = datetime.now(UTC).isoformat()
    clock = time.monotonic()
    log = folder / PRODUCER_LOG
    env = dict(os.environ)
    env.pop("BASH_ENV", None)
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
        )
        while process.poll() is None:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                print(
                    f"[proof] {name} running {int(time.monotonic() - clock)}s",
                    flush=True,
                )
    duration = round((time.monotonic() - clock) * 1000)
    sanitize_outputs(folder)
    _, after = discover_context(
        ROOT, policy=policy, claim=plan["claim"], ci_run_id=ci_run
    )
    if after != source:
        raise ValueError("Producer changed the bound source tree")
    if "kind" in spec:
        receipt = build_receipt(
            repo_root=ROOT,
            policy=policy,
            task_id=plan["task_id"],
            claim=plan["claim"],
            receipt_input=ReceiptInput(
                receipt_id=name,
                producer=spec["producer"],
                evidence_kind=spec["kind"],
                command=" ".join(command),
                argv=command,
                cwd=str(ROOT),
                started_at=started,
                duration_ms=duration,
                exit_code=process.returncode,
                status="pass" if process.returncode == 0 else "fail",
                output_path=log,
            ),
            trust_tier="ci",
            ci_run_id=ci_run,
        )
        write_json(folder / "receipt.json", receipt)
    write_json(
        folder / EXECUTION_FILE,
        {
            "check": name,
            "catalog_digest": canonical_digest(plan),
            "repository": repository,
            "source": source,
            "argv": command,
            "exit_code": process.returncode,
            "started_at": started,
            "duration_ms": duration,
            "executor_elapsed_ms": executor_elapsed_ms(),
            "job_url": os.environ["CIRCLE_BUILD_URL"],
            "job_id": os.environ["CIRCLE_BUILD_NUM"],
            "artifacts": artifact_hashes(folder),
        },
    )
    print(f"[proof] {name} exit={process.returncode}", flush=True)
    return process.returncode


def validate_execution(
    name: str, ci_run: str, source: dict[str, Any]
) -> dict[str, Any]:
    folder = EVIDENCE / name
    record = json.loads((folder / EXECUTION_FILE).read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid producer execution record")
    if (
        record["check"] != name
        or record["catalog_digest"] != canonical_digest(catalog())
        or record["repository"]["ci_run_id"] != ci_run
        or record["source"] != source
        or record["exit_code"] != 0
        or record["argv"] != command_for(name)
    ):
        raise ValueError(f"Incomplete or foreign producer: {name}")
    if (
        record["artifacts"] != artifact_hashes(folder)
        or PRODUCER_LOG not in record["artifacts"]
    ):
        raise ValueError(f"Producer artifact mismatch: {name}")
    return record


def assemble() -> int:
    """No subprocess producers here: fail closed if transported evidence is incomplete."""
    from scripts.engineering.ci.closeout_cost_budget import (
        evaluate_closeout_cost_budget,
    )

    ci_run = ci_identity()
    plan = catalog()
    policy = load_policy()
    _, source = discover_context(
        ROOT, policy=policy, claim=plan["claim"], ci_run_id=ci_run
    )
    cost_budget = evaluate_closeout_cost_budget(ROOT)
    write_json(EVIDENCE / "closeout/cost-budget.json", cost_budget)
    if cost_budget["outcome"] != "PASS":
        raise ValueError("CI cost budget failed: " + ", ".join(cost_budget["errors"]))
    receipts = []
    executions: dict[str, dict[str, Any]] = {}
    coverage_producer_seconds: dict[str, float] = {}
    for name, spec in plan["checks"].items():
        execution = validate_execution(name, ci_run, source)
        executions[name] = execution
        if name.startswith("coverage-"):
            coverage_producer_seconds[name] = round(
                float(execution["duration_ms"]) / 1000, 3
            )
        if "kind" in spec:
            receipt = json.loads(
                (EVIDENCE / name / "receipt.json").read_text(encoding="utf-8")
            )
            if (
                receipt["receipt_id"] != name
                or receipt["argv"] != command_for(name)
                or receipt["producer"] != spec["producer"]
                or receipt["evidence_kind"] != spec["kind"]
                or receipt["output_digest"]
                != file_digest(EVIDENCE / name / PRODUCER_LOG)
            ):
                raise ValueError(f"Receipt does not describe producer: {name}")
            receipts.append(receipt)
    cost_budget["observed_coverage_producer_seconds"] = coverage_producer_seconds
    cost_budget["observed_coverage_producer_total_seconds"] = round(
        sum(coverage_producer_seconds.values()), 3
    )
    executor_seconds: dict[str, float] = {}
    missing_executor_measurements: list[str] = []
    for name, execution in executions.items():
        elapsed = execution.get("executor_elapsed_ms")
        if elapsed is None:
            missing_executor_measurements.append(name)
            continue
        job_id = str(execution["job_id"])
        executor_seconds[job_id] = max(
            executor_seconds.get(job_id, 0.0), round(float(elapsed) / 1000, 3)
        )
    closeout_elapsed = executor_elapsed_ms()
    if closeout_elapsed is not None:
        executor_seconds[str(os.environ["CIRCLE_BUILD_NUM"])] = round(
            closeout_elapsed / 1000, 3
        )
    cost_budget["observed_executor_seconds_by_job"] = executor_seconds
    cost_budget["observed_executor_total_seconds"] = round(
        sum(executor_seconds.values()), 3
    )
    cost_budget["missing_executor_measurements"] = sorted(missing_executor_measurements)
    write_json(EVIDENCE / "closeout/cost-budget.json", cost_budget)
    from scripts.engineering.ci.local_test_telemetry import validate_local_measurement
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        compute_test_telemetry_source_tree_sha256,
    )
    from scripts.engineering.qa.report_module_coverage_inventory import (
        compute_source_tree_sha256,
    )

    manifest = EVIDENCE / "coverage/coverage/manifest.json"
    coverage = json.loads(manifest.read_text(encoding="utf-8"))
    if coverage["head"] != source["head_sha"]:
        raise ValueError("Coverage belongs to another SHA")
    validate_local_measurement(
        manifest,
        repo_root=ROOT,
        test_tree_sha256=compute_test_telemetry_source_tree_sha256(repo_root=ROOT),
        source_tree_sha256=compute_source_tree_sha256(repo_root=ROOT),
    )
    bundle = assemble_bundle(
        repo_root=ROOT,
        policy=policy,
        run_id=ci_run,
        task_id=plan["task_id"],
        claim=plan["claim"],
        actor="circleci",
        runtime="ci",
        trust_tier="ci",
        receipts=receipts,
        ci_run_id=ci_run,
    )
    result = verify_bundle(
        bundle=bundle, repo_root=ROOT, policy=policy, schema=load_schema()
    )
    write_json(EVIDENCE / "closeout/bundle.json", bundle)
    write_json(EVIDENCE / "closeout/verification.json", result.to_dict())
    print(json.dumps(result.to_dict()))
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["enabled", "receive", "produce", "validate", "assemble"]
    )
    parser.add_argument("--check", choices=list(catalog()["checks"]))
    args = parser.parse_args(argv)
    if args.action == "enabled":
        return 0 if enabled() else 1
    try:
        if args.action == "receive":
            receive()
            return 0
        if args.action == "validate":
            if not args.check:
                parser.error("validate requires --check")
            ci_run = ci_identity()
            _, source = discover_context(
                ROOT, policy=load_policy(), claim=catalog()["claim"], ci_run_id=ci_run
            )
            validate_execution(args.check, ci_run, source)
            return 0
        if args.action == "produce":
            if not args.check:
                parser.error("produce requires --check")
            return produce(args.check)
        return assemble()
    except (ValueError, KeyError, OSError) as exc:
        if args.action == "assemble":
            write_json(
                EVIDENCE / "closeout/verification.json",
                {
                    "schema_version": 1,
                    "outcome": "STOP",
                    "claim_qualified": False,
                    "errors": [str(exc)],
                    "degradations": [],
                    "exit_code": 2,
                },
            )
        print(f"[proof] STOP: {exc}")
        return 2
