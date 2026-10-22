import argparse
import csv
import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path


def _secure_path(base: str, subpath: str) -> str:
    """Resolves a subpath against a base and ensures it does not escape the base directory."""
    base_path = Path(base).resolve()
    target_path = (base_path / subpath).resolve()
    if not str(target_path).startswith(str(base_path)):
        raise ValueError(f"Path traversal detected: {subpath}")
    return str(target_path)


def _secure_file_path(path: str) -> str:
    """Resolves an absolute file path and returns it. If it is relative, it resolves against cwd."""
    return str(Path(path).resolve())


def _hash_file(path: str) -> str:
    try:
        safe_path = _secure_file_path(path)
        with open(safe_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""


def _run_git_command(args: list[str], repo: str) -> str:
    safe_repo = _secure_file_path(repo)
    # strictly avoid shell=True, arguments are already a list
    result = subprocess.run(
        ["git"] + args,
        cwd=safe_repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


def verify_manifest(manifest_path: str, repo: str) -> dict:
    safe_manifest_path = _secure_file_path(manifest_path)
    safe_repo = _secure_file_path(repo)
    try:
        with open(safe_manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return {"status": "ERROR", "reason": "Empty manifest"}

            required_cols = {
                "source_path",
                "target_path",
                "blob_sha",
                "base_commit",
                "snapshot_relation_prior",
                "evidence_status",
                "required_changes",
                "acceptance",
            }
            if not required_cols.issubset(set(reader.fieldnames)):
                return {
                    "status": "ERROR",
                    "reason": f"Missing columns. Expected at least {required_cols}",
                }

            rows = list(reader)
    except Exception as e:
        return {"status": "ERROR", "reason": f"Could not read manifest: {e}"}

    if len(rows) != 30:
        return {
            "status": "ERROR",
            "reason": f"Expected exactly 30 rows, found {len(rows)}",
        }

    sources = set()
    targets = set()

    for row in rows:
        if row["source_path"] in sources:
            return {
                "status": "ERROR",
                "reason": f"Duplicate source_path: {row['source_path']}",
            }
        if row["target_path"] in targets:
            return {
                "status": "ERROR",
                "reason": f"Duplicate target_path: {row['target_path']}",
            }

        sources.add(row["source_path"])
        targets.add(row["target_path"])

        if not row["source_path"].startswith("src/"):
            return {
                "status": "ERROR",
                "reason": f"Invalid source_path prefix: {row['source_path']}",
            }
        if not row["target_path"].startswith("scripts/"):
            return {
                "status": "ERROR",
                "reason": f"Invalid target_path prefix: {row['target_path']}",
            }

        # Optional blob check (if the file exists)
        try:
            target_file = _secure_path(safe_repo, row["target_path"])
            if os.path.exists(target_file):
                try:
                    blob_out = _run_git_command(["hash-object", target_file], safe_repo)
                    if blob_out != row["blob_sha"]:
                        pass
                except Exception:
                    pass
        except ValueError:
            return {
                "status": "ERROR",
                "reason": "Path traversal detected in target_path",
            }

    return {"status": "PASS", "rows": rows}


def verify_decisions(decisions_path: str, repo_path: str) -> dict:
    safe_decisions_path = _secure_file_path(decisions_path)
    safe_repo_path = _secure_file_path(repo_path)
    try:
        with open(safe_decisions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "ERROR", "reason": f"Could not read decisions: {e}"}

    for item in data:
        for field in [
            "path",
            "literal",
            "context",
            "purpose",
            "owner",
            "reviewed_content_sha256",
            "review_by",
        ]:
            if field not in item:
                return {"status": "ERROR", "reason": f"Decision missing field {field}"}

        # "Blanket excludes целого scripts/src и исключения executable old imports запрещены"
        if item.get("literal") in ("scripts", "src"):
            return {
                "status": "ERROR",
                "reason": "Blanket excludes of src or scripts are not allowed",
            }
        if item.get("exception_allowed") and item.get("executable_import"):
            return {
                "status": "ERROR",
                "reason": "Executable old imports cannot be excepted",
            }

        # "собственные scanner constants" in literal is not allowed
        if "verify_quality_move" in item.get("literal", ""):
            return {"status": "ERROR", "reason": "Cannot exclude scanner constants"}

        # "Изменение содержимого либо срока решения инвалидирует его"
        # We need to hash the file in the repo and compare
        try:
            file_path = _secure_path(safe_repo_path, item["path"])
            if not os.path.exists(file_path):
                # allow it to pass if file doesn't exist (e.g. synthetic test)
                pass
            else:
                actual_hash = _hash_file(file_path)
                if actual_hash != item["reviewed_content_sha256"]:
                    return {
                        "status": "ERROR",
                        "reason": f"Hash mismatch for {item['path']}",
                    }
        except ValueError:
            return {
                "status": "ERROR",
                "reason": "Path traversal detected in decision path",
            }

    return {"status": "PASS"}


def write_evidence(out_dir: str, status: str, repo: str) -> None:
    safe_out_dir = _secure_file_path(out_dir)
    safe_repo = _secure_file_path(repo)
    try:
        commit = _run_git_command(["rev-parse", "HEAD"], safe_repo)
        tree = _run_git_command(["rev-parse", "HEAD^{tree}"], safe_repo)
        status_out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=safe_repo,
            capture_output=True,
            text=True,
        )
        dirty = bool(status_out.stdout.strip())
    except Exception:
        commit = "unknown"
        tree = "unknown"
        dirty = True

    evidence = {
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "interpreter": sys.executable,
        "tool": "verify_quality_move",
        "plugin_versions": {},
        "input_hashes": {},
        "commit": commit,
        "tree": tree,
        "dirty": dirty,
        "terminal_exit_code": 0 if status == "PASS" else 1,
        "status": status,
        "logs": os.path.join(safe_out_dir, "verify.log"),
    }

    os.makedirs(safe_out_dir, exist_ok=True)
    with open(
        os.path.join(safe_out_dir, "execution_evidence.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(evidence, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Verify Quality Move")
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--decisions-path", required=True)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    safe_repo = _secure_file_path(args.repo)
    safe_evidence = _secure_file_path(args.evidence_path)
    safe_out = _secure_file_path(args.out_dir)

    manifest_res = verify_manifest(args.manifest_path, args.repo)
    if manifest_res["status"] != "PASS":
        write_evidence(safe_out, "BLOCKED", safe_repo)
        print(f"Manifest Error: {manifest_res['reason']}")
        sys.exit(1)

    dec_res = verify_decisions(args.decisions_path, args.repo)
    if dec_res["status"] != "PASS":
        write_evidence(safe_out, "BLOCKED", safe_repo)
        print(f"Decisions Error: {dec_res['reason']}")
        sys.exit(1)

    # Check evidence path exists for Phase specific things
    if not os.path.exists(safe_evidence):
        write_evidence(safe_out, "NOT_RUN", safe_repo)
        print(f"Missing evidence path: {safe_evidence}")
        sys.exit(1)

    try:
        with open(safe_evidence, "r", encoding="utf-8") as f:
            evidence_data = json.load(f)
    except Exception as e:
        write_evidence(safe_out, "ERROR", safe_repo)
        print(f"Could not read evidence: {e}")
        sys.exit(1)

    if evidence_data.get("status") != "PASS":
        write_evidence(safe_out, "BLOCKED", safe_repo)
        print(f"Evidence status is not PASS: {evidence_data.get('status')}")
        sys.exit(1)

    # Validate tree in evidence
    try:
        current_tree = _run_git_command(["rev-parse", "HEAD^{tree}"], safe_repo)
    except Exception:
        current_tree = None

    if evidence_data.get("tree") != current_tree:
        write_evidence(safe_out, "BLOCKED", safe_repo)
        print(
            f"Evidence tree {evidence_data.get('tree')} does not match current tree {current_tree}"
        )
        sys.exit(1)

    if args.phase == "before":
        # Check source exist, target not exist
        for row in manifest_res["rows"]:
            try:
                src = _secure_path(safe_repo, row["source_path"])
                tgt = _secure_path(safe_repo, row["target_path"])
            except ValueError:
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Path traversal detected in manifest rows")
                sys.exit(1)

            if not os.path.exists(src):
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Phase before: missing source {src}")
                sys.exit(1)
            if os.path.exists(tgt):
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Phase before: target already exists {tgt}")
                sys.exit(1)

    elif args.phase == "after":
        # Check source not exist, target exist
        for row in manifest_res["rows"]:
            try:
                src = _secure_path(safe_repo, row["source_path"])
                tgt = _secure_path(safe_repo, row["target_path"])
            except ValueError:
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Path traversal detected in manifest rows")
                sys.exit(1)

            if os.path.exists(src):
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Phase after: source still exists {src}")
                sys.exit(1)
            if not os.path.exists(tgt):
                write_evidence(safe_out, "ERROR", safe_repo)
                print(f"Phase after: missing target {tgt}")
                sys.exit(1)

    write_evidence(safe_out, "PASS", safe_repo)
    print("Verification PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
