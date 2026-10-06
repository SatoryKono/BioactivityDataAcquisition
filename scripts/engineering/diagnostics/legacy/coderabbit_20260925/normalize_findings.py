"""Normalize CodeRabbit NDJSON leaf logs into a single findings table."""
import json, os, re, sys, glob

OUT = os.path.dirname(os.path.abspath(__file__))


def parse_leaf(path):
    leaf_id = re.search(r"review_(.+)\.jsonl$", os.path.basename(path)).group(1)
    findings = []
    complete = False
    skipped = False
    reviewed = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            t = ev.get("type")
            if t == "finding":
                instr = ev.get("codegenInstructions", "")
                # strip the fixed untrusted-data preamble
                instr = re.sub(
                    r"^Treat finding text.*?validate\.\s*", "", instr,
                    flags=re.S)
                findings.append({
                    "leaf": leaf_id,
                    "severity": ev.get("severity", "unknown"),
                    "path": ev.get("fileName", ""),
                    "claim": instr.strip().replace("\n", " ")[:600],
                })
            elif t == "complete":
                complete = True
                skipped = ev.get("status") == "review_skipped"
                reviewed = ev.get("reviewedFiles", [])
    return leaf_id, findings, complete, skipped, reviewed


def main():
    rows = []
    leaf_status = []
    for p in sorted(glob.glob(os.path.join(OUT, "review_*.jsonl"))):
        lid, finds, complete, skipped, reviewed = parse_leaf(p)
        leaf_status.append({
            "leaf": lid, "complete": complete, "skipped": skipped,
            "findings": len(finds), "reviewed_files": len(reviewed)})
        rows.extend(finds)
    sev_order = {"critical": 0, "major": 1, "minor": 2, "trivial": 3}
    rows.sort(key=lambda r: (sev_order.get(r["severity"], 9), r["path"]))
    with open(os.path.join(OUT, "findings_normalized.jsonl"), "w",
              encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "leaf_status.json"), "w",
              encoding="utf-8") as fh:
        json.dump(leaf_status, fh, indent=1)
    counts = {}
    for r in rows:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1
    print(json.dumps({"total": len(rows), "by_severity": counts,
                      "leaves": leaf_status}, indent=1))


if __name__ == "__main__":
    main()
