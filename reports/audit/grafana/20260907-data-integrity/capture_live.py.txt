"""Read-only exact Grafana requests and independently selected source evidence."""
import copy
import gzip
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import yaml
from dotenv import dotenv_values

ROOT = Path('E:/github/BioactivityDataAcquisition-wt-data-10163-10164')
MAIN = Path('E:/github/BioactivityDataAcquisition')
OUT = Path(__file__).parent
GRAFANA = 'http://127.0.0.1:3000'
PROM = 'http://127.0.0.1:9090'
OPS = 'http://127.0.0.1:8000'
ENV = dotenv_values(MAIN / '.env')
SESSION = requests.Session()
SESSION.auth = (ENV.get('GF_SECURITY_ADMIN_USER') or 'admin', ENV.get('GF_SECURITY_ADMIN_PASSWORD') or ENV.get('GRAFANA_ADMIN_PASSWORD') or ENV.get('GRAFANA_PASSWORD') or '')
NOW = datetime.now(timezone.utc).isoformat()
CACHE = {}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def get(url, params=None):
    key = json.dumps([url, params], sort_keys=True)
    if key not in CACHE:
        response = SESSION.get(url, params=params, timeout=30) if url.startswith(GRAFANA) else requests.get(url, params=params, timeout=30)
        CACHE[key] = {'url': response.url, 'status': response.status_code, 'body': response.json(), 'captured_at': datetime.now(timezone.utc).isoformat()}
    return CACHE[key]


def prom(expr, end):
    return get(PROM + '/api/v1/query', {'query': expr, 'time': end / 1000})


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels', []))


def interpolate(text, values, variables, is_url, start, end):
    def replace(m):
        name = m.group(1) or m.group(3)
        fmt = m.group(2)
        builtins = {'__from': str(start), '__to': str(end), '__range': str((end-start)//1000)+'s', '__range_s': str((end-start)//1000), '__interval': '30s', '__rate_interval': '2m'}
        if name in builtins:
            return builtins[name]
        if name not in values:
            raise ValueError('Unresolved variable: ' + name)
        value = values[name]
        var = variables.get(name, {})
        if value == '$__all':
            value = var.get('allValue') or '.*'
            # A custom All value is passed through by Grafana without escaping.
            return value
        if isinstance(value, list):
            if fmt == 'csv' or is_url:
                return ','.join(value)
            return '(' + '|'.join(re.escape(v).replace('\\','\\\\') for v in value) + ')'
        value = str(value)
        if fmt == 'queryparam':
            return quote(value, safe='')
        if not is_url and (var.get('multi') or var.get('includeAll')):
            return re.escape(value).replace('\\','\\\\')
        return value
    return re.sub(r'\$\{([A-Za-z_]\w*)(?::(\w+))?\}|\$([A-Za-z_]\w*)', replace, text)


# These source selectors and calculations are specified from the metric catalog
# and the approved recording-rule definitions, never copied from panel inventory.
REFS = {
 ('bioetl-control-plane-v1', 891): ('max', ['bioetl_replay_safety_blockers_15m{pipeline=~"$pipeline",run_type=~"$run_type"}']),
 ('bioetl-control-plane-v1', 130): ('blocker_count', ['bioetl_trust_replay_blocker_events_total{pipeline=~"$pipeline",run_type=~"$run_type"}[$__range]', 'bioetl_trust_replay_blocker_integrity{pipeline=~"$pipeline",run_type=~"$run_type"}[$__range]']),
 ('bioetl-control-plane-v1', 9401): ('max', ['bioetl_control_plane_current_status_trusted{pipeline=~"$pipeline",run_type=~"$run_type"}']),
 ('bioetl-overview-v2', 214): ('max', ['bioetl_l0_status{pipeline=~"$pipeline",run_type=~"$run_type"}']),
 ('bioetl-overview-v2', 215): ('route_top2', ['bioetl_l0_next_action_route{pipeline=~"$pipeline",run_type=~"$run_type"}', 'bioetl_l0_next_action_no_route']),
 ('bioetl-runtime', 9401): ('max', ['bioetl_runtime_current_status_trusted{pipeline=~"$pipeline",run_type=~"$run_type"}']),
 ('bioetl-runtime', 205): ('increase_sum', ['bioetl_pipeline_runs_total{pipeline=~"$pipeline",run_type=~"$run_type",status="failed"}[$__range]']),
 ('bioetl-runtime', 237): ('stage_lag', ['bioetl_stage_lag_seconds{run_type=~"$run_type"}[15m]']),
 ('bioetl-runtime', 9102): ('max', ['bioetl_runtime_trust_gap_status_10m']),
 ('bioetl-provider-health-v2', 9101): ('provider_top3', ['bioetl_provider_current_status{provider=~"$provider",provider!~"^(test|synthetic)$"}']),
 ('bioetl-provider-health-v2', 9103): ('cause_top4', ['bioetl_provider_current_cause']),
 ('bioetl-dq-v2', 9401): ('max', ['bioetl_dq_current_status{pipeline=~"$pipeline"}']),
 ('bioetl-dq-v2', 9101): ('dq_state', ['bioetl_dq_current_reason{pipeline=~"$pipeline",severity="crit"}', 'bioetl_dq_current_status{pipeline=~"$pipeline"}']),
 ('bioetl-dq-v2', 9102): ('dq_reasons_top5', ['bioetl_dq_first_window_reason{pipeline=~"$pipeline"}']),
 ('bioetl-dq-v2', 8): ('freshness_hours', ['bioetl_data_freshness_seconds{pipeline=~"$pipeline"}[12h]']),
 ('bioetl-incident-v1', 2010): ('incident_top5', ['bioetl_incident_ranked_runtime', 'bioetl_incident_ranked_provider', 'bioetl_incident_ranked_dq']),
 ('bioetl-incident-v1', 2005): ('alert_count', ['ALERTS{alertstate=~"firing|pending"}']),
 ('bioetl-incident-v1', 2006): ('alert_history', ['ALERTS{alertstate=~"firing|pending"}[$__range]']),
}


def capture():
    inventory = yaml.safe_load((ROOT / 'docs/03-guides/dashboards/contracts/dashboard-inventory.yaml').read_text(encoding='utf-8'))
    metadata = {'captured_at': NOW, 'endpoint': GRAFANA, 'grafana': get(GRAFANA+'/api/health'), 'datasources': [], 'targets': get(PROM+'/api/v1/targets'), 'rules': get(PROM+'/api/v1/rules'), 'build': get(PROM+'/api/v1/status/buildinfo'), 'source_index': get(OPS+'/ops/observability/pipeline-run-reports', {'limit': 100})}
    for ds in get(GRAFANA+'/api/datasources')['body']:
        metadata['datasources'].append({k: ds[k] for k in ('uid', 'type', 'name', 'url', 'jsonData') if k in ds})
        metadata['datasources'][-1]['health'] = get(GRAFANA+'/api/datasources/uid/'+ds['uid']+'/health')
    metadata['head'] = subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(), '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    normal_end = 1788764400000 # 2026-09-07 07:00 UTC
    anomaly_end = 1788765000000 # 2026-09-07 07:10 UTC
    known = {'workflow':'chembl_baseline', 'pipeline':'chembl_assay', 'run_type':'backfill', 'run_id':'a72f6bc0-d3cb-5e9f-bd7d-00763ec963c8', 'provider':'chembl', 'pipeline_context':'chembl_assay', 'adapter':'chembl', 'stage':'$__all', 'provider_hint':'chembl'}
    matrix = [('normal-15m', normal_end-900000, normal_end, known), ('normal-6h', normal_end-21600000, normal_end, known), ('scrape-anomaly', anomaly_end-300000, anomaly_end, known)]
    matrix += [('default',normal_end-21600000,normal_end,None), ('all',normal_end-21600000,normal_end,{'workflow':'$__all','run_type':'$__all','run_id':'','stage':'$__all'}), ('multi',normal_end-21600000,normal_end,{'run_type':['backfill','incremental'],'run_id':''}), ('empty',normal_end-21600000,normal_end,{'pipeline':'','run_type':'','run_id':'','provider':''}), ('regex-special',normal_end-21600000,normal_end,{'pipeline':'audit.(no-such)+[pipeline]','run_type':'backfill','run_id':''}), ('selected-missing-run',normal_end-21600000,normal_end,{'run_id':'00000000-0000-0000-0000-000000000000'})]
    metadata['known_events'] = get(PROM+'/api/v1/query_range', {'query':'up{job="bioetl"}', 'start':(normal_end-21600000)/1000, 'end':anomaly_end/1000,'step':'30s'})
    captures = []
    dashboards = []
    for board in inventory['dashboards']:
        uid = board['uid']
        source = get(GRAFANA+'/api/dashboards/uid/'+uid)
        dashboard = source['body']['dashboard']
        shipped = read(ROOT / 'grafana/dashboards' / (uid+'.json'))
        variables = {v['name']:v for v in dashboard.get('templating',{}).get('list',[])}
        defaults = {name:v.get('current',{}).get('value','') for name,v in variables.items()}
        dashboards.append({'uid':uid, 'live':source, 'shipped':shipped, 'key_panels':board['key_panels']})
        indexed = {p['id']:p for p in walk(dashboard['panels'])}
        for key in board['key_panels']:
            panel = indexed[key['id']]
            if panel['type']=='text':
                continue
            for name,start,end,overrides in matrix:
                values = defaults.copy()
                values.update(known if overrides is not None else {})
                values.update(overrides or {})
                # A single-value selector does not support UI multiselect; do not fabricate it.
                unsupported = [k for k,v in values.items() if isinstance(v,list) and len(v)>1 and not variables.get(k,{}).get('multi')]
                item = {'id':f'{uid}-{key["id"]}-{name}', 'uid':uid, 'panel_id':key['id'], 'scenario':name, 'from':start,'to':end,'variables':values,'unsupported':unsupported,'panel':panel}
                if unsupported:
                    captures.append(item)
                    continue
                queries = []
                for target in panel.get('targets',[]):
                    if target.get('hide'): continue
                    q = copy.deepcopy(target)
                    is_http = bool(q.get('url'))
                    q['datasource'] = {'type':'yesoreyeram-infinity-datasource','uid':'bioetl-ops-http'} if is_http else {'type':'prometheus','uid':'prometheus'}
                    q.update(intervalMs=30000,maxDataPoints=720)
                    for field in ('url','expr'):
                        if q.get(field):q[field] = interpolate(q[field],values,variables,is_http,start,end)
                    if not is_http:
                        q.update(utcOffsetSec=0,exemplar=False,requestId=str(key['id'])+q['refId'])
                        q.setdefault('range',not q.get('instant',False))
                        q.setdefault('instant',False)
                    queries.append(q)
                payload = {'from':str(start),'to':str(end),'queries':queries}
                response = SESSION.post(GRAFANA+'/api/ds/query',json=payload,timeout=60)
                item.update(request=payload,response=response.json(),status=response.status_code,captured_at=datetime.now(timezone.utc).isoformat())
                if (uid,key['id']) in REFS:
                    calculation, selectors = REFS[(uid,key['id'])]
                    item['reference'] = {'calculation':calculation,'sources': [prom(interpolate(q,values,variables,False,start,end),end) for q in selectors]}
                else:
                    item['reference'] = {'calculation':'persisted_http','sources':[get(OPS+q['url']) for q in queries]}
                captures.append(item)
            dump('captures-partial.json',captures)
            print(uid,key['id'],'captured',flush=True)
    add_candidates(captures,dashboards)
    # Persisted artifacts provide a separate reference for HTTP accounting and run identity.
    persisted = []
    for pattern in ('reports/run-reports/pipeline/*/*/pipeline-run-report.json','reports/run-reports/workflow/*/*/workflow-run-report.json'):
        for p in MAIN.glob(pattern):
            raw = p.read_bytes()
            persisted.append({'path':p.relative_to(MAIN).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'body':json.loads(raw)})
    dump('runtime-metadata.json',metadata)
    dump('dashboards.json',dashboards)
    dump('persisted-references.json',persisted)
    dump('captures.json',captures)
    with gzip.open(OUT/'source-responses.json.gz','wt',encoding='utf-8') as f:json.dump(CACHE,f,ensure_ascii=False)
    print('Completed',len(captures),'panel requests;',len(CACHE),'source requests')


def add_candidates(captures, dashboards):
    # Candidates are distinguished from the pre-fix provisioned panels.
    for uid,pid in [('bioetl-runtime',205),('bioetl-incident-v1',2010)]:
        candidate = next(p for p in walk(read(ROOT/'grafana/dashboards'/(uid+'.json'))['panels']) if p['id']==pid)
        for baseline in [x for x in captures if x['uid']==uid and x['panel_id']==pid and 'request' in x and not x.get('candidate')]:
            item = copy.deepcopy(baseline)
            item['id'] += '-candidate'
            item['candidate'] = True
            item['panel'] = candidate
            q = copy.deepcopy(candidate['targets'][0])
            vars = {v['name']:v for v in next(d['live']['body']['dashboard'] for d in dashboards if d['uid']==uid)['templating']['list']}
            q['expr'] = interpolate(q['expr'],item['variables'],vars,False,item['from'],item['to'])
            q.update(datasource={'uid':'prometheus','type':'prometheus'},intervalMs=30000,maxDataPoints=720,utcOffsetSec=0,exemplar=False)
            item['request']['queries'] = [q]
            response = SESSION.post(GRAFANA+'/api/ds/query',json=item['request'],timeout=60)
            item.update(response=response.json(),status=response.status_code)
            captures.append(item)


if __name__=='__main__':capture()
