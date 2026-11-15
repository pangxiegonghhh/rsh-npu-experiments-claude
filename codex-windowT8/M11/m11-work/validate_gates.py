from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
expected=dict.fromkeys(['gate-v1','gate-A-nd','gate-A-ordinary'],198);expected['gate-micro']=510
records=[]
for name,count in expected.items():
 gates=sorted((root/name).glob('*/gate.json'));assert len(gates)==count,(name,len(gates),count)
 for gate in gates:
  assert json.loads(gate.read_text())['status']=='PASS'
  actual=(gate.parent/'output-f32.bin').read_bytes();reference=(gate.parent/'reference-f32.bin').read_bytes();assert actual==reference,gate
  records.append(dict(gate=str(gate.relative_to(root)),bytes=len(actual),actual_sha256=hashlib.sha256(actual).hexdigest(),reference_sha256=hashlib.sha256(reference).hexdigest()))
 # Host process performs group-level full input and guard audit after per-case gates.
 log=(root/(name+'.log')).read_text();assert f'M11_ALL_PASS {count}' in log,name
for mode in ['gate-A-nd','gate-A-ordinary']:
 for source in (root/'gate-v1').glob('*/output-f32.bin'):
  assert source.read_bytes()==(root/mode/source.parent.name/source.name).read_bytes(),(mode,source)
result=dict(status='PASS',binary_sha256=hashlib.sha256((root/'build/t8_micro').read_bytes()).hexdigest(),expected=expected,finite_integer_outputs_bitwise_equal=True,A_chains_same_output=True,records=records)
(root/'GATES-PASSED.json').write_text(json.dumps(result,indent=2));print('M11_FULL_GATES_PASS',len(records),flush=True)
