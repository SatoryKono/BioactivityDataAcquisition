"""Append byte-verified receipts to the isolated artifact branch."""
from pathlib import Path
import json,os,subprocess
ROOT=Path.cwd().resolve()
PROOF=ROOT/'reports/quality/proof-or-stop/grafana-11874-11844'
BRANCH='codex/grafana-acceptance-artifacts-11874-11844'
paths=[(ROOT/p).resolve() for p in json.loads((PROOF/'final-artifact-files.json').read_text(encoding='utf-8'))]
assert all(p.is_file() and p.is_relative_to(PROOF) for p in paths)
env=os.environ.copy();env['GIT_INDEX_FILE']=str(ROOT/'.git/grafana-evidence-index')
def git(*args,data=None):
    return subprocess.check_output(['git',*args],input=data,env=env)
parent=git('rev-parse',f'refs/heads/{BRANCH}').decode().strip()
git('read-tree',parent)
entries=[]
for p in paths:
    blob=git('hash-object','-w','--stdin',data=p.read_bytes()).decode().strip()
    entries.append(f'100644 {blob}\t{p.relative_to(ROOT).as_posix()}\n')
git('update-index','--index-info',data=''.join(entries).encode())
tree=git('write-tree').decode().strip()
commit=git('commit-tree',tree,'-p',parent,'-m','Final verified R11 coverage, current source and five-dashboard screenshot receipts').decode().strip()
for p in paths:
    assert git('show',f'{commit}:{p.relative_to(ROOT).as_posix()}')==p.read_bytes()
git('update-ref',f'refs/heads/{BRANCH}',commit,parent)
subprocess.run(['git','push','origin',f'{commit}:refs/heads/{BRANCH}'],env=env,check=True)
result={'artifact_commit':commit,'parent_artifact_commit':parent,'verified_original_files':len(paths)}
(PROOF/'artifact-final-seal.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
