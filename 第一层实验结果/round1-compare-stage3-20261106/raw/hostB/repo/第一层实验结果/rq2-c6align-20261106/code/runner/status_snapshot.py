from __future__ import annotations
import collections,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
logs=BASE/'logs';stages=collections.defaultdict(collections.Counter);active=[];failures=[]
for path in (logs/'jobs').glob('*.command.json'):
    d=json.loads(path.read_text());spec=d['spec'];key=spec['key']
    if 'wiki-RfA-reconstructed' in key:continue
    stages[key.split('__')[0]][str(d.get('returncode','ACTIVE'))]+=1
    if 'returncode' not in d:
        out=path.with_name(key+'.stdout.log');lines=out.read_text().splitlines() if out.exists() else []
        active.append({'key':key,'pid':d['pid'],'last':lines[-1] if lines else 'waiting / initializing'})
    elif d['returncode']!=0:failures.append({'key':key,'returncode':d['returncode'],'timed_out':d.get('timed_out',False)})
def tail(name:str)->str:
    p=logs/name
    return p.read_text()[-1800:] if p.exists() else ''
print(json.dumps({'stages':dict(stages),'active':active,'failures':failures,'pipeline':tail('finish-pipeline.stdout.log'),'pipeline_error':tail('finish-pipeline.stderr.log'),'handover_error':tail('handover-v5.stderr.log')},ensure_ascii=False))
