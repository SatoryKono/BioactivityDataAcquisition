"""
Minimal adapter for diagnosing Python/pytest aborts.
Implements Approach B: supervisor with explicit state machine for subprocess
termination and a separate diagnostic sidecar manifest.
"""

import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict


@dataclass
class DiagnosticManifest:
    status: str
    exit_code: int | None
    signal: int | None
    stdout_file: str
    stderr_file: str
    missing_evidence: bool


class PytestAbortDiagnosticAdapter:
    def __init__(self, timeout: int = 60, dump_margin: int = 5):
        self.timeout = timeout
        self.dump_margin = dump_margin

    def run(
        self, cmd: list[str], expected_evidence: Path | None, output_dir: Path
    ) -> DiagnosticManifest:
        output_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = Path(os.path.abspath(str(output_dir / "stdout.log")))
        stderr_path = Path(os.path.abspath(str(output_dir / "stderr.log")))
        manifest_path = Path(
            os.path.abspath(str(output_dir / "diagnostic_manifest.json"))
        )

        # Security: verify files are strictly within output_dir
        if (
            not str(stdout_path).startswith(str(output_dir))
            or not str(stderr_path).startswith(str(output_dir))
            or not str(manifest_path).startswith(str(output_dir))
        ):
            raise ValueError("Invalid output path traversal")

        env = os.environ.copy()
        env["PYTHONFAULTHANDLER"] = "1"

        start_time = time.time()

        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            proc = subprocess.Popen(
                cmd,
                stdout=out,
                stderr=err,
                env=env,
            )

            status = "UNKNOWN"
            exit_code = None
            sig = None

            try:
                proc.wait(timeout=self.timeout)
                exit_code = proc.returncode
                if exit_code == 0:
                    status = "NORMAL_EXIT"
                elif exit_code > 0:
                    status = "NONZERO_EXIT"
                else:
                    status = "SIGNAL_ABORT"
                    sig = -exit_code
            except subprocess.TimeoutExpired:
                status = "WATCHDOG_TIMEOUT"
                # Send SIGABRT to trigger faulthandler dump
                proc.send_signal(signal.SIGABRT)
                try:
                    proc.wait(timeout=self.dump_margin)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                exit_code = proc.returncode
                if exit_code < 0:
                    sig = -exit_code

            missing_evidence = False
            if expected_evidence and not expected_evidence.exists():
                missing_evidence = True

            manifest = DiagnosticManifest(
                status=status,
                exit_code=exit_code,
                signal=sig,
                stdout_file=str(stdout_path),
                stderr_file=str(stderr_path),
                missing_evidence=missing_evidence,
            )

            with open(manifest_path, "w") as f:
                json.dump(asdict(manifest), f, indent=2)

            return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dump-margin", type=int, default=5)
    parser.add_argument("--expected-evidence", type=str, default="")
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    adapter = PytestAbortDiagnosticAdapter(
        timeout=args.timeout, dump_margin=args.dump_margin
    )
    evidence_path = None
    if args.expected_evidence:
        ev_str = args.expected_evidence
        if ".." in ev_str:
            raise ValueError("Invalid evidence path traversal")
        evidence_path = Path(os.path.abspath(ev_str))

    out_dir_str = os.path.basename(args.output_dir)
    out_path = Path.cwd() / "reports" / "pytest_abort_diagnostic" / out_dir_str

    manifest = adapter.run(args.cmd, evidence_path, out_path)
    print(
        f"Diagnostic Manifest: {manifest.status} (exit_code={manifest.exit_code}, signal={manifest.signal})"
    )
    if manifest.missing_evidence:
        print("Warning: Missing expected evidence!")
    sys.exit(
        manifest.exit_code
        if manifest.exit_code is not None and manifest.exit_code > 0
        else 0
    )
