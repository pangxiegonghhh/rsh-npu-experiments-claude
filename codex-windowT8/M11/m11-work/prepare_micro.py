from pathlib import Path
import json
from prepare import ROOT,put,commands
out=ROOT/'inputs';names=[];check=[];a_names=[]
for dtype,es in [('FP16',2),('FP32',4)]:
 for n in [16,32,64,128,256]:
  for h in range(1,17):
   physical=list(range(h))+list(range(h+16,h+16+16-h));raw=list(range(h))+[0xffffffff-i for i in range(16-h)]
   cmd=commands(physical,n,h)
   for path in range(3):
    for batch in [64,256,1024,4096]:
     name=f'micro-copy-{dtype}-n{n}-h{h}-p{path}-b{batch}'
     cfg=[int(es==4),n,1,2,1,1,1,1,path,1,h,0,h+16,0,1,batch,0,0,0,0,h,0,0,0]+[0,0,1]+physical
     for suffix,values in [('config',cfg),('commands',[v for c in cmd for v in c]),('offsets',[0,len(cmd)]),('rows',raw),('lengths',[h])]:put(out/(name+f'.{suffix}.bin'),values)
     names.append(name)
     if batch==64:check.append(name)
  for mode,label in [(2,'transpose'),(3,'plain'),(4,'a-chain')]:
   for batch in [64,256,1024,4096]:
    name=f'micro-{label}-{dtype}-n{n}-b{batch}';rr=list(range(16));cmd=commands(rr,n,16)
    cfg=[int(es==4),n,1,2,1,1,1,1,0,1,16,0,32,0,mode,batch,0,0,0,0,16,0,0,0]+[0,0,1]+rr
    for suffix,values in [('config',cfg),('commands',[v for c in cmd for v in c]),('offsets',[0,len(cmd)]),('rows',rr),('lengths',[16])]:put(out/(name+f'.{suffix}.bin'),values)
    (a_names if mode==4 else names).append(name)
    if batch==64:check.append(name)
for label,items in [('stage2',names),('micro-gate',check),('a-micro',a_names)]: (ROOT/(label+'.list')).write_text('\n'.join(items)+'\n')
print(dict(stage2=len(names),a_chain=len(a_names),gate=len(check)))
