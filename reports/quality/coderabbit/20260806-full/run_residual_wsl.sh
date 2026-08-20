#!/usr/bin/env bash
# Sequential residual CodeRabbit reviews via orphan empty-base worktree.
# Usage (WSL):
#   bash reports/quality/coderabbit/20260806-full/run_residual_wsl.sh
# Env:
#   CR_WAVE=A|B|C|...   CR_MAX_LEAVES=N   CR_SLEEP=5   CR_LIGHT=1
#   CR_LEAVES=id1,id2   CR_TIMEOUT=600
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export NO_COLOR=1
export TERM=dumb

REPO_WIN="/mnt/e/github/BioactivityDataAcquisition"
if [[ ! -d "$REPO_WIN/.git" ]]; then
  REPO_WIN="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
cd "$REPO_WIN" || exit 1

OUT="$REPO_WIN/reports/quality/coderabbit/20260806-full"
MATRIX="$OUT/01-scope-matrix.json"
LOGS="$OUT/logs"
mkdir -p "$LOGS"
PROGRESS="$OUT/progress.json"
WT="/tmp/bioetl-cr-full-wt"
MAIN_SHA="$(git rev-parse HEAD)"
CR_SLEEP="${CR_SLEEP:-8}"
CR_TIMEOUT="${CR_TIMEOUT:-600}"
CR_LIGHT="${CR_LIGHT:-1}"
CR_MAX_LEAVES="${CR_MAX_LEAVES:-0}"
CR_WAVE="${CR_WAVE:-}"
CR_LEAVES="${CR_LEAVES:-}"
SKIPPED_STATUS="skipped"

if ! command -v coderabbit >/dev/null; then
  echo "coderabbit not found" >&2
  exit 2
fi
if ! command -v python3 >/dev/null; then
  PYTHON=python3
else
  PYTHON=python3
fi
# WSL may have python3
command -v python3 >/dev/null || PYTHON=python

light_flag=()
if [[ "$CR_LIGHT" == "1" ]]; then
  light_flag=(--light)
fi

# Build leaf plan as JSON lines via python
PLAN_JSON="$OUT/_run_plan.json"
python3 - <<'PY' "$MATRIX" "$PLAN_JSON" "$CR_WAVE" "$CR_LEAVES" "$CR_MAX_LEAVES"
import json, sys
from pathlib import Path
matrix_path, plan_path, wave, leaves_s, max_s = sys.argv[1:6]
matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
leaves = matrix["leaves"]
wave_order = {"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"R":6}
if wave:
    leaves = [L for L in leaves if L.get("wave")==wave]
if leaves_s:
    want=set(leaves_s.split(","))
    leaves=[L for L in leaves if L["id"] in want]
leaves=sorted(leaves, key=lambda L: (wave_order.get(L.get("wave"),9), L["id"]))
max_n=int(max_s or 0)
if max_n>0:
    leaves=leaves[:max_n]
Path(plan_path).write_text(json.dumps(leaves, indent=2), encoding="utf-8")
print(f"plan_leaves={len(leaves)}")
PY

# Prepare worktree once
if [[ -d "$WT" ]]; then
  git -C "$REPO_WIN" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
fi
git worktree add --detach "$WT" "$MAIN_SHA"
cd "$WT" || exit 1
git checkout --orphan "cr-full-empty-base" >/dev/null 2>&1 || true
git rm -rf . >/dev/null 2>&1 || true
git commit --allow-empty -m "empty base for residual CR-FULL" >/dev/null
EMPTY_SHA="$(git rev-parse HEAD)"
echo "EMPTY_SHA=$EMPTY_SHA MAIN_SHA=$MAIN_SHA WT=$WT"

# progress helpers
if [[ ! -f "$PROGRESS" ]]; then
  echo '{"results":{}}' > "$PROGRESS"
fi

n_total=$(python3 -c "import json;print(len(json.load(open('$PLAN_JSON'))))")
idx=0
while IFS= read -r leaf_json; do
  idx=$((idx+1))
  lid=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  wave=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('wave',''))")
  dirp=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dir') or '')")
  flist=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('use_file_list') or '')")
  files_n=$(echo "$leaf_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('files',0))")

  # skip if already ok
  already=$(python3 -c "import json; d=json.load(open('$PROGRESS')); r=d.get('results',{}).get('$lid',{}); print(r.get('status',''))")
  if [[ "$already" == "ok" || "$already" == "ignored" ]]; then
    echo "[$idx/$n_total] SKIP $lid ($already)"
    continue
  fi

  echo "[$idx/$n_total] RUN $lid wave=$wave files=$files_n dir=$dirp"
  log="$LOGS/review_${lid}.jsonl"
  # reset to empty base
  git checkout -f "cr-full-empty-base" >/dev/null 2>&1
  git clean -fdx >/dev/null 2>&1
  git checkout -B "cr-leaf-$lid" "cr-full-empty-base" >/dev/null 2>&1

  # populate files from main
  status="ok"
  reason=""
  if [[ -n "$dirp" ]]; then
    if ! git checkout "$MAIN_SHA" -- "$dirp" 2>/tmp/cr_co.err; then
      status="error"
      reason="checkout_dir_failed"
      cat /tmp/cr_co.err >> "$log" 2>/dev/null || true
    fi
    review_dir="$dirp"
  elif [[ -n "$flist" ]]; then
    # file list may be Windows path — map
    flist_wsl="$flist"
    if [[ "$flist" == E:/* || "$flist" == e:/* ]]; then
      flist_wsl="/mnt/e/${flist:3}"
      flist_wsl="${flist_wsl//\\//}"
    elif [[ "$flist" == reports/* ]]; then
      flist_wsl="$REPO_WIN/$flist"
    fi
    if [[ ! -f "$flist_wsl" ]]; then
      # try relative from repo
      flist_wsl="$REPO_WIN/${flist#*20260806-full/}"
      if [[ ! -f "$flist_wsl" ]]; then
        flist_wsl="$OUT/$(basename "$flist")"
      fi
    fi
    if [[ ! -f "$flist_wsl" ]]; then
      status="$SKIPPED_STATUS"
      reason="missing_file_list:$flist"
      review_dir=""
    else
      mapfile -t files < <(grep -v '^$' "$flist_wsl" || true)
      if [[ ${#files[@]} -eq 0 ]]; then
        status="$SKIPPED_STATUS"
        reason="empty_file_list"
        review_dir=""
      else
        # checkout files; ignore missing
        printf '%s\0' "${files[@]}" | xargs -0 -r git checkout "$MAIN_SHA" -- 2>/tmp/cr_co.err || true
        # common dir for --dir
        review_dir=$(python3 - <<'PY' "${files[@]}"
import os,sys
files=sys.argv[1:]
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
  else
    status="$SKIPPED_STATUS"
    reason="no_dir_or_list"
    review_dir=""
  fi

  if [[ "$status" == "ok" ]]; then
    git add -A >/dev/null 2>&1 || true
    if git diff --cached --quiet; then
      status="$SKIPPED_STATUS"
      reason="no_files_checked_out"
    else
      git commit -m "residual leaf $lid" >/dev/null 2>&1 || true
    fi
  fi

  if [[ "$status" == "ok" ]]; then
    set +e
    timeout "$CR_TIMEOUT" coderabbit review \
      --base-commit="$EMPTY_SHA" \
      --dir "${review_dir:-.}" \
      --agent \
      "${light_flag[@]}" \
      >"$log" 2>"$LOGS/review_${lid}.err"
    ec=$?
    set -e
    if [[ $ec -eq 124 ]]; then
      status="timeout"
      reason="timeout_${CR_TIMEOUT}s"
    elif [[ $ec -ne 0 ]]; then
      status="error"
      reason="exit_$ec"
    fi
    # detect rate limit / ignored
    if grep -qi 'rate.limit\|rate_limit' "$log" "$LOGS/review_${lid}.err" 2>/dev/null; then
      status="rate_limit"
      reason="rate_limit"
    fi
    if grep -qi 'all files ignored' "$log" "$LOGS/review_${lid}.err" 2>/dev/null; then
      status="ignored"
      reason="all_files_ignored"
    fi
    # count findings
    fcount=$(grep -c '"type":"finding"' "$log" 2>/dev/null || echo 0)
  else
    fcount=0
    echo "{\"type\":\"status\",\"status\":\"$status\",\"reason\":\"$reason\"}" >"$log"
  fi

  python3 - <<PY
import json
from pathlib import Path
from datetime import datetime, timezone
p=Path("$PROGRESS")
d=json.loads(p.read_text(encoding="utf-8"))
d.setdefault("results",{})["$lid"]={
  "id":"$lid",
  "wave":"$wave",
  "status":"$status",
  "reason":"$reason",
  "findings": int("$fcount" or 0),
  "log":"$log",
  "review_dir":"$review_dir",
  "updated": datetime.now(timezone.utc).isoformat(),
}
p.write_text(json.dumps(d, indent=2), encoding="utf-8")
print(f"  -> $status findings=$fcount reason=$reason")
PY

  if [[ "$status" == "rate_limit" ]]; then
    echo "rate_limit — sleep 120s then continue"
    sleep 120
  else
    sleep "$CR_SLEEP"
  fi
done < <(python3 -c "import json; [print(json.dumps(x)) for x in json.load(open('$PLAN_JSON'))]")

echo "DONE plan"
python3 - <<PY
import json
from collections import Counter
from pathlib import Path
d=json.loads(Path("$PROGRESS").read_text(encoding="utf-8"))
c=Counter(r.get("status") for r in d.get("results",{}).values())
print("SUMMARY", dict(c))
print("total_findings", sum(r.get("findings",0) for r in d.get("results",{}).values()))
Path("$OUT/run_summary.json").write_text(json.dumps({"counts":dict(c),"results":d.get("results",{})}, indent=2), encoding="utf-8")
PY
