import os
import glob
import re
import json

def read_file_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), f.readlines()
    except Exception:
        return "", []

def grep_files(pattern, files, category, rule, severity):
    issues = []
    regex = re.compile(pattern)
    for f in files:
        if not f.endswith('.py'): continue
        content, lines = read_file_safe(f)
        for i, line in enumerate(lines):
            if regex.search(line) and "TYPE_CHECKING" not in line:
                issues.append({
                    "file": f,
                    "line": i + 1,
                    "category": category,
                    "rule": rule,
                    "severity": severity,
                    "desc": f"Matched pattern '{pattern}'"
                })
    return issues

def scan_sector(sector_id, name, paths):
    files = []
    for p in paths:
        files.extend(glob.glob(p, recursive=True))
    files = [f for f in files if os.path.isfile(f)]

    loc = 0
    for f in files:
        _, lines = read_file_safe(f)
        loc += len(lines)

    issues = []

    if sector_id == "S1":
        # ARCH-002: no I/O in domain
        issues.extend(grep_files(r"import\s+requests|import\s+httpx|open\(|\.read_text|\.write_", files, "Architecture", "ARCH-002", "CRITICAL"))
        # ARCH-001: domain -> infra/app/comp/iface
        issues.extend(grep_files(r"from\s+bioetl\.(infrastructure|application|composition|interfaces)", files, "Architecture", "ARCH-001", "CRITICAL"))
        # AP-002: direct structlog
        issues.extend(grep_files(r"import\s+structlog", files, "Anti-Patterns", "AP-002", "HIGH"))

    if sector_id == "S2":
        # ARCH-001: app -> infra/comp/iface
        issues.extend(grep_files(r"from\s+bioetl\.(infrastructure|composition|interfaces)", files, "Architecture", "ARCH-001", "CRITICAL"))
        # AP-002: direct structlog
        issues.extend(grep_files(r"import\s+structlog", files, "Anti-Patterns", "AP-002", "HIGH"))

    if sector_id == "S3":
        # ARCH-001: infra -> app/comp/iface
        issues.extend(grep_files(r"from\s+bioetl\.(application|composition|interfaces)", files, "Architecture", "ARCH-001", "CRITICAL"))
        # ARCH-006: raw parquet
        issues.extend(grep_files(r"to_parquet|write_parquet", files, "Architecture", "ARCH-006", "CRITICAL"))

    # DI-003: Service Locator
    issues.extend(grep_files(r"ServiceLocator|Container\.resolve|Container\.get", files, "DI Violations", "DI-003", "CRITICAL"))

    # AP-005: Hardcoded secrets
    issues.extend(grep_files(r"(password|api_key|secret)\s*=\s*['\"][^'\"]+['\"]", files, "Anti-Patterns", "AP-005", "CRITICAL"))

    # AP-006: Print statements
    issues.extend(grep_files(r"^\s*print\(", files, "Anti-Patterns", "AP-006", "MEDIUM"))

    return {
        "id": sector_id,
        "name": name,
        "files_count": len(files),
        "loc": loc,
        "issues": issues
    }

sectors = [
    ("S1", "Domain Layer", ["src/bioetl/domain/**/*.py"]),
    ("S2", "Application Layer", ["src/bioetl/application/**/*.py"]),
    ("S3", "Infrastructure Layer", ["src/bioetl/infrastructure/**/*.py"]),
    ("S4", "Composition & Interfaces", ["src/bioetl/composition/**/*.py", "src/bioetl/interfaces/**/*.py"]),
    ("S5", "Cross-cutting Concerns", ["src/bioetl/**/*.py"]),
    ("S6", "Tests", ["tests/**/*.py"]),
    ("S7", "Configs", ["configs/**/*.yaml", "configs/**/*.yml"]),
    ("S8", "Documentation", ["docs/**/*.md"])
]

results = []
for sid, name, paths in sectors:
    res = scan_sector(sid, name, paths)
    # Dedup S5 to only include true cross-cutting issues not already found, but for now just dump it
    results.append(res)

with open("review_data.json", "w") as f:
    json.dump(results, f, indent=2)
