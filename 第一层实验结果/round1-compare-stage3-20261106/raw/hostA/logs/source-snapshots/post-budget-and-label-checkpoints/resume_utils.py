import json
from pathlib import Path
from naming import t23_name
BASE=Path(__file__).resolve().parents[1]
def completed_post():
 done=set()
 for p in (BASE/'work/post-e').glob('*/record.json'):
  r=json.loads(p.read_text())
  if r.get('status') in ['OK','INCOMPLETE']:done.add((r['matrix'],t23_name(r.get('member',r.get('method'))),int(r['tau'])))
 return done
def completed_diag():
 done=set()
 for p in (BASE/'work/t23-diagnostics').glob('*/diag.json'):
  r=json.loads(p.read_text());done.add((r['matrix'],t23_name(r['member'])))
 return done
