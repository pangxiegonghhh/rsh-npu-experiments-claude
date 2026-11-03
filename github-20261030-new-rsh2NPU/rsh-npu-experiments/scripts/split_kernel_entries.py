"""CANN's launch generator infers a kernel type per source file."""
from pathlib import Path
import sys
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('npu')
s=(p/'kernels.cpp').read_text()
assert not (p/'work.h').exists()
head=s[:s.index('#define ALL_ARGS')]
(p/'work.h').write_text('#pragma once\n'+head)
argnames='ptr cols vals gp refs tiles rows rhs packed output config'.split()
for name in ['cube','vector','mix','restore']:
 start=s.index('extern "C" __global__ __aicore__ void rsh_'+name+'(')
 nextstart=s.find('\nextern "C" ',start+1)
 body=s[start:nextstart]
 body=body.replace('ALL_ARGS',','.join('GM_ADDR '+a for a in argnames))
 names=['packed','map','output','config'] if name=='restore' else argnames
 wrapper='\nextern "C" void rsh_launch_'+name+'(void* stream,int blocks,'+','.join('void* '+a for a in names)+') {\n rsh_'+name+'<<<blocks,nullptr,stream>>>('+','.join('(GM_ADDR)'+a for a in names)+');\n}\n'
 (p/(name+'.cpp')).write_text('#include "work.h"\n'+body+wrapper)
decl=[]
for name in ['cube','vector','mix','restore']:
 count=4 if name=='restore' else 11
 decl.append('extern "C" void rsh_launch_'+name+'(void*,int,'+','.join(['void*']*count)+');')
old=s[s.index('extern "C" void rsh_launch('):]
for name,blocks in [('vector','c.cores*2'),('cube','c.cores'),('mix','c.cores'),('restore','c.cores*2')]:
 old=old.replace('rsh_'+name+'<<<'+blocks+',nullptr,stream>>>(', 'rsh_launch_'+name+'(stream,'+blocks+',').replace('(GM_ADDR)','')
(p/'dispatch.cpp').write_text('#include "common.h"\n'+'\n'.join(decl)+'\n'+old)
f=p/'CMakeLists.txt';t=f.read_text().replace('STATIC kernels.cpp','STATIC cube.cpp vector.cpp mix.cpp restore.cpp').replace('rsh_runner runner.cpp','rsh_runner runner.cpp dispatch.cpp');f.write_text(t)
print('SPLIT_ENTRIES_OK')
