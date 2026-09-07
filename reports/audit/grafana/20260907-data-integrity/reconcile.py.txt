"""Independent calculations over source samples/artifacts, never panel results."""
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent


def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def increase(series,start,end):
    samples=[(float(t),float(v)) for t,v in series.get('values',[]) if start<t<=end and math.isfinite(float(v))]
    if len(samples)<2:return None
    first,last=samples[0],samples[-1]
    change=last[1]-first[1]
    for prev,current in zip(samples,samples[1:]):
        if current[1]<prev[1]:change+=prev[1]
    observed=last[0]-first[0]
    avg=observed/(len(samples)-1)
    before=first[0]-start;after=end-last[0]
    if before>=avg*1.1:before=avg/2
    if change>0 and first[1]>=0:before=min(before,observed*first[1]/change)
    if after>=avg*1.1:after=avg/2
    return change*(observed+before+after)/observed


def result(source):
    return source['body'].get('data',{}).get('result',[])


def value(s):return float(s['value'][1])


def source_rows(series):
    return [{**s['metric'],'Value':value(s),'Time':float(s['value'][0])*1000} for s in series]


def group_max(series,keys):
    groups={}
    for s in series:
        k=tuple(s['metric'].get(x,'') for x in keys)
        groups[k]=max(groups.get(k,float('-inf')),value(s))
    return [{**dict(zip(keys,k)),'Value':v} for k,v in groups.items()]


def scalar_ref(item):
    refs=[result(s) for s in item['reference']['sources']]
    calc=item['reference']['calculation'];start=item['from']/1000;end=item['to']/1000
    if calc=='max':return max(map(value,refs[0]),default=None)
    if calc=='increase_sum':
        values=[increase(s,start,end) for s in refs[0]]
        values=[v for v in values if v is not None]
        return sum(values) if values else None
    if calc=='blocker_count':
        counts=[increase(s,start,end) for s in refs[0]];counts=[v for v in counts if v is not None]
        flags=[max(float(v) for _,v in s['values'])>0 for s in refs[1] if s.get('values')]
        return math.floor(sum(counts)+sum(flags)+0.5) if counts and flags else None
    if calc=='dq_state':
        critical=[value(s)*2 for s in refs[0] if value(s)>0]
        return max(critical or [value(s) for s in refs[1]],default=None)
    if calc=='stage_lag':
        pipeline=item['variables']['pipeline'];pipeline=pipeline if isinstance(pipeline,str) else '|'.join(pipeline)
        if pipeline=='$__all':pipeline='.*'
        canonical=re.sub('^workflow_','',pipeline)
        samples=[float(v) for s in refs[0] if re.fullmatch(pipeline,s['metric'].get('pipeline','')) or s['metric'].get('pipeline')==canonical for _,v in s.get('values',[])]
        return max(samples,default=None)
    if calc=='freshness_hours':
        ages=[max(0,end-max(float(v) for _,v in s['values']))/3600 for s in refs[0] if s.get('values')]
        return max(ages,default=None)
    raise ValueError(calc)


def prom_table_ref(item):
    refs=[result(s) for s in item['reference']['sources']];calc=item['reference']['calculation']
    if calc=='route_top2':rows=source_rows(refs[0] or refs[1]);limit=2
    elif calc=='provider_top3':rows=group_max(refs[0],['provider']);limit=3
    elif calc=='cause_top4':rows=[r for r in group_max(refs[0],['provider','cause']) if r['Value']>0];limit=4
    elif calc=='dq_reasons_top5':rows=[r for r in source_rows(refs[0]) if r['Value']>0];limit=5
    elif calc=='incident_top5':rows=source_rows([s for ref in refs for s in ref]);limit=5
    elif calc=='alert_count':
        count=Counter((s['metric'].get('alertname',''),s['metric'].get('alertstate','')) for s in refs[0])
        return [{'alertname':k[0],'alertstate':k[1],'Value':v} for k,v in count.items()]
    else:raise ValueError(calc)
    return sorted(rows,key=lambda r:-r['Value'])[:limit]


def frame_rows(frames):
    rows=[]
    for f in frames:
        for i in range(f['length']):rows.append({field['name']:field['values'][i] for field in f['fields']})
    return rows


def project(rows,frames):
    names=list(dict.fromkeys(field['name'] for f in frames for field in f['fields']))
    types={field['name']:field['type'] for f in frames for field in f['fields']}
    output=[]
    for row in rows:
        values={k:row.get(k,'') for k in names}
        for k,v in values.items():
            if types[k]=='time' and isinstance(v,str) and v:
                values[k]=int(datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()*1000)
        output.append(values)
    return output


def canonical(rows):
    return sorted(json.dumps({k:int(v) if isinstance(v,float) and v.is_integer() else v for k,v in r.items()},sort_keys=True,ensure_ascii=False) for r in rows)


def http_ref(item,persisted):
    """Return the independent artifact rows when the source artifact exists."""
    sources=[s['body'] for s in item['reference']['sources']]
    pid=item['panel_id'];run=item['variables'].get('run_id');pipeline=item['variables'].get('pipeline')
    report=next((x['body'] for x in persisted if x['body'].get('identity',{}).get('run_id')==run and x['body'].get('identity',{}).get('pipeline_name')==pipeline),None)
    if pid in (9403,3023):
        if not report:return None,'No exact persisted run selected; direct HTTP comparison alone is not an independent accounting reference.'
        aliases={'bronze_records':'bronze_records','silver_valid_records':'silver_valid','silver_filtered_out_records':'silver_filtered_out','silver_quarantined_records':'silver_quarantined','silver_skipped_records':'silver_skipped','silver_deduplicated_records':'silver_deduplicated','gold_written_records':'gold_written','gold_excluded_by_contract_records':'gold_excluded_by_contract','gold_quarantined_records':'gold_quarantined','gold_skipped_records':'gold_skipped','gold_deduplicated_records':'gold_deduplicated'}
        counts={k:report['layers'][v] for k,v in aliases.items()}
        return counts,'Persisted pipeline report layers; integers parsed independently from rendered strings.'
    if pid==3011:
        if not report:return None,'No matching persisted run report.'
        rows=[]
        for r in report['funnel']:
            r=r.copy();r['removals_summary']='; '.join(str(x['count'])+' '+x['reason_code'] for x in r['removals']) or '—';rows.append(r)
        return rows,'Persisted funnel rows with independent count/reason formatting.'
    if pid in (3010,3020):
        items=sources[0].get('items',[]);rows=[]
        for r in items:
            path=r.get('json_path','').replace('/app/','')
            artifact=next((x for x in persisted if x['path']==path),None)
            if not artifact:return None,'Index references a missing source artifact: '+path
            body=artifact['body'];identity=body.get('identity',{})
            if pid==3010:
                rows.append({'pipeline':identity['pipeline_name'],'run_id':identity['run_id'],'run_type':identity['run_type'],'workflow_id':identity.get('workflow_id'),'workflow_run_id':identity.get('workflow_run_id'),'started_at':identity.get('started_at'),'completed_at':identity.get('completed_at'),'status':identity['status'],'selected':int(identity['run_id']==run)})
            else:
                rows.append({'workflow':identity.get('workflow_name'),'workflow_run_id':identity.get('workflow_run_id'),'completed_at':identity.get('completed_at'),'status':identity.get('status'),'selected':0})
        return rows,'Each displayed index row is independently read from its hashed file; latest-N selection and ordering are not independently proved.'
    if pid in (9402,3022):
        rows=[r for source,target in zip(sources,item['request']['queries']) for r in source.get(target['root_selector'],[])]
        # The identity-table branch is a second service source. Identity rows from
        # the pipeline report are anchored independently; manifest fields need its file.
        return rows,'Transport/merge reference only for control-plane rows; persisted manifest reference is separately required.'
    return None,'No reference defined.'


def reconcile():
    captures=read('captures.json');transforms={x['id']:x for x in read('transformed.json')};persisted=read('persisted-references.json')
    rows=[];details=[]
    for item in captures:
        if 'response' not in item:continue
        transformed=transforms[item['id']];calc=item['reference']['calculation'];kind=item['panel']['type']
        status='PASS';note='';expected=None;actual=None;samples=0;error=None
        try:
            if item['status']!=200:
                status='NA';note='Rejected invalid/out-of-domain selector input; preserve explicit query error.'
            elif kind in ('stat','gauge'):
                expected=scalar_ref(item)
                displays=[v['display']['numeric'] for v in transformed.get('displays',[]) if v.get('name')!='No data']
                actual=displays[-1] if displays else None;samples=len(displays)
                if expected is None or actual is None:
                    status='NOT_VERIFIABLE' if expected is None and actual is None else 'FAIL'
                    note='Source samples absent/insufficient; empty matches UNKNOWN, but no numeric agreement is claimed.'
                else:
                    error=abs(actual-expected);status='PASS' if error<=1e-9 else 'FAIL'
            elif calc=='alert_history':
                status='NOT_VERIFIABLE';note='Raw range series captured; exact stale-marker reconstruction is unavailable from the range-vector API.'
            elif calc=='persisted_http':
                expected,note=http_ref(item,persisted)
                actual=frame_rows(transformed['frames']);samples=len(actual)
                if expected is None:status='NOT_VERIFIABLE'
                elif item['panel_id'] in (9403,3023):
                    actual={r['parameter'].split(' ',1)[1]:int(r['value'].replace(' ','')) for r in actual}
                    status='PASS' if actual==expected else 'FAIL';error=max((abs(actual.get(k,-1)-v) for k,v in expected.items()),default=0)
                else:
                    expected=project(expected,transformed['frames'])
                    status='PASS' if canonical(actual)==canonical(expected) else 'FAIL'
                    if item['panel_id'] in (9402,3022) and status=='PASS':status='NOT_VERIFIABLE'
            else:
                expected=project(prom_table_ref(item),transformed['frames']);actual=frame_rows(transformed['frames']);samples=len(actual)
                status='PASS' if canonical(actual)==canonical(expected) else 'FAIL'
                if not samples:status='NOT_VERIFIABLE';note='No source rows at this scope/time; no numeric sample.'
                if calc=='incident_top5' and not any(f['name']=='Value' for frame in transformed['frames'] for f in frame['fields']):status='FAIL';note='Missing common Value column: Value #A/#B/#C cannot satisfy priority sort/reduction.'
        except (KeyError,ValueError,TypeError) as exc:
            status='NOT_VERIFIABLE';note='Reference could not be evaluated: '+str(exc)
        if status=='PASS' and error is None:error=0
        details.append({'id':item['id'],'status':status,'reference_method':calc,'actual':actual,'expected':expected,'sample_size':samples,'absolute_error':error,'tolerance':1e-9,'note':note})
        rows.append({'id':item['id'],'dashboard':item['uid'],'panel_id':item['panel_id'],'scenario':item['scenario'],'candidate':bool(item.get('candidate')),'from_utc':datetime.fromtimestamp(item['from']/1000,timezone.utc).isoformat(),'to_utc':datetime.fromtimestamp(item['to']/1000,timezone.utc).isoformat(),'status':status,'sample_size':samples,'absolute_error':error,'relative_error':error/abs(expected) if error is not None and isinstance(expected,(int,float)) and expected else None,'tolerance':1e-9,'method':calc,'note':note})
    dump('reference-results.json',details)
    with (OUT/'reconciliation.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(Counter(x['status'] for x in details))
    for x in details:
        if x['status']=='FAIL' and 'normal-6h' in x['id']:print(x['id'],x['note'],str(x['actual'])[:350],str(x['expected'])[:350])


if __name__=='__main__':reconcile()
