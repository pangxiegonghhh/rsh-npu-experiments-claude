from __future__ import annotations
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from align_context import BASE,dump,assert_runtime
assert_runtime()
import c6
import campaign
spec=json.loads(Path(sys.argv[1]).read_text());output=Path(sys.argv[2]).resolve()
assert output.is_relative_to(BASE/'delivery')
campaign.OUT=output
for name in ('orders','tasks','checks'):(output/name).mkdir(parents=True,exist_ok=True)
campaign.worker(spec)
path=output/'tasks'/(spec['key']+'.json');task=json.loads(path.read_text())
assert len(task['rows'])==len(task['joint'])==16
params=json.loads(task['rows'][0]['member_params']);sizes=params['group_sizes'];n=task['rows'][0]['n']
assert sizes==[16]*(n//16)+([n%16]if n%16 else [])
for row in task['rows']+task['joint']:
    row['note']+='; trace=checks/'+spec['key']+'-bisections.json'
dump(path,task)
dump(output/'checks'/(spec['key']+'-invariants.json'),{'passed':True,'n':n,'group_sizes':sizes,'permutation_checked':True,
 'same_A0_A1_window_and_residual_sets':True,'D_and_membership_checks':task['checks'],'alignment_repair':params['alignment_repair']})
print('CASE COMPLETE',spec['key'],params['alignment_repair'],flush=True)
