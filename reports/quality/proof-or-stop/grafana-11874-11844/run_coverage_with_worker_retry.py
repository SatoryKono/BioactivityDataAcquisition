"""Retry native worker crashes while retaining the canonical 17-shard producer."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path.cwd()))
from scripts.engineering.qa import run_local_coverage_verify as producer

ROOT=Path.cwd().resolve()
PROOF=ROOT/'reports/quality/proof-or-stop/grafana-11874-11844'
SCRATCH=PROOF/'full-coverage-f042bfb-r2'
EXPECTED='f042bfb86e67e4bfb256181c977772f52b842154'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==EXPECTED
original=producer._run_logged
attempts=[]

def record():
    (SCRATCH/'worker-retry-attempts.json').write_text(json.dumps(attempts,indent=2),encoding='utf-8')

def logged(command, log, *, env):
    for attempt in range(1,4):
        code=original(command,log,env=env)
        payload=log.read_text(encoding='utf-8',errors='replace')
        crashed=code!=0 and 'node down: Not properly terminated' in payload
        if not crashed or attempt==3:
            if crashed:
                attempts.append({'log':str(log),'attempt':attempt,'exit_code':code,'action':'failed_no_more_retries'})
                record()
            return code
        failed=SCRATCH/'failed-worker-attempts'/f'{log.stem}-{attempt}'
        failed.mkdir(parents=True,exist_ok=False)
        files=[log]
        files.extend(Path(arg.split('=',1)[1]) for arg in command if arg.startswith('--junitxml='))
        cov=Path(env['COVERAGE_FILE'])
        files.extend(cov.parent.glob(cov.name+'*'))
        hashes={}
        for file in files:
            file=file.resolve()
            if not file.is_file():
                continue
            assert file.is_relative_to(SCRATCH)
            dst=(failed/file.name).resolve()
            assert dst.is_relative_to(SCRATCH)
            hashes[str(file.relative_to(SCRATCH))]=hashlib.sha256(file.read_bytes()).hexdigest()
            shutil.move(str(file),str(dst))
        attempts.append({'log':str(log),'attempt':attempt,'exit_code':code,'action':'rerun_same_canonical_command','failed_file_sha256':hashes})
        record()
        print(f'[worker-retry] {log.stem}: exit={code}; preserved attempt {attempt}; rerun unchanged command',flush=True)
    raise AssertionError('unreachable')

producer._run_logged=logged
code=producer.main(['--scratch-dir',str(SCRATCH)])
if not (SCRATCH/'worker-retry-attempts.json').exists():
    record()
raise SystemExit(code)
