"""Synthetic ranking regression through the same Grafana 12 transformation replay."""
import copy
import json
from pathlib import Path

OUT=Path(__file__).parent
c=json.loads((OUT/'captures.json').read_text(encoding='utf-8'))
baseline=next(x for x in c if x['id']=='bioetl-incident-v1-2010-normal-6h')
candidate=next(x for x in c if x['id']=='bioetl-incident-v1-2010-normal-6h-candidate')
samples=[('runtime','r0',0),('runtime','r1',1),('runtime','r2',1),('runtime','r3',0),('runtime','r4',0),('runtime','r5',0),('provider','p0',2),('dq','d0',2)]
items=[]
for source in (baseline,candidate):
    item=copy.deepcopy(source);item['id']='synthetic-ranking-'+('candidate' if source.get('candidate') else 'before')
    item['provenance']='Synthetic regression only; no samples were written to live Prometheus.'
    frames=[]
    for domain,signal,value in samples:
        ref='A' if source.get('candidate') else {'runtime':'A','provider':'B','dq':'C'}[domain]
        name='bioetl_incident_ranked_'+domain
        labels={'__name__':name,'domain':domain,'pipeline':'fixture','signal':signal,'action':domain}
        frames.append({'schema':{'refId':ref,'meta':{'custom':{'resultType':'vector'}},'fields':[{'name':'Time','type':'time'},{'name':name,'type':'number','labels':labels}]},'data':{'values':[[1788764400000],[value]]}})
    item['response']={'results':{'A':{'status':200,'frames':frames}}}
    items.append(item)
(OUT/'synthetic-rank-input.json').write_text(json.dumps(items,indent=2),encoding='utf-8')
