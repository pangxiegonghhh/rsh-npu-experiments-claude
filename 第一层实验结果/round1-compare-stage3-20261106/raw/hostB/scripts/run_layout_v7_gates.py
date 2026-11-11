import hashlib,json,os,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
first=json.loads((BASE/'logs/layout-v7-port-gate.json').read_text())
assert first['passed'] and len(first['placements'])==180 and sum(x['rows'] for x in first['condition_grid'])==40
component=json.loads((BASE/'logs/layout-v7-component-run.json').read_text())
assert component['tool_result']['exit_code']==0 and json.loads(component['tool_result']['output'])['passed']
env=os.environ.copy();env['RQ3_LAYOUT_LIB']=str(BASE/'work/liblayouts-v7.dylib')
commands=[]
for label,script,output in [
 ('width','gate_width_sensitivity_v7.py','layout-W-sensitivity-v7-gate.json'),
 ('rq3-tables','gate_rq3_tables_v7.py','rq3-native-table-v7-gate.json'),
 ('random','gate_layouts_flatco_random.py','layout-v7-random-gate.json'),
 ('boundaries','gate_chain_v7_boundaries.py','layout-v7-boundary-gate.json'),
 ('scale','gate_flatco_scale.py','layout-v7-scale-gate.json')]:
 command=[sys.executable,'-B','scripts/'+script];start=time.time()
 with (BASE/'logs'/('layout-v7-'+label+'.stdout')).open('w') as out,(BASE/'logs'/('layout-v7-'+label+'.stderr')).open('w') as err:r=subprocess.run(command,env=env,cwd=BASE,stdout=out,stderr=err)
 rec=dict(command=command,environment_override=dict(RQ3_LAYOUT_LIB=env['RQ3_LAYOUT_LIB']),source_sha256=hashlib.sha256((BASE/'scripts'/script).read_bytes()).hexdigest(),start=start,end=time.time(),exitcode=r.returncode,output=output)
 commands.append(rec);(BASE/'logs'/('layout-v7-'+label+'-command.json')).write_text(json.dumps(rec,indent=2))
 print(label,'EXIT',r.returncode,flush=True)
 if r.returncode or not json.loads((BASE/'logs'/output).read_text())['passed']:
  (BASE/'logs/layout-v7-gates-controller.json').write_text(json.dumps(dict(passed=False,commands=commands,activated=False),indent=2))
  raise SystemExit(1)
(BASE/'logs/layout-v7-gates-controller.json').write_text(json.dumps(dict(passed=True,commands=commands,activated=False),indent=2))
print('V7_ALL_ADDITIONAL_GATES_PASSED_NOT_ACTIVATED',flush=True)
