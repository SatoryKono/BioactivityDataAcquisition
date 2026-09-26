#!/usr/bin/env bash
# Restore incomplete CodeRabbit leaves from 20260925_085141.
# WSL: bash reports/quality/coderabbit/20260926_restore/run.sh
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export NO_COLOR=1
export TERM=dumb

REPO_WIN="/mnt/e/github/BioactivityDataAcquisition"
SRC_AUDIT="$REPO_WIN/reports/quality/coderabbit/20260925_085141"
OUT="$REPO_WIN/reports/quality/coderabbit/20260926_restore"
MATRIX="$SRC_AUDIT/scope_matrix.json"
LOGS="$OUT/logs"
PROGRESS="$OUT/progress.json"
MIRROR="${BIOETL_CR_MIRROR:-$HOME/bioetl-cr-restore-src}"
WT="${BIOETL_CR_WT:-$HOME/bioetl-cr-restore-wt}"
CR_SLEEP="${CR_SLEEP:-12}"
CR_TIMEOUT="${CR_TIMEOUT:-900}"
CR_LIGHT="${CR_LIGHT:-1}"
CR_LEAVES="${CR_LEAVES:-S03-infra-adapters,S05-interfaces,S06a-tests-architecture,S06b-tests-architecture,S07-configs-quality,S08a-docs-00-project,S08b-docs-decisions}"

mkdir -p "$LOGS" "$OUT"
command -v coderabbit >/dev/null || { echo "coderabbit missing"; exit 2; }

if [[ -z "${CODERABBIT_API_KEY:-}" && -f "$REPO_WIN/.env" ]]; then
  CODERABBIT_API_KEY="$(python3 - <<'PY' "$REPO_WIN/.env"
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    s=line.strip()
    if s.startswith("CODERABBIT_API_KEY="):
        print(s.split("=",1)[1].strip().strip('"').strip("'"))
        break
PY
)"
  export CODERABBIT_API_KEY
fi

if [[ ! -d "$MIRROR/.git" ]]; then
  echo "clone mirror..."
  git clone --shared "$REPO_WIN" "$MIRROR" || git clone "$REPO_WIN" "$MIRROR"
fi
cd "$MIRROR" || exit 1
MAIN_SHA="$(git -C "$REPO_WIN" rev-parse HEAD)"
git fetch --all --tags >/dev/null 2>&1 || true
git checkout -f "$MAIN_SHA" >/dev/null 2>&1 || true
REPO="$MIRROR"

light_flag=()
[[ "$CR_LIGHT" == "1" ]] && light_flag=(--light)

python3 - <<'PY' "$MATRIX" "$OUT/_run_plan.json" "$CR_LEAVES" "$SRC_AUDIT"
import json, sys
from pathlib import Path
matrix = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
want = set(sys.argv[3].split(","))
src = Path(sys.argv[4])
leaves = []
for L in matrix["leaves"]:
    lid = L["leaf_id"]
    if lid not in want:
        continue
    files = L.get("files") or []
    pf = src / "leaves" / f"{lid}.paths"
    if pf.exists() and not files:
        files = [x.strip() for x in pf.read_text(encoding="utf-8").splitlines() if x.strip()]
    sel = L.get("selection") or []
    dirp = ""
    if sel and isinstance(sel[0], str) and "(" not in sel[0]:
        dirp = sel[0]
    leaves.append({"id": lid, "dir": dirp, "files": files, "file_count": len(files)})
Path(sys.argv[2]).write_text(json.dumps(leaves, indent=2), encoding="utf-8")
print("plan_leaves", len(leaves))
for x in leaves:
    print(" ", x["id"], x["file_count"], x["dir"])
PY

[[ -f "$PROGRESS" ]] || echo '{"results":{}}' >"$PROGRESS"

if [[ -d "$WT" ]]; then
  git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
fi
git -C "$REPO" worktree prune >/dev/null 2>&1 || true
rm -rf "$WT"
git -C "$REPO" worktree add --detach -f "$WT" "$MAIN_SHA"
cd "$WT" || exit 1
git checkout --orphan cr-restore-empty-base >/dev/null 2>&1 || true
git rm -rf . >/dev/null 2>&1 || true
git -c user.email=cr-restore@local -c user.name=cr-restore commit --allow-empty -m "empty base" >/dev/null
EMPTY_SHA="$(git rev-parse HEAD)"
echo "EMPTY_SHA=$EMPTY_SHA MAIN_SHA=$MAIN_SHA"

while IFS= read -r leaf_json; do
  lid=$(python3 -c "import sys,json;print(json.load(sys.stdin)['id'])" <<<"$leaf_json")
  dirp=$(python3 -c "import sys,json;print(json.load(sys.stdin).get('dir') or '')" <<<"$leaf_json")
  files_n=$(python3 -c "import sys,json;print(json.load(sys.stdin).get('file_count',0))" <<<"$leaf_json")
  already=$(python3 -c "import json;print(json.load(open('$PROGRESS')).get('results',{}).get('$lid',{}).get('status',''))")
  [[ "$already" == "ok" ]] && { echo "SKIP $lid"; continue; }

  echo "RUN $lid files=$files_n dir=$dirp"
  log="$LOGS/review_${lid}.jsonl"
  : >"$log"
  findings=0
  status=ok
  reason=""

  git checkout -f cr-restore-empty-base >/dev/null 2>&1
  git clean -fdx >/dev/null 2>&1
  git checkout -B "cr-leaf-$lid" cr-restore-empty-base >/dev/null 2>&1

  if [[ -n "$dirp" ]]; then
    git checkout "$MAIN_SHA" -- "$dirp" || { status=error; reason=checkout_dir; }
    review_dir="$dirp"
  else
    python3 - <<'PY' "$OUT/_run_plan.json" "$lid" "$MAIN_SHA"
import json, subprocess, sys
from pathlib import Path
leaf=next(x for x in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if x["id"]==sys.argv[2])
files=leaf["files"]
for i in range(0,len(files),80):
    subprocess.run(["git","checkout",sys.argv[3],"--",*files[i:i+80]], check=False)
print(len(files))
PY
    review_dir=$(python3 - <<'PY' "$OUT/_run_plan.json" "$lid"
import json,sys
from pathlib import Path
files=next(x for x in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if x["id"]==sys.argv[2])["files"]
parts=[f.split("/") for f in files]
common=[]
for segs in zip(*parts):
    if len(set(segs))==1: common.append(segs[0])
    else: break
print("/".join(common) if common else ".")
PY
)
  fi

  if [[ "$status" == "ok" ]]; then
    git add -A >/dev/null 2>&1 || true
    if git diff --cached --quiet; then
      status=skipped; reason=no_files
    else
      git -c user.email=cr-restore@local -c user.name=cr-restore commit -m "leaf $lid" >/dev/null 2>&1 || true
      set +e
      timeout --signal=TERM --kill-after=30 "$CR_TIMEOUT" \
        coderabbit review --agent "${light_flag[@]}" --base-commit="$EMPTY_SHA" --dir "$review_dir" \
        >"$log" 2>"$LOGS/review_${lid}.stderr.txt"
      rc=$?
      set -e
      findings=$(python3 -c "import json,pathlib;n=0
p=pathlib.Path('$log')
for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
  try: o=json.loads(line)
  except Exception: continue
  if o.get('type')=='finding': n+=1
print(n)")
      if grep -qE 'Rate limit exceeded|"type":"error"|All files are ignored' "$log" "$LOGS/review_${lid}.stderr.txt" 2>/dev/null; then
        if grep -q 'All files are ignored' "$log" "$LOGS/review_${lid}.stderr.txt" 2>/dev/null; then
          status=ignored; reason=all_files_ignored
        else
          status=error; reason=coderabbit_error
        fi
      elif [[ $rc -ne 0 && $findings -eq 0 ]]; then
        status=error; reason="rc_$rc"
      else
        status=ok; reason="findings=$findings"
      fi
      cp -f "$log" "$SRC_AUDIT/review_${lid}.jsonl" 2>/dev/null || true
      cp -f "$LOGS/review_${lid}.stderr.txt" "$SRC_AUDIT/review_${lid}.stderr.txt" 2>/dev/null || true
    fi
  fi

  python3 - <<'PY' "$PROGRESS" "$lid" "$status" "$reason" "$files_n" "$findings"
import json,datetime,sys
from pathlib import Path
p=Path(sys.argv[1]); lid,status,reason,files_n,findings=sys.argv[2:7]
data=json.loads(p.read_text(encoding="utf-8"))
data.setdefault("results",{})[lid]={"status":status,"reason":reason,"files":int(files_n),"findings":findings,"at":datetime.datetime.utcnow().isoformat()+"Z"}
p.write_text(json.dumps(data,indent=2),encoding="utf-8")
print(f"RESULT {lid} status={status} reason={reason}")
PY

  if [[ "$status" == "ok" ]]; then
    python3 - <<'PY' "$SRC_AUDIT/state.json" "$lid"
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); lid=sys.argv[2]
data=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"ok":[]}
ok=list(data.get("ok") or [])
if lid not in ok: ok.append(lid)
data["ok"]=ok
p.write_text(json.dumps(data),encoding="utf-8")
PY
  fi
  sleep "$CR_SLEEP"
done < <(python3 -c "import json; [print(json.dumps(x)) for x in json.load(open('$OUT/_run_plan.json'))]")

echo "=== restore finished ==="
python3 -c "import json;print(json.dumps(json.load(open('$PROGRESS')),indent=2))"
