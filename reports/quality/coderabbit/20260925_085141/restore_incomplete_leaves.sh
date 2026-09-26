#!/usr/bin/env bash
# Restore incomplete CodeRabbit leaves from 20260925_085141 campaign.
# Run in WSL: bash reports/quality/coderabbit/20260925_085141/restore_incomplete_leaves.sh
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export NO_COLOR=1
export TERM=dumb

REPO_WIN="/mnt/e/github/BioactivityDataAcquisition"
if [[ ! -d "$REPO_WIN/.git" ]]; then
  REPO_WIN="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
cd "$REPO_WIN" || exit 1

SRC_AUDIT="$REPO_WIN/reports/quality/coderabbit/20260925_085141"
OUT="$REPO_WIN/reports/quality/coderabbit/20260926_restore"
MATRIX="$SRC_AUDIT/scope_matrix.json"
LOGS="$OUT/logs"
mkdir -p "$LOGS" "$OUT"
PROGRESS="$OUT/progress.json"
WT="/tmp/bioetl-cr-restore-wt"
MAIN_SHA="$(git -C "$REPO_WIN" rev-parse HEAD)"
CR_SLEEP="${CR_SLEEP:-12}"
CR_TIMEOUT="${CR_TIMEOUT:-900}"
CR_LIGHT="${CR_LIGHT:-1}"

# Incomplete / failed leaves from 20260925 campaign
DEFAULT_LEAVES="S03-infra-adapters,S05-interfaces,S06a-tests-architecture,S06b-tests-architecture,S07-configs-quality,S08a-docs-00-project,S08b-docs-decisions"
CR_LEAVES="${CR_LEAVES:-$DEFAULT_LEAVES}"

if ! command -v coderabbit >/dev/null; then
  echo "coderabbit not found in PATH" >&2
  exit 2
fi

echo "coderabbit=$(coderabbit --version 2>/dev/null || true)"
echo "MAIN_SHA=$MAIN_SHA"
echo "OUT=$OUT"
echo "LEAVES=$CR_LEAVES"

# Load API key from repo .env without sourcing (python)
if [[ -z "${CODERABBIT_API_KEY:-}" && -f "$REPO_WIN/.env" ]]; then
  CODERABBIT_API_KEY="$(python3 - <<'PY' "$REPO_WIN/.env"
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    s=line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k,v=s.split("=",1)
    if k.strip()=="CODERABBIT_API_KEY":
        print(v.strip().strip('"').strip("'"))
        break
PY
)"
  export CODERABBIT_API_KEY
fi

light_flag=()
if [[ "$CR_LIGHT" == "1" ]]; then
  light_flag=(--light)
fi

PLAN_JSON="$OUT/_run_plan.json"
python3 - <<'PY' "$MATRIX" "$PLAN_JSON" "$CR_LEAVES" "$SRC_AUDIT"
import json, sys
from pathlib import Path
matrix_path, plan_path, leaves_s, src_audit = sys.argv[1:5]
matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
want = set(leaves_s.split(","))
leaves = []
for L in matrix["leaves"]:
    lid = L["leaf_id"]
    if lid not in want:
        continue
    paths_file = Path(src_audit) / "leaves" / f"{lid}.paths"
    files = L.get("files") or []
    if paths_file.exists() and not files:
        files = [ln.strip() for ln in paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # derive dir from selection when possible
    sel = L.get("selection") or []
    dirp = ""
    if sel and isinstance(sel[0], str) and not sel[0].endswith(")"):
        # e.g. tests/architecture (1/2) -> skip dir, use file list
        if "(" not in sel[0]:
            dirp = sel[0]
    leaves.append({
        "id": lid,
        "dir": dirp,
        "files": files,
        "file_count": len(files),
        "selection": sel,
    })
Path(plan_path).write_text(json.dumps(leaves, indent=2), encoding="utf-8")
print(f"plan_leaves={len(leaves)}")
for x in leaves:
    print(f"  {x['id']} files={x['file_count']} dir={x['dir']!r}")
PY

if [[ ! -f "$PROGRESS" ]]; then
  echo '{"results":{}}' > "$PROGRESS"
fi

# Prepare orphan worktree
if [[ -d "$WT" ]]; then
  git -C "$REPO_WIN" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
fi
git -C "$REPO_WIN" worktree add --detach "$WT" "$MAIN_SHA"
cd "$WT" || exit 1
git checkout --orphan "cr-restore-empty-base" >/dev/null 2>&1 || true
git rm -rf . >/dev/null 2>&1 || true
git commit --allow-empty -m "empty base for CR restore" >/dev/null
EMPTY_SHA="$(git rev-parse HEAD)"
echo "EMPTY_SHA=$EMPTY_SHA WT=$WT"

n_total=$(python3 -c "import json;print(len(json.load(open('$PLAN_JSON'))))")
idx=0
while IFS= read -r leaf_json; do
  idx=$((idx+1))
  lid=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  dirp=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dir') or '')")
  files_n=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_count',0))")

  already=$(python3 -c "import json; d=json.load(open('$PROGRESS')); r=d.get('results',{}).get('$lid',{}); print(r.get('status',''))")
  if [[ "$already" == "ok" ]]; then
    echo "[$idx/$n_total] SKIP $lid (already ok)"
    continue
  fi

  echo "[$idx/$n_total] RUN $lid files=$files_n dir=$dirp"
  log="$LOGS/review_${lid}.jsonl"
  : >"$log"

  git checkout -f "cr-restore-empty-base" >/dev/null 2>&1
  git clean -fdx >/dev/null 2>&1
  git checkout -B "cr-leaf-$lid" "cr-restore-empty-base" >/dev/null 2>&1

  status="ok"
  reason=""
  findings=0
  review_dir="."
  if [[ -n "$dirp" ]]; then
    if ! git checkout "$MAIN_SHA" -- "$dirp" 2>/tmp/cr_co.err; then
      status="error"
      reason="checkout_dir_failed"
      cat /tmp/cr_co.err >>"$log" || true
    fi
    review_dir="$dirp"
  else
    # checkout explicit file list from plan
    python3 - <<'PY' "$PLAN_JSON" "$lid" "$MAIN_SHA"
import json, subprocess, sys
from pathlib import Path
plan=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lid=sys.argv[2]
sha=sys.argv[3]
leaf=next(x for x in plan if x["id"]==lid)
files=leaf.get("files") or []
if not files:
    raise SystemExit("no files")
# batch checkout
chunk=80
for i in range(0,len(files),chunk):
    batch=files[i:i+chunk]
    subprocess.run(["git","checkout",sha,"--",*batch], check=False)
print(f"checked_out={len(files)}")
PY
    if [[ $? -ne 0 ]]; then
      status="error"
      reason="checkout_files_failed"
    else
      review_dir=$(python3 - <<'PY' "$PLAN_JSON" "$lid"
import json,sys
from pathlib import Path
plan=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lid=sys.argv[2]
files=next(x for x in plan if x["id"]==lid).get("files") or ["."]
parts=[f.replace("\\","/").split("/") for f in files]
common=[]
for segs in zip(*parts):
    if len(set(segs))==1:
        common.append(segs[0])
    else:
        break
print("/".join(common) if common else ".")
PY
)
    fi
  fi

  if [[ "$status" == "ok" ]]; then
    git add -A >/dev/null 2>&1 || true
    if git diff --cached --quiet; then
      status="skipped"
      reason="no_files_checked_out"
    else
      git -c user.email=cr@local -c user.name=cr commit -m "leaf $lid" >/dev/null 2>&1 || true
      set +e
      timeout --signal=TERM --kill-after=30 "$CR_TIMEOUT" \
        coderabbit review --agent "${light_flag[@]}" --base-commit="$EMPTY_SHA" --dir "$review_dir" \
        >"$log" 2>"$LOGS/review_${lid}.stderr.txt"
      rc=$?
      set -e
      findings=$(python3 -c "import json; n=0
import pathlib
p=pathlib.Path('$log')
for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
  try:
    o=json.loads(line)
  except Exception:
    continue
  if o.get('type')=='finding': n+=1
print(n)")
      # detect failures
      if grep -q '"type":"error"' "$log" 2>/dev/null || grep -q 'Rate limit exceeded' "$LOGS/review_${lid}.stderr.txt" 2>/dev/null; then
        status="error"
        reason="coderabbit_error"
      elif grep -q 'All files are ignored' "$log" 2>/dev/null || grep -q 'All files are ignored' "$LOGS/review_${lid}.stderr.txt" 2>/dev/null; then
        status="ignored"
        reason="all_files_ignored"
      elif [[ "$rc" -ne 0 && "$findings" -eq 0 ]]; then
        status="error"
        reason="rc_$rc"
      else
        status="ok"
        reason="findings=$findings"
      fi
      # also copy into original audit dir for continuity
      cp -f "$log" "$SRC_AUDIT/review_${lid}.jsonl" 2>/dev/null || true
      cp -f "$LOGS/review_${lid}.stderr.txt" "$SRC_AUDIT/review_${lid}.stderr.txt" 2>/dev/null || true
    fi
  fi

  python3 - <<'PY' "$PROGRESS" "$lid" "$status" "$reason" "$files_n" "$findings"
import json,sys,datetime
from pathlib import Path
prog_path, lid, status, reason, files_n, findings = sys.argv[1:7]
data=json.loads(Path(prog_path).read_text(encoding="utf-8"))
data.setdefault("results",{})[lid]={
  "status": status,
  "reason": reason,
  "files": int(files_n),
  "findings": int(findings) if str(findings).isdigit() else findings,
  "at": datetime.datetime.utcnow().isoformat()+"Z",
}
Path(prog_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"RESULT {lid} status={status} reason={reason}")
PY

  # update state.json ok list on success
  if [[ "$status" == "ok" ]]; then
    python3 - <<'PY' "$SRC_AUDIT/state.json" "$lid"
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); lid=sys.argv[2]
data=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"ok":[]}
ok=list(data.get("ok") or [])
if lid not in ok:
    ok.append(lid)
data["ok"]=ok
p.write_text(json.dumps(data), encoding="utf-8")
PY
  fi

  echo "sleep ${CR_SLEEP}s"
  sleep "$CR_SLEEP"
done < <(python3 -c "import json; [print(json.dumps(x)) for x in json.load(open('$PLAN_JSON'))]")

echo "=== restore finished ==="
python3 -c "import json;print(json.dumps(json.load(open('$PROGRESS')),indent=2))"
