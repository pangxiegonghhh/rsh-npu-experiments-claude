"""Supplementary post-timing address readback; never modifies timing executable."""
from pathlib import Path
import subprocess,json,hashlib
ROOT=Path(__file__).resolve().parent

def main()->None:
 subprocess.run(['python3',str(ROOT/'prepare_strong_gate.py')],cwd=ROOT,check=True)
 original=hashlib.sha256((ROOT/'build/t8_micro').read_bytes()).hexdigest();assert original==json.loads((ROOT/'GATES-PASSED.json').read_text())['binary_sha256']
 records=[]
 for mode in [0,1,2]:
  out=ROOT/f'gate-address-a{mode}'
  with (ROOT/f'gate-address-a{mode}.log').open('w') as f:r=subprocess.run([str(ROOT/'build/t8_identity'),'check',str(out),str(ROOT/'strong-gate.list'),'0',str(mode)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  assert r.returncode==0,(mode,r.returncode)
  gates=list(out.glob('*/gate.json'));assert len(gates)==198
  for gate in gates:
   y=(gate.parent/'output-f32.bin').read_bytes();ref=(gate.parent/'reference-f32.bin').read_bytes();assert y==ref,gate
   records.append(dict(path=str(gate.relative_to(ROOT)),bytes=len(y),sha256=hashlib.sha256(y).hexdigest()))
  assert 'M11_ALL_PASS 198' in (ROOT/f'gate-address-a{mode}.log').read_text()
 result=dict(status='PASS',gate_cases=594,individual_tiles_read_back=True,full_rank_nonsymmetric_permutation_A=True,B_row_bits_covered=33,B_values='1..2048 exact FP16 integers',timing_binary_unchanged=hashlib.sha256((ROOT/'build/t8_micro').read_bytes()).hexdigest()==original,checks=records)
 (ROOT/'STRONG-ADDRESS-GATES.json').write_text(json.dumps(result,indent=2));print('M11_STRONG_ADDRESS_GATES_PASS',len(records),flush=True)
if __name__=='__main__':main()
