from pathlib import Path
import subprocess,json,re,collections
summary=json.loads(Path("analysis/simulator-instructions.json").read_text())
for i in range(8,24):
 root=Path(f'sim-case{i}')
 if i:
  cmd=['timeout','120','msprof','op','simulator','--soc-version=Ascend910B2',f'--output={root}','--launch-count=1','--timeout=1','--aic-metrics=PipeUtilization','--dump=on','./build-sim/t8_micro','simone',f'results-sim-case{i}',str(i)]
  with Path(f'sim-case{i}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 text=Path(f'sim-case{i}.log').read_text();assert 'ALL_PASS 1 cases mode=simone' in text,(i,text[-500:])
 trace=next(root.rglob('core0.cubecore0.instr_popped_log.dump'));lines=trace.read_text().splitlines();ops=[];dma=[]
 for line in lines:
  m=re.search(r'\(Binary:[^)]+\)\s+([A-Za-z0-9_]+)',line)
  if m:ops.append(m.group(1))
  if ' MTE2 ' in line:dma.append(line)
 record=dict(index=i,trace=str(trace),opcode_counts=dict(collections.Counter(ops)),mte2_lines=dma);summary.append(record);Path('analysis/simulator-instructions.json').write_text(json.dumps(summary,indent=2));print('SIM_PASS',i,'MTE2',len(dma),'OPCODES',dict(collections.Counter(ops)),flush=True)
print('ALL_SIM_CASES_PASS',flush=True)
