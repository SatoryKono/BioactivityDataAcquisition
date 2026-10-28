import subprocess
import time

lanes = {
    "architecture": [
        "uv",
        "run",
        "python",
        "-m",
        "scripts.engineering.ci.run_pytest_resilient",
        "--target",
        "tests/architecture",
        "--reports-dir",
        "reports/quality/arch_bench",
        "--receipt-run-id",
        "arch_bench",
        "--receipt-attempt",
        "1",
        "--parallel-marker",
        "not slow and not benchmark and not memory and not serial",
        "--serial-marker",
        "serial and not slow and not benchmark and not memory",
        "--fallback-addopts",
        "-p no:xdist -q --tb=line --ignore-glob=tests/architecture/test_diagram*.py --ignore=tests/architecture/test_check_diagram_visual_smoke.py --ignore=tests/architecture/test_run_diagram_checks_script.py --ignore=tests/architecture/test_validate_mermaid_syntax_script.py",
        "--serial-addopts",
        "-p no:xdist -q --tb=line --ignore-glob=tests/architecture/test_diagram*.py --ignore=tests/architecture/test_check_diagram_visual_smoke.py --ignore=tests/architecture/test_run_diagram_checks_script.py --ignore=tests/architecture/test_validate_mermaid_syntax_script.py",
    ],
    "affected": [
        "uv",
        "run",
        "python",
        "-m",
        "scripts.engineering.ci.run_pytest_resilient",
        "--target",
        "tests/unit/domain",
        "--reports-dir",
        "reports/quality/aff_bench",
        "--receipt-run-id",
        "aff_bench",
        "--receipt-attempt",
        "1",
        "--parallel-marker",
        "not serial",
        "--serial-marker",
        "serial",
        "--fallback-addopts",
        "-p no:xdist -q --tb=line",
        "--serial-addopts",
        "-p no:xdist -q --tb=line",
    ],
}

configs = [
    ("-n 0", "-p no:xdist -q --tb=line"),
    ("-n 2 loadscope", "-n 2 --dist loadscope -q --tb=line"),
    ("-n 2 loadfile", "-n 2 --dist loadfile -q --tb=line"),
    ("-n 4 loadscope", "-n 4 --dist loadscope -q --tb=line"),
    ("-n 4 loadfile", "-n 4 --dist loadfile -q --tb=line"),
    ("-n auto loadscope", "-n auto --dist loadscope -q --tb=line"),
    ("-n auto loadfile", "-n auto --dist loadfile -q --tb=line"),
]

runs = 3

for lane_name, base_cmd in lanes.items():
    for conf_name, conf_opts in configs:
        for run_idx in range(runs):
            addopts = conf_opts
            if lane_name == "architecture":
                addopts += " --ignore-glob=tests/architecture/test_diagram*.py --ignore=tests/architecture/test_check_diagram_visual_smoke.py --ignore=tests/architecture/test_run_diagram_checks_script.py --ignore=tests/architecture/test_validate_mermaid_syntax_script.py"

            cmd = base_cmd + ["--parallel-addopts", addopts, "--no-fallback"]

            print(f"Running cmd: {' '.join(cmd)}")
            start_time = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True)
            end_time = time.time()
            wall_clock = end_time - start_time
            with open("reports/epoch2208/b/bench_results.txt", "a") as f:
                f.write(
                    f"{lane_name} | {conf_name} | Run {run_idx + 1} | {wall_clock:.2f}s | Exit: {proc.returncode}\n"
                )
